# 素材库（Materials）

后端素材库统一使用 `materials` 表存储素材记录，并把文件写入 `center_code/uploads/materials/`。

## 支持类型

- 视频：`uploads/materials/videos/`（`.mp4` / `.avi` / `.mov`）
- 音频：`uploads/materials/audios/`（`.mp3` / `.wav` / `.flac`）
- 图片：`uploads/materials/images/`（`.jpg` / `.jpeg` / `.png` / `.gif` / `.webp`）

## API

- 上传素材：`POST /api/material/upload`（`multipart/form-data`，字段名 `file`）
- 获取素材列表：`GET /api/materials?type=video|audio|image`（不传 `type` 返回全部）
- 清空素材库：`POST /api/materials/clear`（`{"confirm": true}`）
- 删除单个素材：`POST /api/delete-material`

说明：当前剪辑轨道只支持添加视频/音频；图片素材用于管理与预览（后续可扩展为封面/贴图等用途）。

