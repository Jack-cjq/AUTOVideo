<template>
  <div class="video-editor-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>AI视频剪辑</h3>
          <el-button type="primary" @click="handleNewProject">
            <el-icon><Plus /></el-icon>
            新建项目
          </el-button>
        </div>
      </template>

      <!-- 项目列表 -->
      <div class="project-list" v-loading="loading">
        <el-empty v-if="projects.length === 0 && !loading" description="暂无项目，点击新建项目开始剪辑" />
        <el-card
          v-for="project in projects"
          :key="project.id"
          class="project-card"
          shadow="hover"
          @click="handleOpenProject(project)"
        >
          <div class="project-header">
            <h4>{{ project.name }}</h4>
            <div class="project-actions">
              <el-button link type="primary" size="small" @click.stop="handleEdit(project)">编辑</el-button>
              <el-button link type="danger" size="small" @click.stop="handleDelete(project)">删除</el-button>
            </div>
          </div>
          <div class="project-info">
            <div class="info-item">
              <el-icon><VideoPlay /></el-icon>
              <span>视频数量: {{ project.video_count || 0 }}</span>
            </div>
            <div class="info-item">
              <el-icon><Clock /></el-icon>
              <span>创建时间: {{ formatDate(project.created_at) }}</span>
            </div>
            <div class="info-item" v-if="project.status">
              <el-icon><Loading /></el-icon>
              <span>状态: {{ getStatusText(project.status) }}</span>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="pagination.total > 0">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[12, 24, 48]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 新建/编辑项目对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="800px"
    >
      <el-form :model="form" label-width="120px" v-loading="processing">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入项目描述" />
        </el-form-item>
        
        <!-- 视频上传区域 -->
        <el-form-item label="上传视频">
          <el-upload
            class="video-uploader"
            :action="uploadAction"
            :headers="uploadHeaders"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            :file-list="fileList"
            multiple
            accept="video/*"
          >
            <el-button type="primary">
              <el-icon><Upload /></el-icon>
              选择视频文件
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 MP4、AVI、MOV 等格式，单个文件不超过 500MB
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- AI剪辑参数设置 -->
        <el-divider>AI剪辑参数</el-divider>
        
        <el-form-item label="剪辑模式">
          <el-radio-group v-model="form.edit_mode">
            <el-radio label="auto">自动剪辑</el-radio>
            <el-radio label="smart">智能剪辑</el-radio>
            <el-radio label="custom">自定义</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="目标时长" v-if="form.edit_mode !== 'custom'">
          <el-input-number
            v-model="form.target_duration"
            :min="10"
            :max="600"
            :step="10"
            style="width: 200px;"
          />
          <span style="margin-left: 10px;">秒</span>
        </el-form-item>

        <el-form-item label="保留精彩片段">
          <el-switch v-model="form.keep_highlights" />
        </el-form-item>

        <el-form-item label="自动添加字幕">
          <el-switch v-model="form.auto_subtitle" />
        </el-form-item>

        <el-form-item label="背景音乐" v-if="form.edit_mode !== 'custom'">
          <el-select v-model="form.music_style" placeholder="选择音乐风格" clearable style="width: 100%;">
            <el-option label="无音乐" value="none" />
            <el-option label="轻快" value="light" />
            <el-option label="激昂" value="energetic" />
            <el-option label="舒缓" value="relaxing" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item label="转场效果" v-if="form.edit_mode !== 'custom'">
          <el-select v-model="form.transition" placeholder="选择转场效果" clearable style="width: 100%;">
            <el-option label="无转场" value="none" />
            <el-option label="淡入淡出" value="fade" />
            <el-option label="滑动" value="slide" />
            <el-option label="缩放" value="zoom" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="processing">确定</el-button>
      </template>
    </el-dialog>

    <!-- 剪辑工作台对话框 -->
    <el-dialog
      v-model="workspaceVisible"
      title="AI视频剪辑工作台"
      width="90%"
      :close-on-click-modal="false"
      fullscreen
    >
      <div class="workspace" v-if="currentProject">
        <div class="workspace-header">
          <h3>{{ currentProject.name }}</h3>
          <div class="workspace-actions">
            <el-button @click="handlePreview">预览</el-button>
            <el-button type="primary" @click="handleExport">导出视频</el-button>
            <el-button @click="workspaceVisible = false">关闭</el-button>
          </div>
        </div>
        
        <div class="workspace-content">
          <div class="workspace-left">
            <el-card shadow="never">
              <template #header>视频素材</template>
              <div class="video-materials">
                <div
                  v-for="video in currentProject.videos"
                  :key="video.id"
                  class="material-item"
                  :class="{ active: selectedVideo?.id === video.id }"
                  @click="selectVideo(video)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  <span>{{ video.name }}</span>
                  <span class="duration">{{ formatDuration(video.duration) }}</span>
                </div>
              </div>
            </el-card>
          </div>
          
          <div class="workspace-center">
            <el-card shadow="never">
              <template #header>预览窗口</template>
              <div class="preview-area">
                <div class="preview-placeholder">
                  <el-icon size="64"><VideoPlay /></el-icon>
                  <p>视频预览区域</p>
                </div>
              </div>
            </el-card>
          </div>
          
          <div class="workspace-right">
            <el-card shadow="never">
              <template #header>时间轴</template>
              <div class="timeline-area">
                <div class="timeline-placeholder">
                  <el-icon size="64"><Clock /></el-icon>
                  <p>时间轴编辑区域</p>
                </div>
              </div>
            </el-card>
            
            <el-card shadow="never" style="margin-top: 20px;">
              <template #header>AI功能</template>
              <div class="ai-features">
                <el-button @click="handleAICut">智能裁剪</el-button>
                <el-button @click="handleAISubtitle">生成字幕</el-button>
                <el-button @click="handleAIFilter">滤镜美化</el-button>
                <el-button @click="handleAIMusic">配乐推荐</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { 
  getProjects, 
  createProject, 
  updateProject, 
  deleteProject, 
  getProjectDetail,
  startEdit,
  exportVideo
} from '../api/videoEditor'

