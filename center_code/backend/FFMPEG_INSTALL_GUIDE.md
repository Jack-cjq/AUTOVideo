# FFmpeg 安装指南

## 问题说明
当前目录 `D:\软件\ffmpeg-8.0.1` 是 FFmpeg 的**源代码**，不是可执行文件。需要下载**编译好的 Windows 版本**。

## 安装方法

### 方法 1：下载预编译版本（推荐）

1. **访问下载页面**：
   - https://www.gyan.dev/ffmpeg/builds/ （推荐，包含完整版本）
   - 或 https://github.com/BtbN/FFmpeg-Builds/releases

2. **下载 Windows 版本**：
   - 选择 "ffmpeg-release-essentials.zip" 或 "ffmpeg-release-full.zip"
   - 解压到任意目录，例如：`D:\软件\ffmpeg`

3. **目录结构应该是**：
   ```
   D:\软件\ffmpeg\
   ├── bin\
   │   ├── ffmpeg.exe    ← 这个文件是必需的
   │   ├── ffplay.exe
   │   └── ffprobe.exe
   ├── doc\
   └── presets\
   ```

4. **配置路径**：
   - 编辑 `center_code/backend/config.py`
   - 设置 `FFMPEG_PATH = r"D:\软件\ffmpeg\bin\ffmpeg.exe"`

### 方法 2：使用 Chocolatey（如果已安装）

```powershell
choco install ffmpeg
```

### 方法 3：添加到系统 PATH

1. 将 FFmpeg 的 `bin` 目录添加到系统 PATH 环境变量
2. 例如：`D:\软件\ffmpeg\bin`
3. 重启终端和后端服务

## 验证安装

在 PowerShell 中运行：
```powershell
ffmpeg -version
```

如果显示版本信息，说明安装成功。

## 配置后端

安装完成后，重启后端服务，代码会自动检测 FFmpeg。

