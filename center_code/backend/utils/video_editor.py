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
            vf_parts: List[str] = []

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