const authStore = useAuthStore()
const loading = ref(false)
const processing = ref(false)
const projects = ref([])
const currentProject = ref(null)
const selectedVideo = ref(null)

const filters = ref({
  search: ''
})

const pagination = ref({
  page: 1,
  size: 12,
  total: 0
})

const dialogVisible = ref(false)
const workspaceVisible = ref(false)
const form = ref({
  id: null,
  name: '',
  description: '',
  edit_mode: 'auto',
  target_duration: 60,
  keep_highlights: true,
  auto_subtitle: true,
  music_style: '',
  transition: 'fade'
})

const fileList = ref([])

const dialogTitle = computed(() => {
  return form.value.id ? '编辑项目' : '新建项目'
})

const uploadAction = computed(() => {
  return '/api/video-editor/upload'
})

const uploadHeaders = computed(() => {
  return {
    'Authorization': `Bearer ${authStore.token || ''}`
  }
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const formatDuration = (seconds) => {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, '0')}`
}

const getStatusText = (status) => {
  const map = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status] || status
}

const loadProjects = async () => {
  try {
    loading.value = true
    const params = {
      search: filters.value.search || undefined,
      limit: pagination.value.size,
      offset: (pagination.value.page - 1) * pagination.value.size
    }
    
    const response = await getProjects(params)
    if (response.code === 200) {
      projects.value = response.data.projects || []
      pagination.value.total = response.data.total || 0
    }
  } catch (error) {
    ElMessage.error('加载项目列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (size) => {
  pagination.value.size = size
  pagination.value.page = 1
  loadProjects()
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadProjects()
}

const handleNewProject = () => {
  form.value = {
    id: null,
    name: '',
    description: '',
    edit_mode: 'auto',
    target_duration: 60,
    keep_highlights: true,
    auto_subtitle: true,
    music_style: '',
    transition: 'fade'
  }
  fileList.value = []
  dialogVisible.value = true
}

const handleEdit = (project) => {
  form.value = {
    id: project.id,
    name: project.name,
    description: project.description || '',
    edit_mode: project.edit_mode || 'auto',
    target_duration: project.target_duration || 60,
    keep_highlights: project.keep_highlights !== false,
    auto_subtitle: project.auto_subtitle !== false,
    music_style: project.music_style || '',
    transition: project.transition || 'fade'
  }
  fileList.value = []
  dialogVisible.value = true
}

const handleDelete = async (project) => {
  try {
    await ElMessageBox.confirm('确定要删除该项目吗？删除后无法恢复。', '提示', {
      type: 'warning'
    })
    
    const response = await deleteProject(project.id)
    if (response.code === 200) {
      ElMessage.success('删除成功')
      loadProjects()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

const handleOpenProject = async (project) => {
  try {
    loading.value = true
    const response = await getProjectDetail(project.id)
    if (response.code === 200) {
      currentProject.value = response.data
      workspaceVisible.value = true
    }
  } catch (error) {
    ElMessage.error('打开项目失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const beforeUpload = (file) => {
  const isValidType = ['video/mp4', 'video/avi', 'video/mov', 'video/quicktime'].includes(file.type)
  const isLt500M = file.size / 1024 / 1024 < 500

  if (!isValidType) {
    ElMessage.error('只能上传视频文件!')
    return false
  }
  if (!isLt500M) {
    ElMessage.error('视频文件大小不能超过 500MB!')
    return false
  }
  return true
}

const handleUploadSuccess = (response, file) => {
  ElMessage.success('视频上传成功')
  // 这里可以处理上传成功的响应
}

const handleUploadError = (error) => {
  ElMessage.error('视频上传失败')
  console.error(error)
}

const handleSubmit = async () => {
  if (!form.value.name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  
  try {
    processing.value = true
    const data = {
      name: form.value.name,
      description: form.value.description,
      edit_mode: form.value.edit_mode,
      target_duration: form.value.target_duration,
      keep_highlights: form.value.keep_highlights,
      auto_subtitle: form.value.auto_subtitle,
      music_style: form.value.music_style,
      transition: form.value.transition
    }
    
    let response
    if (form.value.id) {
      response = await updateProject(form.value.id, data)
    } else {
      response = await createProject(data)
    }
    
    if (response.code === 200 || response.code === 201) {
      ElMessage.success(form.value.id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      loadProjects()
    }
  } catch (error) {
    ElMessage.error(form.value.id ? '更新失败' : '创建失败')
    console.error(error)
  } finally {
    processing.value = false
  }
}

const selectVideo = (video) => {
  selectedVideo.value = video
}

const handlePreview = () => {
  ElMessage.info('预览功能待实现')
}

const handleExport = async () => {
  try {
    await ElMessageBox.confirm('确定要导出视频吗？', '提示', {
      type: 'info'
    })
    
    processing.value = true
    const response = await exportVideo(currentProject.value.id)
    if (response.code === 200 || response.code === 201) {
      ElMessage.success('导出任务已提交，请稍后查看')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('导出失败')
      console.error(error)
    }
  } finally {
    processing.value = false
  }
}

const handleAICut = () => {
  ElMessage.info('智能裁剪功能待实现')
}

const handleAISubtitle = () => {
  ElMessage.info('生成字幕功能待实现')
}

const handleAIFilter = () => {
  ElMessage.info('滤镜美化功能待实现')
}

const handleAIMusic = () => {
  ElMessage.info('配乐推荐功能待实现')
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.video-editor-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.project-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.project-card:hover {
  transform: translateY(-4px);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.project-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.project-actions {
  display: flex;
  gap: 8px;
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.video-uploader {
  width: 100%;
}

.workspace {
  height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
}

.workspace-header h3 {
  margin: 0;
}

.workspace-actions {
  display: flex;
  gap: 12px;
}

.workspace-content {
  flex: 1;
  display: grid;
  grid-template-columns: 250px 1fr 300px;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}

.workspace-left,
.workspace-center,
.workspace-right {
  overflow-y: auto;
}

.video-materials {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.material-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.material-item:hover {
  background: #f5f7fa;
  border-color: #409eff;
}

.material-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}

.material-item .duration {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

.preview-area {
  width: 100%;
  height: 400px;
  background: #000;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-placeholder {
  color: #909399;
  text-align: center;
}

.preview-placeholder p {
  margin-top: 16px;
}

.timeline-area {
  width: 100%;
  height: 200px;
  background: #f5f7fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.timeline-placeholder {
  color: #909399;
  text-align: center;
}

.timeline-placeholder p {
  margin-top: 16px;
}

.ai-features {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-features .el-button {
  width: 100%;
}
</style>

