"""
iFlytek (讯飞) 录音文件转写 (LFASR / RAASR) client.

This module is intentionally self-contained and only used when ASR_PROVIDER is set
to "iflytek_lfasr" (or similar). Baidu ASR remains the default.

Env vars:
  - IFLYTEK_APPID
  - IFLYTEK_SECRET_KEY   (also known as APISecret in many docs; for public RAASR/LFASR)
  - IFLYTEK_LFASR_HOST   (optional, default: https://raasr.xfyun.cn/v2/api)

Office/enterprise variant (as provided by user snippet):
  - IFLYTEK_LFASR_MODE=office
  - IFLYTEK_LFASR_HOST=https://office-api-ist-dx.iflyaisol.com
  - IFLYTEK_ACCESS_KEY_ID     (aka APIKey)
  - IFLYTEK_ACCESS_KEY_SECRET (aka APISecret)

Notes:
  - The API is a multi-step flow: create -> upload slices -> merge -> poll -> getResult.
  - We parse common result formats and return sentence-level timestamps.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import time
import tempfile
import urllib.parse
import wave
from typing import Dict, List, Optional, Tuple

import requests


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()

def _verify_ssl() -> bool:
    v = (_env("IFLYTEK_VERIFY_SSL", "true") or "true").strip().lower()
    return v not in ("0", "false", "no", "off")


def _md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _hmac_sha1_base64(key: str, msg: str) -> str:
    import hmac

    digest = hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def _signa(appid: str, secret_key: str, ts: str) -> str:
    # iFlytek LFASR signa: base64(hmac-sha1(secret_key, md5(appid + ts)))
    return _hmac_sha1_base64(secret_key, _md5_hex(appid + ts))


def _post_form(url: str, data: Dict, timeout: int = 30) -> Dict:
    resp = requests.post(url, data=data, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        body = ""
        try:
            body = (resp.text or "").strip()
        except Exception:
            body = ""
        hint = f"HTTP {resp.status_code} for url={url}"
        if body:
            hint += f" body={body[:500]}"
        raise requests.HTTPError(hint, response=resp) from e
    return resp.json()


def _raise_if_error(payload: Dict, context: str) -> None:
    # Typical: {"ok":0,"err_no":...,"failed":...} or {"code":"0","desc":"success"} depending on versions.
    if payload is None:
        raise RuntimeError(f"{context}: empty response")
    if isinstance(payload, dict):
        if "err_no" in payload and str(payload.get("err_no")) not in ("0", ""):
            raise RuntimeError(f"{context}: err_no={payload.get('err_no')} err_msg={payload.get('err_msg')}")
        if "ok" in payload and str(payload.get("ok")) not in ("0", ""):
            raise RuntimeError(f"{context}: ok={payload.get('ok')} desc={payload.get('desc')}")
        if "code" in payload and str(payload.get("code")) not in ("0", "000000"):
            raise RuntimeError(f"{context}: code={payload.get('code')} message={payload.get('message') or payload.get('desc')}")


def _candidate_bases(host: str) -> List[str]:
    host = (host or "").strip().rstrip("/")
    if not host:
        return []

    bases: List[str] = []

    def add(x: str) -> None:
        x = (x or "").strip().rstrip("/")
        if x and x not in bases:
            bases.append(x)

    add(host)

    # Add common variants for RAASR/LFASR deployments.
    if host.endswith("/v2/api"):
        add(host[: -len("/v2/api")] + "/api")
        add(host[: -len("/v2/api")] + "/v2/api")  # keep original form
    elif host.endswith("/api"):
        add(host[: -len("/api")] + "/v2/api")
    else:
        add(host + "/v2/api")
        add(host + "/api")

    # Swap domain between raasr and lfasr if user provided one of them.
    for x in list(bases):
        add(x.replace("raasr.xfyun.cn", "lfasr.xfyun.cn"))
        add(x.replace("lfasr.xfyun.cn", "raasr.xfyun.cn"))

    return bases


def _iter_slices(file_path: str, slice_bytes: int) -> Tuple[int, List[bytes]]:
    size = os.path.getsize(file_path)
    if size <= 0:
        return 0, []
    slice_num = int(math.ceil(size / float(slice_bytes)))
    out: List[bytes] = []
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(slice_bytes)
            if not chunk:
                break
            out.append(chunk)
    return slice_num, out


def _parse_result_to_timestamps(result_payload: object) -> Tuple[str, List[Dict]]:
    """
    Try to parse iFlytek results into:
      - full_text: str
      - timestamps: [{"text":..., "start":sec, "end":sec, "duration":sec}, ...]
    """

    def _loads_maybe_nested_json(value: object) -> object:
        """
        Some fields (e.g. office orderResult, lattice2) may contain JSON encoded as a string,
        sometimes double-escaped. Try a couple of best-effort decoding passes.
        """
        cur = value
        for _ in range(3):
            if not isinstance(cur, str):
                return cur
            s = cur.strip()
            if not s:
                return cur
            try:
                cur = json.loads(s)
                continue
            except Exception:
                # Common issue: extra escaping of backslashes
                try:
                    cleaned = s.replace("\\\\", "\\")
                    cur = json.loads(cleaned)
                    continue
                except Exception:
                    return value
        return cur

    def _parse_office_order_result(obj: object) -> Optional[Tuple[str, List[Dict]]]:
        """
        Office API variant: orderResult contains {"lattice":[{"json_1best":"{...}"}...]}
        Each json_1best has st.bg/st.ed (ms) and st.rt[].ws[].cw[].w tokens.
        We convert each lattice item to a sentence-level timestamp.
        """
        order_obj = _loads_maybe_nested_json(obj)
        if not isinstance(order_obj, dict):
            return None
        lattice = order_obj.get("lattice")
        if not isinstance(lattice, list) or not lattice:
            return None

        texts: List[str] = []
        timestamps: List[Dict] = []

        for lattice_item in lattice:
            if not isinstance(lattice_item, dict):
                continue
            json_1best = lattice_item.get("json_1best")
            best_obj = _loads_maybe_nested_json(json_1best)
            if not isinstance(best_obj, dict):
                continue
            st = best_obj.get("st") or {}
            if not isinstance(st, dict):
                continue

            bg = st.get("bg")
            ed = st.get("ed")
            try:
                bg_ms = float(bg) if bg is not None else None
                ed_ms = float(ed) if ed is not None else None
            except Exception:
                bg_ms, ed_ms = None, None

            seg_tokens: List[str] = []
            rt = st.get("rt")
            if isinstance(rt, list):
                for rt_item in rt:
                    if not isinstance(rt_item, dict):
                        continue
                    ws = rt_item.get("ws")
                    if not isinstance(ws, list):
                        continue
                    for ws_item in ws:
                        if not isinstance(ws_item, dict):
                            continue
                        cw = ws_item.get("cw")
                        if not isinstance(cw, list):
                            continue
                        for cw_item in cw:
                            if not isinstance(cw_item, dict):
                                continue
                            w = cw_item.get("w")
                            if w is None:
                                continue
                            seg_tokens.append(str(w))

            seg_text = "".join(seg_tokens).strip()
            if not seg_text:
                continue

            texts.append(seg_text)
            if bg_ms is not None and ed_ms is not None:
                s = max(0.0, bg_ms / 1000.0)
                e = max(s, ed_ms / 1000.0)
                timestamps.append({"text": seg_text, "start": s, "end": e, "duration": e - s})

        return ("".join(texts).strip(), timestamps)

    def add(seg_text: str, start_ms: float, end_ms: float) -> None:
        seg_text = (seg_text or "").strip()
        if not seg_text:
            return
        s = max(0.0, float(start_ms) / 1000.0)
        e = max(s, float(end_ms) / 1000.0)
        timestamps.append({"text": seg_text, "start": s, "end": e, "duration": e - s})
        texts.append(seg_text)

    texts: List[str] = []
    timestamps: List[Dict] = []

    # Office API orderResult (stringified JSON)
    office_parsed = _parse_office_order_result(result_payload)
    if office_parsed:
        return office_parsed

    # getResult may return: list[{"onebest": "...", "bg": 0, "ed": 1234, ...}, ...]
    if isinstance(result_payload, list):
        for item in result_payload:
            if not isinstance(item, dict):
                continue
            seg_text = item.get("onebest") or item.get("text") or ""
            bg = item.get("bg")
            ed = item.get("ed")
            if bg is not None and ed is not None:
                add(seg_text, float(bg), float(ed))
            else:
                seg_text = (seg_text or "").strip()
                if seg_text:
                    texts.append(seg_text)
        return ("".join(texts).strip(), timestamps)

    # Sometimes wrapped in dict fields
    if isinstance(result_payload, dict):
        # Common wrapper: {"data": [...]} or {"result": [...]} or {"orderResult": "...json..."}
        for key in ("data", "result", "results"):
            v = result_payload.get(key)
            if v:
                t, ts = _parse_result_to_timestamps(v)
                return t, ts

        order = result_payload.get("orderResult")
        if isinstance(order, str) and order.strip():
            # Could be office orderResult or other wrapped JSON
            order_obj = _loads_maybe_nested_json(order)
            office_parsed = _parse_office_order_result(order_obj)
            if office_parsed:
                return office_parsed
            return _parse_result_to_timestamps(order_obj)

        # Lattice-style: {"lattice2": "...json..."}
        lattice2 = result_payload.get("lattice2")
        if isinstance(lattice2, str) and lattice2.strip():
            lattice_obj = _loads_maybe_nested_json(lattice2)
            # best-effort: extract segments with bg/ed and w/onebest
            if isinstance(lattice_obj, dict):
                lat = lattice_obj.get("lattice") or lattice_obj.get("lattice2") or lattice_obj
                if isinstance(lat, list):
                    for seg in lat:
                        if not isinstance(seg, dict):
                            continue
                        seg_text = seg.get("onebest") or seg.get("text") or ""
                        bg = seg.get("bg")
                        ed = seg.get("ed")
                        if bg is not None and ed is not None:
                            add(seg_text, float(bg), float(ed))
                    return ("".join(texts).strip(), timestamps)

    # Fallback: treat as plain text
    txt = str(result_payload or "").strip()
    return (txt, timestamps)


def _ensure_wav_for_office_api(audio_file_path: str) -> Tuple[str, Optional[str]]:
    """
    Office/enterprise API variant requires WAV. If input is not wav, convert to wav via ffmpeg.
    Returns: (wav_path, tmp_path_to_cleanup)
    """
    if audio_file_path.lower().endswith(".wav"):
        return audio_file_path, None

    try:
        import ffmpeg  # type: ignore
    except Exception as e:
        raise RuntimeError(f"讯飞转写需要 WAV 输入，且当前非 WAV，无法转换（缺少 ffmpeg-python）：{e}")

    tmp_dir = tempfile.gettempdir()
    base = os.path.splitext(os.path.basename(audio_file_path))[0]
    out_path = os.path.join(tmp_dir, f"iflytek_asr_{base}_{int(time.time())}.wav")

    # Convert to 16kHz mono wav (common ASR-friendly format)
    stream = ffmpeg.input(audio_file_path)
    stream = ffmpeg.output(stream, out_path, ac=1, ar=16000, format="wav")
    ffmpeg.run(stream, overwrite_output=True, quiet=True)
    return out_path, out_path


def _wav_duration_ms(wav_path: str) -> int:
    with wave.open(wav_path, "rb") as wav_file:
        n_frames = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
        if not sample_rate:
            return 0
        return int(round(n_frames / float(sample_rate) * 1000.0))


def _office_signature_base_string(params: Dict) -> str:
    sign_params = {k: v for k, v in params.items() if k != "signature"}
    sorted_params = sorted(sign_params.items(), key=lambda x: x[0])
    parts: List[str] = []
    for k, v in sorted_params:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        ek = urllib.parse.quote(str(k), safe="")
        ev = urllib.parse.quote(s, safe="")
        parts.append(f"{ek}={ev}")
    return "&".join(parts)


def _office_signature(access_key_secret: str, base_string: str) -> str:
    import hmac

    digest = hmac.new(access_key_secret.encode("utf-8"), base_string.encode("utf-8"), digestmod="sha1").digest()
    return base64.b64encode(digest).decode("utf-8")


def _office_upload_and_poll(
    audio_file_path: str,
    *,
    host: str,
    appid: str,
    access_key_id: str,
    access_key_secret: str,
    timeout_sec: int,
) -> object:
    wav_path, tmp_to_cleanup = _ensure_wav_for_office_api(audio_file_path)
    try:
        verify_ssl = _verify_ssl()
        if not verify_ssl:
            try:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

        file_size = str(os.path.getsize(wav_path))
        file_name = os.path.basename(wav_path)
        duration_ms = str(_wav_duration_ms(wav_path))

        # dateTime requires tz offset like 2026-01-21T12:34:56+0800
        local_now = time.localtime()
        dt = time.strftime("%Y-%m-%dT%H:%M:%S", local_now)
        tz = time.strftime("%z", local_now)
        date_time = f"{dt}{tz}"

        signature_random = base64.b64encode(os.urandom(12)).decode("utf-8").replace("=", "")[:16]

        upload_path = "/v2/upload"
        params = {
            "appId": appid,
            "accessKeyId": access_key_id,
            "dateTime": date_time,
            "signatureRandom": signature_random,
            "fileSize": file_size,
            "fileName": file_name,
            "language": "autodialect",
            "duration": duration_ms,
        }

        base_string = _office_signature_base_string(params)
        signature = _office_signature(access_key_secret, base_string)
        headers = {"Content-Type": "application/octet-stream", "signature": signature}

        encoded_params = []
        for k, v in params.items():
            encoded_params.append(f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}")
        upload_url = f"{host.rstrip('/')}{upload_path}?{'&'.join(encoded_params)}"

        with open(wav_path, "rb") as f:
            audio_bytes = f.read()

        resp = requests.post(upload_url, headers=headers, data=audio_bytes, timeout=60, verify=verify_ssl)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise requests.HTTPError(f"HTTP {resp.status_code} for url={upload_url} body={(resp.text or '')[:500]}", response=resp) from e
        payload = resp.json()
        _raise_if_error(payload, "讯飞上传失败")

        try:
            order_id = payload["content"]["orderId"]
        except Exception as e:
            raise RuntimeError(f"讯飞上传成功但未返回 orderId：{payload}") from e

        # Poll getResult
        get_path = "/v2/getResult"
        start = time.time()
        while True:
            if time.time() - start > timeout_sec:
                raise RuntimeError(f"讯飞转写超时：orderId={order_id}")

            query_params = {
                "appId": appid,
                "accessKeyId": access_key_id,
                "dateTime": date_time,
                "ts": str(int(time.time())),
                "orderId": order_id,
                "signatureRandom": signature_random,
            }
            base_string_q = _office_signature_base_string(query_params)
            signature_q = _office_signature(access_key_secret, base_string_q)
            headers_q = {"Content-Type": "application/json", "signature": signature_q}
            encoded_q = []
            for k, v in query_params.items():
                encoded_q.append(f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}")
            query_url = f"{host.rstrip('/')}{get_path}?{'&'.join(encoded_q)}"

            r = requests.post(query_url, headers=headers_q, data=json.dumps({}), timeout=30, verify=verify_ssl)
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise requests.HTTPError(f"HTTP {r.status_code} for url={query_url} body={(r.text or '')[:500]}", response=r) from e
            res = r.json()
            _raise_if_error(res, "讯飞查询失败")

            try:
                status = int(res["content"]["orderInfo"]["status"])
            except Exception:
                status = -1

            if status == 4:
                return res
            if status != 3:
                raise RuntimeError(f"讯飞转写异常：status={status} resp={res}")
            time.sleep(10)
    finally:
        if tmp_to_cleanup and os.path.exists(tmp_to_cleanup):
            try:
                os.remove(tmp_to_cleanup)
            except Exception:
                pass


def transcribe_with_timestamps(
    audio_file_path: str,
    *,
    timeout_sec: int = 15 * 60,
    poll_interval_sec: float = 3.0,
) -> Tuple[str, List[Dict]]:
    """
    Upload an audio file to iFlytek LFASR and return (text, timestamps).
    """
    if not os.path.isfile(audio_file_path):
        raise RuntimeError(f"音频文件不存在：{audio_file_path}")

    appid = _env("IFLYTEK_APPID")
    mode = (_env("IFLYTEK_LFASR_MODE") or "").strip().lower()
    host = _env("IFLYTEK_LFASR_HOST", "https://raasr.xfyun.cn/v2/api").rstrip("/")

    # Office/enterprise API variant (no create/merge, just upload+poll)
    if mode == "office" or "office-api" in host:
        access_key_id = _env("IFLYTEK_ACCESS_KEY_ID") or _env("IFLYTEK_API_KEY") or _env("IFLYTEK_APIKEY")
        access_key_secret = _env("IFLYTEK_ACCESS_KEY_SECRET") or _env("IFLYTEK_SECRET_KEY") or _env("IFLYTEK_API_SECRET")
        if not appid or not access_key_id or not access_key_secret:
            raise RuntimeError("缺少讯飞Office转写配置：IFLYTEK_APPID、IFLYTEK_ACCESS_KEY_ID(APIKey)、IFLYTEK_ACCESS_KEY_SECRET(APISecret)")

        res_payload = _office_upload_and_poll(
            audio_file_path,
            host=host,
            appid=appid,
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            timeout_sec=timeout_sec,
        )
        # Office result typically wraps orderResult in res["content"]["orderResult"] (string or object)
        payload_obj = res_payload
        try:
            payload_obj = (res_payload or {}).get("content", {}).get("orderResult")  # type: ignore[attr-defined]
            if isinstance(payload_obj, str) and payload_obj.strip():
                try:
                    payload_obj = json.loads(payload_obj)
                except Exception:
                    pass
        except Exception:
            payload_obj = res_payload
        text, timestamps = _parse_result_to_timestamps(payload_obj)
        timestamps = [t for t in timestamps if isinstance(t, dict) and "start" in t and "end" in t and t.get("text")]
        timestamps.sort(key=lambda x: float(x.get("start") or 0.0))
        return (text.strip(), timestamps)

    # Public RAASR/LFASR variant
    secret_key = _env("IFLYTEK_SECRET_KEY") or _env("IFLYTEK_API_SECRET")
    if not appid or not secret_key:
        raise RuntimeError("缺少讯飞配置：请设置 IFLYTEK_APPID 和 IFLYTEK_SECRET_KEY(或 IFLYTEK_API_SECRET)")

    base_candidates = _candidate_bases(host)
    if not base_candidates:
        raise RuntimeError("无效的 IFLYTEK_LFASR_HOST")

    ts = str(int(time.time()))
    signa = _signa(appid, secret_key, ts)

    file_size = os.path.getsize(audio_file_path)
    file_name = os.path.basename(audio_file_path)

    slice_bytes = 10 * 1024 * 1024
    slice_num, slices = _iter_slices(audio_file_path, slice_bytes)
    if slice_num <= 0:
        raise RuntimeError("音频文件为空，无法转写")

    # 1) create (try candidate bases; different products/accounts may use different base paths)
    create_payload = None
    base = None
    last_err: Optional[Exception] = None
    for b in base_candidates:
        try:
            create_payload = _post_form(
                f"{b}/create",
                data={
                    "appid": appid,
                    "signa": signa,
                    "ts": ts,
                    "file_len": str(file_size),
                    "file_name": file_name,
                    "slice_num": str(slice_num),
                },
                timeout=30,
            )
            base = b
            break
        except requests.HTTPError as e:
            last_err = e
            resp = getattr(e, "response", None)
            # 404 likely means wrong base path; try next candidate.
            if resp is not None and getattr(resp, "status_code", None) == 404:
                continue
            raise
        except Exception as e:
            last_err = e
            raise

    if create_payload is None or base is None:
        raise RuntimeError(
            f"讯飞创建任务失败：未命中有效接口基址。"
            f"请检查 IFLYTEK_LFASR_HOST（当前={host}），候选={base_candidates}，错误={last_err}"
        )

    _raise_if_error(create_payload, "讯飞创建任务失败")
    task_id = None
    if isinstance(create_payload, dict):
        task_id = (
            (create_payload.get("data") or {}).get("task_id")
            or (create_payload.get("data") or {}).get("id")
            or create_payload.get("task_id")
            or create_payload.get("id")
        )
    task_id = str(task_id or "").strip()
    if not task_id:
        raise RuntimeError(f"讯飞创建任务失败：无法获取 task_id，响应={create_payload}")

    upload_url = f"{base}/upload"
    merge_url = f"{base}/merge"
    progress_url = f"{base}/getProgress"
    result_url = f"{base}/getResult"

    # 2) upload slices
    upload_id = task_id
    for idx, chunk in enumerate(slices, start=1):
        ts_u = str(int(time.time()))
        signa_u = _signa(appid, secret_key, ts_u)
        files = {"content": chunk}
        resp = requests.post(
            upload_url,
            data={
                "appid": appid,
                "signa": signa_u,
                "ts": ts_u,
                "task_id": task_id,
                "upload_id": upload_id,
                "slice_id": f"{idx}",
            },
            files=files,
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        _raise_if_error(payload, f"讯飞上传分片失败 slice_id={idx}")

    # 3) merge
    ts_m = str(int(time.time()))
    signa_m = _signa(appid, secret_key, ts_m)
    merge_payload = _post_form(
        merge_url,
        data={"appid": appid, "signa": signa_m, "ts": ts_m, "task_id": task_id, "file_name": file_name},
        timeout=30,
    )
    _raise_if_error(merge_payload, "讯飞合并任务失败")

    # 4) poll progress
    start = time.time()
    status = None
    while True:
        if time.time() - start > timeout_sec:
            raise RuntimeError("讯飞转写超时")
        ts_p = str(int(time.time()))
        signa_p = _signa(appid, secret_key, ts_p)
        prog_payload = _post_form(
            progress_url,
            data={"appid": appid, "signa": signa_p, "ts": ts_p, "task_id": task_id},
            timeout=30,
        )
        _raise_if_error(prog_payload, "讯飞查询进度失败")
        # progress response often contains JSON string in data
        data = prog_payload.get("data") if isinstance(prog_payload, dict) else None
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = None
        if isinstance(data, list) and data:
            try:
                first = data[0]
                if isinstance(first, dict):
                    status = first.get("status")
            except Exception:
                status = None
        if str(status) == "9":  # finished
            break
        if str(status) in ("-1", "4", "5"):  # failed/canceled (best-effort)
            raise RuntimeError(f"讯飞转写失败，status={status}, progress={prog_payload}")
        time.sleep(max(0.5, float(poll_interval_sec)))

    # 5) get result
    ts_r = str(int(time.time()))
    signa_r = _signa(appid, secret_key, ts_r)
    res_payload = _post_form(
        result_url,
        data={"appid": appid, "signa": signa_r, "ts": ts_r, "task_id": task_id},
        timeout=60,
    )
    _raise_if_error(res_payload, "讯飞获取结果失败")

    data = res_payload.get("data") if isinstance(res_payload, dict) else None
    if isinstance(data, str) and data.strip():
        try:
            data = json.loads(data)
        except Exception:
            pass

    text, timestamps = _parse_result_to_timestamps(data if data is not None else res_payload)
    # Ensure monotonic timestamps
    timestamps = [t for t in timestamps if isinstance(t, dict) and "start" in t and "end" in t and t.get("text")]
    timestamps.sort(key=lambda x: float(x.get("start") or 0.0))
    return (text.strip(), timestamps)
