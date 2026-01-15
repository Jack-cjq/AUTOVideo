"""
视频编辑核心逻辑
使用 FFmpeg 进行视频拼接、添加音频、调速、字幕烧录等
"""
import os
import sys
from typing import Optional, List

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
        voice_path: Optional[str],
        bgm_path: Optional[str],
        speed=1.0,
        subtitle_path: Optional[str] = None,
        bgm_volume: float = 0.25,
        voice_volume: float = 1.0,
        output_name: Optional[str] = None,
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
        :param output_name: 自定义输出文件名（不含扩展名），如果为None则自动生成
        :return: 成品视频绝对路径（失败返回None）
        """
        try:
            import ffmpeg
        except ImportError:
            raise RuntimeError("未安装 ffmpeg-python，请先 pip install ffmpeg-python")
        
        # 检查 FFmpeg 是否可用
        try:
            import shutil
            
            # 优先检查环境变量或配置文件指定的 FFmpeg 路径
            try:
                from config import FFMPEG_PATH as config_ffmpeg_path
                ffmpeg_path = os.environ.get('FFMPEG_PATH') or config_ffmpeg_path
            except ImportError:
                ffmpeg_path = os.environ.get('FFMPEG_PATH')
            if ffmpeg_path and os.path.exists(ffmpeg_path):
                # 设置 ffmpeg-python 使用指定的路径
                import ffmpeg
                ffmpeg_path = os.path.abspath(ffmpeg_path)
                # 将 FFmpeg 目录添加到 PATH（仅当前进程）
                ffmpeg_dir = os.path.dirname(ffmpeg_path)
                if ffmpeg_dir not in os.environ.get('PATH', ''):
                    os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
                print(f"[VideoEditor] 使用环境变量指定的 FFmpeg：{ffmpeg_path}")
            else:
                # 尝试从系统 PATH 中查找
                ffmpeg_path = shutil.which('ffmpeg')
                if not ffmpeg_path:
                    # 尝试常见的安装路径
                    common_paths = [
                        r'D:\ffmpeg\bin\ffmpeg.exe',
                        r'C:\ffmpeg\bin\ffmpeg.exe',
                        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            ffmpeg_path = path
                            ffmpeg_dir = os.path.dirname(ffmpeg_path)
                            if ffmpeg_dir not in os.environ.get('PATH', ''):
                                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
                            print(f"[VideoEditor] 找到 FFmpeg：{ffmpeg_path}")
                            break
                    
                    if not ffmpeg_path:
                        raise RuntimeError(
                            "未找到 FFmpeg 可执行文件。\n"
                            "解决方案：\n"
                            "1. 将 FFmpeg 的 bin 目录添加到系统 PATH 环境变量\n"
                            "2. 或设置环境变量 FFMPEG_PATH 指向 ffmpeg.exe 的完整路径\n"
                            "   例如：set FFMPEG_PATH=D:\\软件\\ffmpeg-8.0.1\\bin\\ffmpeg.exe\n"
                            "3. 重启后端服务后重试"
                        )
        except Exception as e:
            raise RuntimeError(f"检查 FFmpeg 时出错：{str(e)}")
        
        # 输出目录
        OUTPUT_VIDEO_DIR = os.path.join(BASE_DIR, 'uploads', 'videos')
        if not os.path.exists(OUTPUT_VIDEO_DIR):
            os.makedirs(OUTPUT_VIDEO_DIR)
        
        # 1. 生成输出文件名
        import secrets
        import re
        import datetime
        
        def sanitize_filename(s):
            """清理文件名，移除非法字符"""
            if not s:
                return ""
            # 移除或替换非法字符
            s = re.sub(r'[<>:"/\\|?*]', '', s)  # 移除Windows非法字符
            s = re.sub(r'\s+', '_', s)  # 空格替换为下划线
            s = s.strip('._')  # 移除首尾的点和下划线
            return s[:100]  # 限制长度
        
        if output_name:
            # 使用自定义文件名
            safe_name = sanitize_filename(output_name)
            if not safe_name:
                # 如果清理后为空，使用默认命名
                output_name = f"output_{secrets.token_hex(4)}.mp4"
            else:
                # 确保有.mp4扩展名
                if not safe_name.endswith('.mp4'):
                    output_name = f"{safe_name}.mp4"
                else:
                    output_name = safe_name
        else:
            # 自动生成文件名
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

            # 获取配音时长（如果有配音）
            voice_duration = None
            if voice_path and os.path.exists(voice_path):
                try:
                    voice_probe = ffmpeg.probe(voice_path)
                    voice_duration = float(voice_probe.get("format", {}).get("duration", 0.0))
                    print(f"[VideoEditor] 配音时长: {voice_duration:.2f}秒")
                except Exception as dur_error:
                    print(f"[VideoEditor] 警告：获取配音时长失败：{dur_error}")

            # 获取视频总时长（拼接后的原始时长）
            video_duration = 0.0
            try:
                for vp in video_paths:
                    vp_probe = ffmpeg.probe(vp)
                    vp_duration = float(vp_probe.get("format", {}).get("duration", 0.0))
                    video_duration += vp_duration
                print(f"[VideoEditor] 视频原始总时长: {video_duration:.2f}秒")
            except Exception as dur_error:
                print(f"[VideoEditor] 警告：获取视频时长失败：{dur_error}")

            # 视频滤镜链（用 -vf，避免 filter_complex 下 Windows 字幕路径转义坑）
            vf_parts: List[str] = []

            # 调速：setpts=1/speed*PTS
            try:
                speed_f = float(speed)
            except Exception:
                speed_f = 1.0
            if speed_f and abs(speed_f - 1.0) > 1e-6:
                vf_parts.append(f"setpts={1/speed_f}*PTS")
                # 调整后的视频时长
                video_duration = video_duration / speed_f
                print(f"[VideoEditor] 调速后视频时长: {video_duration:.2f}秒")

            # 如果有配音且视频较短，需要循环视频
            loop_concat_file = None
            if voice_duration and voice_duration > 0 and video_duration > 0:
                duration_diff = abs(video_duration - voice_duration)
                if duration_diff > 0.5:  # 差异超过0.5秒才调整
                    if video_duration < voice_duration:
                        # 视频较短，需要循环
                        print(f"[VideoEditor] 视频较短（{video_duration:.2f}秒 < {voice_duration:.2f}秒），将循环视频")
                        loop_times = int(voice_duration / video_duration) + 1
                        # 创建循环视频的concat文件
                        import secrets
                        loop_concat_file = os.path.join(OUTPUT_VIDEO_DIR, f"loop_concat_{secrets.token_hex(4)}.txt")
                        with open(loop_concat_file, "w", encoding="utf-8") as f:
                            for _ in range(loop_times):
                                for vp in video_paths:
                                    vp_escaped = vp.replace("'", "'\\''")
                                    f.write(f"file '{vp_escaped}'\n")
                        # 使用循环后的视频
                        v_in = ffmpeg.input(loop_concat_file, format="concat", safe=0)
                        # 更新视频总时长为循环后的时长
                        video_duration = video_duration * loop_times
                        print(f"[VideoEditor] 已创建循环视频，循环 {loop_times} 次，循环后总时长：{video_duration:.2f}秒")

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
            if voice_path:
                # 标准化路径（统一使用正斜杠或反斜杠）
                voice_path = os.path.normpath(voice_path)
                if os.path.exists(voice_path):
                    print(f"[VideoEditor] 使用配音文件：{voice_path}")
                    a_voice = ffmpeg.input(voice_path).audio
                    a_voice = a_voice.filter("volume", voice_volume)
                    audio_stream = a_voice
                else:
                    print(f"[VideoEditor] 警告：配音文件不存在：{voice_path}")

            if bgm_path:
                # 标准化路径
                bgm_path = os.path.normpath(bgm_path)
                if os.path.exists(bgm_path):
                    print(f"[VideoEditor] 使用BGM文件：{bgm_path}")
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
                else:
                    print(f"[VideoEditor] 警告：BGM文件不存在：{bgm_path}")

            # 输出：显式只取视频流（去掉原音轨）
            v_stream = v_in.video
            use_complex_filter = False  # 标记是否使用了复杂滤镜图
            
            # 如果视频较长需要裁剪到配音时长（包括循环后的情况）
            if voice_duration and video_duration > voice_duration:
                print(f"[VideoEditor] 视频较长（{video_duration:.2f}秒 > {voice_duration:.2f}秒），将裁剪到配音时长，确保视频在配音结束时停止")
                v_stream = v_stream.trim(end=voice_duration).setpts("PTS-STARTPTS")
                use_complex_filter = True  # trim 创建了复杂滤镜图
                print(f"[VideoEditor] 视频已裁剪到 {voice_duration:.2f}秒，与配音时长匹配")
            
            # 如果使用了复杂滤镜图，需要将调速和字幕都通过 filter 方法添加
            if use_complex_filter:
                # 应用调速（如果有）
                if speed_f and abs(speed_f - 1.0) > 1e-6:
                    v_stream = v_stream.filter("setpts", f"{1/speed_f}*PTS")
                    print(f"[VideoEditor] 通过复杂滤镜图应用调速：{speed_f}x")
                
                # 添加字幕（如果有）
                if subtitle_path and os.path.exists(subtitle_path):
                    # 使用绝对路径，确保路径格式正确
                    abs_subtitle_path = os.path.abspath(subtitle_path)
                    sub_file_raw = abs_subtitle_path.replace("\\", "/")
                    print(f"[VideoEditor] 通过复杂滤镜图添加字幕，路径：{sub_file_raw}")
                    v_stream = v_stream.filter("subtitles", filename=sub_file_raw, charenc="UTF-8", 
                                               force_style="FontName=Microsoft YaHei,FontSize=28,Outline=2,Shadow=1")
                    print(f"[VideoEditor] 字幕滤镜已添加")
                
                # 清除 vf，因为已经通过 filter 方法添加了所有滤镜
                vf = None
            else:
                # 如果没有使用复杂滤镜图，字幕通过 vf 参数添加（已在之前添加到 vf_parts）
                pass
            
            if audio_stream is not None:
                # 构建输出参数
                output_kwargs = {
                    "vcodec": "libx264",
                    "acodec": "aac",
                }
                # 添加视频滤镜（如果有，且未使用复杂滤镜图）
                if vf and not use_complex_filter:
                    output_kwargs["vf"] = vf
                
                # 创建输出流
                stream = ffmpeg.output(
                    v_stream,
                    audio_stream,
                    output_path,
                    **output_kwargs
                )
            else:
                output_kwargs = {"vcodec": "libx264"}
                if vf and not use_complex_filter:
                    output_kwargs["vf"] = vf
                stream = ffmpeg.output(v_stream, output_path, **output_kwargs)

            # 执行命令
            print(f"[VideoEditor] 开始执行 FFmpeg 命令，输出文件：{output_path}")
            print(f"[VideoEditor] 视频路径：{video_paths}")
            print(f"[VideoEditor] 配音路径：{voice_path}")
            print(f"[VideoEditor] BGM路径：{bgm_path}")
            print(f"[VideoEditor] 字幕路径：{subtitle_path}")
            print(f"[VideoEditor] 播放速度：{speed}")
            
            try:
                # 执行 FFmpeg 命令
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
            except ffmpeg.Error as ffmpeg_error:
                # 捕获 FFmpeg 错误
                stderr_msg = ""
                if hasattr(ffmpeg_error, 'stderr') and ffmpeg_error.stderr:
                    try:
                        stderr_msg = ffmpeg_error.stderr.decode('utf-8', errors='ignore')
                    except:
                        stderr_msg = str(ffmpeg_error.stderr)
                error_msg = f"FFmpeg 执行失败：{stderr_msg or str(ffmpeg_error)}"
                print(f"[VideoEditor] {error_msg}")
                raise RuntimeError(error_msg)
            except Exception as ffmpeg_ex:
                # 捕获其他异常
                error_msg = f"FFmpeg 执行异常：{str(ffmpeg_ex)}"
                print(f"[VideoEditor] {error_msg}")
                raise RuntimeError(error_msg)

            # 4. 清理临时文件
            safe_remove(concat_file)
            if 'loop_concat_file' in locals() and loop_concat_file:
                safe_remove(loop_concat_file)

            # 验证成品是否存在
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[VideoEditor] 剪辑成功，输出文件：{output_path}，大小：{file_size} 字节")
                return output_path
            else:
                print(f"[VideoEditor] 警告：输出文件不存在：{output_path}")
                return None

        except Exception as e:
            error_msg = f"剪辑失败：{e}"
            print(f"[VideoEditor] {error_msg}")
            import traceback
            traceback.print_exc()
            # 清理临时文件/失败文件
            if 'concat_file' in locals():
                safe_remove(concat_file)
            if 'output_path' in locals() and os.path.exists(output_path):
                safe_remove(output_path)
            raise  # 重新抛出异常，让调用者处理


# 单例实例
video_editor = VideoEditor()

