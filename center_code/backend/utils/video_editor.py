"""
视频编辑核心逻辑
使用 FFmpeg 进行视频拼接、添加音频、调速、字幕烧录等
"""
import os
import sys

# 导入配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def safe_remove(file_path):
    """安全删除文件"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"删除文件失败：{e}")


def get_abs_path(rel_path):
    """将相对路径转换为绝对路径"""
    return os.path.join(BASE_DIR, rel_path)


class VideoEditor:
    @staticmethod
    def edit(
        video_paths,
        voice_path: str | None,
        bgm_path: str | None,
        speed=1.0,
        subtitle_path: str | None = None,
        bgm_volume: float = 0.25,
        voice_volume: float = 1.0,
    ):
        """
        最简剪辑逻辑：拼接视频+添加BGM+调速
        
        :param video_paths: 视频素材绝对路径列表
        :param voice_path: 配音音频绝对路径（None则不加配音）
        :param bgm_path: BGM音频绝对路径（None则不加BGM）
        :param speed: 播放速度（默认1.0）
        :param subtitle_path: 字幕文件绝对路径（.srt），可选
        :param bgm_volume: BGM 音量（0~1）
        :param voice_volume: 配音音量（0~1）
        :return: 成品视频绝对路径（失败返回None）
        """
        try:
            import ffmpeg
        except ImportError:
            raise RuntimeError("未安装 ffmpeg-python，请先 pip install ffmpeg-python")
        
        # 输出目录
        OUTPUT_VIDEO_DIR = os.path.join(BASE_DIR, 'uploads', 'videos')
        if not os.path.exists(OUTPUT_VIDEO_DIR):
            os.makedirs(OUTPUT_VIDEO_DIR)
        
        # 1. 生成唯一输出文件名
        import secrets
        output_name = f"output_{secrets.token_hex(4)}.mp4"
        output_path = os.path.join(OUTPUT_VIDEO_DIR, output_name)

        try:
            # 2. 拼接视频（生成临时concat文件）
            concat_file = os.path.join(OUTPUT_VIDEO_DIR, f"concat_{secrets.token_hex(4)}.txt")
            with open(concat_file, "w", encoding="utf-8") as f:
                for vp in video_paths:
                    # 转义单引号
                    vp_escaped = vp.replace("'", "'\\''")
                    f.write(f"file '{vp_escaped}'\n")

            # 3. 执行FFmpeg命令：拼接+调速+加BGM
            # 基础输入：拼接视频
            v_in = ffmpeg.input(concat_file, format="concat", safe=0)

            # 视频滤镜链（用 -vf，避免 filter_complex 下 Windows 字幕路径转义坑）
            vf_parts: list[str] = []

            # 调速：setpts=1/speed*PTS
            try:
                speed_f = float(speed)
            except Exception:
                speed_f = 1.0
            if speed_f and abs(speed_f - 1.0) > 1e-6:
                vf_parts.append(f"setpts={1/speed_f}*PTS")

            # 烧录字幕（可选）
            if subtitle_path and os.path.exists(subtitle_path):
                # Windows 盘符 ':' 需要写成 '\:'（在 Python 字符串里是 '\\:'）
                sub_file = subtitle_path.replace("\\", "/").replace(":", "\\:")
                # filename/force_style 用单引号包裹更稳
                vf_parts.append(
                    "subtitles="
                    + f"filename='{sub_file}'"
                    + ":charenc=UTF-8"
                    + ":force_style='FontName=Microsoft YaHei,FontSize=28,Outline=2,Shadow=1'"
                )

            vf = ",".join(vf_parts) if vf_parts else None

            # 音频：默认去掉原视频音轨，用配音 + BGM 双轨混音（可选）
            audio_stream = None
            if voice_path and os.path.exists(voice_path):
                a_voice = ffmpeg.input(voice_path).audio
                a_voice = a_voice.filter("volume", voice_volume)
                audio_stream = a_voice

            if bgm_path and os.path.exists(bgm_path):
                # 循环 BGM，避免短音乐提前结束
                a_bgm = ffmpeg.input(bgm_path, stream_loop=-1).audio
                a_bgm = a_bgm.filter("volume", bgm_volume)
                if audio_stream is None:
                    audio_stream = a_bgm
                else:
                    audio_stream = ffmpeg.filter(
                        [audio_stream, a_bgm],
                        "amix",
                        inputs=2,
                        duration="shortest",
                        dropout_transition=0,
                    )

            # 输出：显式只取视频流（去掉原音轨）
            v_stream = v_in.video
            if audio_stream is not None:
                stream = ffmpeg.output(
                    v_stream,
                    audio_stream,
                    output_path,
                    vcodec="libx264",
                    acodec="aac",
                    shortest=None,
                    **({"vf": vf} if vf else {}),
                )
            else:
                stream = ffmpeg.output(v_stream, output_path, vcodec="libx264", **({"vf": vf} if vf else {}))

            # 执行命令
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            # 4. 清理临时文件
            safe_remove(concat_file)

            # 验证成品是否存在
            if os.path.exists(output_path):
                return output_path
            return None

        except Exception as e:
            print(f"剪辑失败：{e}")
            import traceback
            traceback.print_exc()
            # 清理临时文件/失败文件
            if 'concat_file' in locals():
                safe_remove(concat_file)
            safe_remove(output_path)
            return None


# 单例实例
video_editor = VideoEditor()

