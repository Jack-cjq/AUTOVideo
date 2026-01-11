<template>
  <div class="video-library-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>云视频库</h3>
          <el-button type="primary" @click="handleUpload">
            <el-icon><Upload /></el-icon>
            上传视频
          </el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filters">
        <el-select v-model="filters.platform" placeholder="选择平台" clearable style="width: 150px; margin-right: 10px;">
          <el-option label="抖音" value="douyin" />
          <el-option label="快手" value="kuaishou" />
          <el-option label="小红书" value="xiaohongshu" />
        </el-select>
        <el-input
          v-model="filters.search"
          placeholder="搜索视频名称"
          style="width: 250px; margin-right: 10px;"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="loadVideos">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <!-- 视频列表 -->
      <div class="video-grid" v-loading="loading">
        <el-card
          v-for="video in videos"
          :key="video.id"
          class="video-card"
          shadow="hover"
        >
          <div class="video-thumbnail" @click="handlePreview(video)">
            <el-image
              v-if="video.thumbnail_url"
              :src="video.thumbnail_url"
              fit="cover"
              style="width: 100%; height: 200px;"
            />
            <div v-else class="video-placeholder">
              <el-icon size="48"><VideoPlay /></el-icon>
            </div>
            <div class="video-duration" v-if="video.duration">
              {{ formatDuration(video.duration) }}
            </div>
          </div>
          <div class="video-info">
            <div class="video-name" :title="video.video_name">{{ video.video_name }}</div>
            <div class="video-meta">
              <span v-if="video.platform">{{ getPlatformText(video.platform) }}</span>
              <span v-if="video.video_size">{{ formatFileSize(video.video_size) }}</span>
            </div>
            <div class="video-actions">
              <el-button link type="primary" size="small" @click="handleEdit(video)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(video)">删除</el-button>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[12, 24, 48, 96]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 上传/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item label="视频名称" required>
          <el-input v-model="form.video_name" placeholder="请输入视频名称" />
        </el-form-item>
        <el-form-item label="视频URL" required>
          <el-input v-model="form.video_url" placeholder="请输入视频URL" />
        </el-form-item>
        <el-form-item label="缩略图URL">
          <el-input v-model="form.thumbnail_url" placeholder="请输入缩略图URL" />
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="form.platform" placeholder="请选择平台" clearable style="width: 100%;">
            <el-option label="抖音" value="douyin" />
            <el-option label="快手" value="kuaishou" />
            <el-option label="小红书" value="xiaohongshu" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="请输入标签，用逗号分隔" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getVideos, uploadVideo, updateVideo, deleteVideo } from '../api/videoLibrary'

const loading = ref(false)
const videos = ref([])

const filters = ref({
  platform: '',
  search: ''
})

const pagination = ref({
  page: 1,
  size: 24,
  total: 0
})

const dialogVisible = ref(false)
const form = ref({
  id: null,
  video_name: '',
  video_url: '',
  thumbnail_url: '',
  platform: '',
  tags: '',
  description: ''
})

const dialogTitle = computed(() => {
  return form.value.id ? '编辑视频' : '上传视频'
})

const getPlatformText = (platform) => {
  const map = {
    'douyin': '抖音',
    'kuaishou': '快手',
    'xiaohongshu': '小红书'
  }
  return map[platform] || platform
}

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${String(secs).padStart(2, '0')}`
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

const loadVideos = async () => {
  try {
    loading.value = true
    const params = {
      platform: filters.value.platform || undefined,
      search: filters.value.search || undefined,
      limit: pagination.value.size,
      offset: (pagination.value.page - 1) * pagination.value.size
    }
    
    const response = await getVideos(params)
      if (response.code === 200) {
        videos.value = response.data.videos
        pagination.value.total = response.data.total
      }
  } catch (error) {
    ElMessage.error('加载视频列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    platform: '',
    search: ''
  }
  loadVideos()
}

const handleSizeChange = (size) => {
  pagination.value.size = size
  pagination.value.page = 1
  loadVideos()
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadVideos()
}

const handleUpload = () => {
  form.value = {
    id: null,
    video_name: '',
    video_url: '',
    thumbnail_url: '',
    platform: '',
    tags: '',
    description: ''
  }
  dialogVisible.value = true
}

const handlePreview = (video) => {
  // 视频预览功能待实现
}

const handleEdit = (row) => {
  form.value = {
    id: row.id,
    video_name: row.video_name,
    video_url: row.video_url,
    thumbnail_url: row.thumbnail_url,
    platform: row.platform,
    tags: row.tags,
    description: row.description
  }
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该视频吗？', '提示', {
      type: 'warning'
    })
    
    const response = await deleteVideo(row.id)
      if (response.code === 200) {
        ElMessage.success('删除成功')
        loadVideos()
      }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

const handleSubmit = async () => {
  if (!form.value.video_name || !form.value.video_url) {
    ElMessage.warning('请输入视频名称和视频URL')
    return
  }
  
  try {
    const data = {
      video_name: form.value.video_name,
      video_url: form.value.video_url,
      thumbnail_url: form.value.thumbnail_url,
      platform: form.value.platform,
      tags: form.value.tags,
      description: form.value.description
    }
    
    let response
    if (form.value.id) {
      response = await updateVideo(form.value.id, data)
    } else {
      response = await uploadVideo(data)
    }
    
    if (response.code === 200 || response.code === 201) {
        ElMessage.success(form.value.id ? '更新成功' : '上传成功')
        dialogVisible.value = false
        loadVideos()
      } else {
        ElMessage.error(response.message || (form.value.id ? '更新失败' : '上传失败'))
      }
  } catch (error) {
    ElMessage.error(form.value.id ? '更新失败' : '上传失败')
    console.error(error)
  }
}

onMounted(() => {
  loadVideos()
})
</script>

<style scoped>
.video-library-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.video-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.video-card:hover {
  transform: translateY(-4px);
}

.video-thumbnail {
  position: relative;
  width: 100%;
  height: 200px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
}

.video-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #909399;
}

.video-duration {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 2px 6px;
  border-radius: 2px;
  font-size: 12px;
}

.video-info {
  padding: 12px 0;
}

.video-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-meta {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.video-meta span {
  margin-right: 12px;
}

.video-actions {
  display: flex;
  gap: 8px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
