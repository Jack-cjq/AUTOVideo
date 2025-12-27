<template>
  <div class="publish-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>立即发布</h3>
          <el-button type="info" @click="showHistory = !showHistory">
            <el-icon><Clock /></el-icon>
            {{ showHistory ? '隐藏' : '查看' }}发布历史
          </el-button>
        </div>
      </template>

      <!-- 发布历史 -->
      <el-collapse-transition>
        <div v-show="showHistory" class="history-section">
          <h4>最近发布记录</h4>
          <el-table :data="safePublishHistory" stripe style="width: 100%" v-loading="historyLoading">
            <el-table-column prop="video_title" label="视频标题" min-width="150" />
            <el-table-column prop="account_name" label="发布账号" width="120" />
            <el-table-column prop="platform" label="平台" width="100">
              <template #default="{ row }">
                {{ getPlatformText(row.platform) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="发布时间" width="180">
              <template #default="{ row }">
                {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="120">
              <template #default="{ row }">
                <el-progress 
                  :percentage="row.progress || 0" 
                  :status="row.status === 'failed' ? 'exception' : (row.status === 'completed' ? 'success' : '')"
                  :stroke-width="8"
                />
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.error_message" style="color: #f56c6c;">{{ row.error_message }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="handleViewDetail(row)">详情</el-button>
                <el-button link type="danger" size="small" @click="handleDeleteTask(row)" v-if="row.status === 'pending' || row.status === 'failed'">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper">
            <el-pagination
              :current-page="historyPagination.page"
              :page-size="historyPagination.size"
              :total="historyPagination.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @size-change="(size) => { historyPagination.size = size; loadPublishHistory(); }"
              @current-change="(page) => { historyPagination.page = page; loadPublishHistory(); }"
            />
          </div>
        </div>
      </el-collapse-transition>

      <!-- 发布表单 -->
      <el-steps :active="currentStep" finish-status="success" style="margin: 30px 0;">
        <el-step title="选择视频" />
        <el-step title="选择账号" />
        <el-step title="编辑信息" />
        <el-step title="发布设置" />
      </el-steps>

      <el-form :model="form" label-width="140px" style="max-width: 1000px; margin: 0 auto;">
        <!-- 步骤1: 选择视频 -->
        <div v-show="currentStep === 0" class="step-content">
          <el-card shadow="hover">
            <template #header>
              <span>选择视频</span>
            </template>
            <el-radio-group v-model="videoSource" @change="handleVideoSourceChange">
              <el-radio label="url">输入视频URL</el-radio>
              <el-radio label="library">从视频库选择</el-radio>
            </el-radio-group>

            <div v-if="videoSource === 'url'" style="margin-top: 20px;">
              <el-form-item label="视频URL" required>
                <el-input
                  v-model="form.video_url"
                  placeholder="请输入视频URL或上传视频文件"
                  clearable
                >
                  <template #append>
                    <el-button @click="handleUploadVideo">上传</el-button>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item label="视频预览">
                <div class="video-preview">
                  <video
                    v-if="form.video_url && isVideoUrl(form.video_url)"
                    :src="form.video_url"
                    controls
                    style="max-width: 100%; max-height: 300px;"
                  />
                  <el-image
                    v-else-if="form.thumbnail_url"
                    :src="form.thumbnail_url"
                    fit="cover"
                    style="max-width: 300px; max-height: 300px; border-radius: 4px;"
                  />
                  <div v-else class="preview-placeholder">
                    <el-icon size="48"><VideoPlay /></el-icon>
                    <p>视频预览</p>
                  </div>
                </div>
              </el-form-item>
            </div>

            <div v-if="videoSource === 'library'" style="margin-top: 20px;">
              <el-form-item label="选择视频" required>
                <el-select
                  v-model="form.video_id"
                  placeholder="请从视频库选择视频"
                  filterable
                  style="width: 100%;"
                  @change="handleVideoSelect"
                >
                  <el-option
                    v-for="video in videoLibrary"
                    :key="video.id"
                    :label="video.video_name || video.video_url"
                    :value="video.id"
                  >
                    <div style="display: flex; align-items: center;">
                      <el-image
                        v-if="video.thumbnail_url"
                        :src="video.thumbnail_url"
                        style="width: 60px; height: 40px; margin-right: 10px; border-radius: 4px;"
                        fit="cover"
                      />
                      <span>{{ video.video_name || video.video_url }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              <el-button type="primary" link @click="loadVideoLibrary">刷新视频库</el-button>
            </div>
          </el-card>
        </div>

        <!-- 步骤2: 选择账号 -->
        <div v-show="currentStep === 1" class="step-content">
          <el-card shadow="hover">
            <template #header>
              <span>选择发布账号</span>
            </template>
            <el-form-item label="平台筛选">
              <el-checkbox-group v-model="selectedPlatforms" @change="filterAccounts">
                <el-checkbox label="douyin">抖音</el-checkbox>
                <el-checkbox label="kuaishou">快手</el-checkbox>
                <el-checkbox label="xiaohongshu">小红书</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="选择账号" required>
              <el-select
                v-model="form.account_ids"
                placeholder="请选择发布账号（可多选）"
                multiple
                filterable
                style="width: 100%;"
                collapse-tags
                collapse-tags-tooltip
              >
                <el-option
                  v-for="account in filteredAccounts"
                  :key="account.id"
                  :label="`${account.account_name} (${getPlatformText(account.platform)})`"
                  :value="account.id"
                >
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span>{{ account.account_name }} ({{ getPlatformText(account.platform) }})</span>
                    <el-tag size="small" type="success" v-if="account.login_status === 'logged_in'">
                      已登录
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" link @click="selectAllAccounts">全选当前平台</el-button>
              <el-button link @click="clearAllAccounts">清空选择</el-button>
            </el-form-item>
            <div v-if="form.account_ids && form.account_ids.length > 0" class="selected-accounts">
              <el-tag
                v-for="accountId in form.account_ids"
                :key="accountId"
                closable
                @close="removeAccount(accountId)"
                style="margin: 5px;"
              >
                {{ getAccountName(accountId) }}
              </el-tag>
            </div>
          </el-card>
        </div>

        <!-- 步骤3: 编辑信息 -->
        <div v-show="currentStep === 2" class="step-content">
          <el-card shadow="hover">
            <template #header>
              <span>编辑视频信息</span>
            </template>
            <el-form-item label="视频标题" required>
              <el-input
                v-model="form.video_title"
                placeholder="请输入视频标题"
                maxlength="100"
                show-word-limit
                clearable
              />
            </el-form-item>
            <el-form-item label="视频描述">
              <el-input
                v-model="form.video_description"
                type="textarea"
                :rows="4"
                placeholder="请输入视频描述"
                maxlength="500"
                show-word-limit
              />
            </el-form-item>
            <el-form-item label="视频标签">
              <el-select
                v-model="form.video_tags_array"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="选择或输入标签"
                style="width: 100%;"
              >
                <el-option
                  v-for="tag in popularTags"
                  :key="tag"
                  :label="tag"
                  :value="tag"
                />
              </el-select>
              <div v-if="form.video_tags_array && form.video_tags_array.length > 0" class="tags-display">
                <el-tag
                  v-for="(tag, index) in form.video_tags_array"
                  :key="index"
                  closable
                  @close="removeTag(index)"
                  style="margin: 5px 5px 5px 0;"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </el-form-item>
            <el-form-item label="封面图片">
              <el-input
                v-model="form.thumbnail_url"
                placeholder="请输入封面图片URL"
                clearable
              >
                <template #append>
                  <el-button @click="handleUploadThumbnail">上传</el-button>
                </template>
              </el-input>
              <div v-if="form.thumbnail_url" class="thumbnail-preview" style="margin-top: 10px;">
                <el-image
                  :src="form.thumbnail_url"
                  fit="cover"
                  style="width: 200px; height: 120px; border-radius: 4px;"
                  :preview-src-list="[form.thumbnail_url]"
                />
              </div>
            </el-form-item>
          </el-card>
        </div>

        <!-- 步骤4: 发布设置 -->
        <div v-show="currentStep === 3" class="step-content">
          <el-card shadow="hover">
            <template #header>
              <span>发布设置</span>
            </template>
            <el-form-item label="发布时间">
              <el-radio-group v-model="publishType" @change="handlePublishTypeChange">
                <el-radio label="immediate">立即发布</el-radio>
                <el-radio label="scheduled">定时发布</el-radio>
                <el-radio label="interval">间隔发布</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="publishType === 'scheduled'" label="发布时间">
              <el-date-picker
                v-model="form.publish_date"
                type="datetime"
                placeholder="选择发布时间"
                style="width: 100%;"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </el-form-item>
            <el-form-item v-if="publishType === 'interval'" label="发布间隔">
              <el-input-number
                v-model="publishInterval"
                :min="1"
                :max="1440"
                :step="1"
                style="width: 200px;"
              />
              <span style="margin-left: 10px;">分钟</span>
            </el-form-item>
            <el-form-item label="发布优先级">
              <el-radio-group v-model="form.priority">
                <el-radio label="high">高</el-radio>
                <el-radio label="normal">普通</el-radio>
                <el-radio label="low">低</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="发布后操作">
              <el-checkbox-group v-model="form.after_publish_actions">
                <el-checkbox label="auto_comment">自动评论</el-checkbox>
                <el-checkbox label="auto_like">自动点赞</el-checkbox>
                <el-checkbox label="auto_share">自动分享</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="失败重试">
              <el-switch v-model="form.retry_on_failure" />
              <span v-if="form.retry_on_failure" style="margin-left: 10px;">
                最多重试
                <el-input-number
                  v-model="form.retry_count"
                  :min="1"
                  :max="5"
                  :step="1"
                  style="width: 100px; margin: 0 5px;"
                />
                次
              </span>
            </el-form-item>
          </el-card>
        </div>

        <!-- 操作按钮 -->
        <div class="form-actions">
          <el-button v-if="currentStep > 0" @click="prevStep">上一步</el-button>
          <el-button v-if="currentStep < 3" type="primary" @click="nextStep">下一步</el-button>
          <el-button
            v-if="currentStep === 3"
            type="primary"
            @click="handleSubmit"
            :loading="submitting"
            size="large"
          >
            <el-icon><Promotion /></el-icon>
            立即发布
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 上传视频对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传视频" width="500px">
      <el-upload
        class="upload-demo"
        drag
        :action="uploadAction"
        :headers="uploadHeaders"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">将视频文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 mp4、mov、avi 格式，文件大小不超过 500MB</div>
        </template>
      </el-upload>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, VideoPlay, Promotion, UploadFilled } from '@element-plus/icons-vue'
import api from '../api'
import { getVideos } from '../api/videoLibrary'

const form = ref({
  video_id: null,
  video_url: '',
  video_title: '',
  video_description: '',
  video_tags_array: [],
  thumbnail_url: '',
  account_ids: [],
  publish_date: '',
  priority: 'normal',
  after_publish_actions: [],
  retry_on_failure: false,
  retry_count: 3
})

const accounts = ref([])
const filteredAccounts = ref([])
const videoLibrary = ref([])
const submitting = ref(false)
const currentStep = ref(0)
const videoSource = ref('url')
const selectedPlatforms = ref([])
const publishType = ref('immediate')
const publishInterval = ref(30)
const showHistory = ref(false)

// 监听showHistory变化，自动加载数据
watch(showHistory, (newVal) => {
  if (newVal && publishHistory.value.length === 0) {
    loadPublishHistory()
  }
})
const historyLoading = ref(false)
const publishHistory = ref([])

// 确保表格数据始终是数组的计算属性
const safePublishHistory = computed(() => {
  const history = publishHistory.value
  if (!Array.isArray(history)) {
    console.warn('publishHistory is not an array, converting to array:', history)
    return []
  }
  return history
})
const uploadDialogVisible = ref(false)

const historyPagination = ref({
  page: 1,
  size: 10,
  total: 0
})

const popularTags = ref([
  '搞笑', '美食', '旅游', '音乐', '舞蹈', '宠物', '科技', '时尚', '健身', '教育',
  '生活', '情感', '游戏', '影视', '汽车', '房产', '财经', '健康', '母婴', '美妆'
])

const uploadAction = computed(() => {
  return `${import.meta.env.VITE_API_BASE_URL || '/api'}/publish/upload-video`
})

const uploadHeaders = computed(() => {
  // Element Plus 的 upload 组件会自动设置 Content-Type，不需要手动设置
  // 如果需要添加认证token，可以在这里添加
  return {}
})

const getPlatformText = (platform) => {
  const map = {
    'douyin': '抖音',
    'kuaishou': '快手',
    'xiaohongshu': '小红书'
  }
  return map[platform] || platform
}

const getStatusType = (status) => {
  const map = {
    'pending': 'info',
    'uploading': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'pending': '待发布',
    'uploading': '发布中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status] || status
}

const getAccountStatusType = (status) => {
  const map = {
    'active': 'success',
    'inactive': 'info',
    'error': 'danger'
  }
  return map[status] || 'info'
}

const getAccountStatusText = (status) => {
  const map = {
    'active': '正常',
    'inactive': '未激活',
    'error': '异常'
  }
  return map[status] || status
}

const getAccountName = (accountId) => {
  const account = accounts.value.find(a => a.id === accountId)
  return account ? `${account.account_name} (${getPlatformText(account.platform)})` : ''
}

const isVideoUrl = (url) => {
  return /\.(mp4|mov|avi|flv|wmv|webm)$/i.test(url) || url.startsWith('blob:')
}

const loadAccounts = async () => {
  try {
    const response = await api.accounts.list({ limit: 1000 })
    console.log('账号列表响应:', response)
    
    // 处理不同的响应格式
    if (response && (response.code === 200 || response.success)) {
      let accountsData = []
      
      if (response.data) {
        // 标准格式：{ code: 200, data: { accounts: [...] } }
        if (Array.isArray(response.data.accounts)) {
          accountsData = response.data.accounts
        } else if (Array.isArray(response.data)) {
          accountsData = response.data
        }
      } else if (Array.isArray(response)) {
        // 直接是数组
        accountsData = response
      }
      
      // 只显示已登录的账号（login_status === 'logged_in'）
      accounts.value = accountsData.filter(account => {
        // 检查登录状态
        return account.login_status === 'logged_in'
      })
      filteredAccounts.value = accounts.value
      
      console.log('加载的账号数量:', accounts.value.length)
      console.log('账号列表:', accounts.value)
    } else {
      console.warn('账号列表响应格式不正确:', response)
      accounts.value = []
      filteredAccounts.value = []
    }
  } catch (error) {
    console.error('加载账号列表失败:', error)
    accounts.value = []
    filteredAccounts.value = []
    // 如果是401错误，不显示错误（已经由拦截器处理）
    if (error.code !== 401) {
      ElMessage.error('加载账号列表失败: ' + (error.message || '未知错误'))
    }
  }
}

const loadVideoLibrary = async () => {
  try {
    const response = await getVideos({ limit: 100 })
    if (response.success) {
      videoLibrary.value = response.data.videos || []
    }
  } catch (error) {
    console.error('加载视频库失败:', error)
  }
}

const loadPublishHistory = async () => {
  try {
    historyLoading.value = true
    const response = await api.post('/publish/history', {
      page: historyPagination.value.page,
      size: historyPagination.value.size
    })
    console.log('发布历史响应:', response)
    
    if (response && response.code === 200) {
      const list = response.data?.list || []
      publishHistory.value = Array.isArray(list) ? list : []
      historyPagination.value.total = response.data?.total || 0
      console.log('加载的发布历史数量:', publishHistory.value.length)
      console.log('发布历史数据:', publishHistory.value)
    } else {
      console.error('加载发布历史失败:', response?.message || '未知错误')
      publishHistory.value = []
      historyPagination.value.total = 0
    }
  } catch (error) {
    console.error('加载发布历史失败:', error)
    publishHistory.value = []
    historyPagination.value.total = 0
    // 如果是401错误，不显示错误（已经由拦截器处理）
    if (error.code !== 401) {
      ElMessage.error('加载发布历史失败: ' + (error.message || '未知错误'))
    }
  } finally {
    historyLoading.value = false
  }
}

const filterAccounts = () => {
  if (selectedPlatforms.value.length === 0) {
    filteredAccounts.value = accounts.value
  } else {
    filteredAccounts.value = accounts.value.filter(account =>
      selectedPlatforms.value.includes(account.platform)
    )
  }
}

const selectAllAccounts = () => {
  form.value.account_ids = filteredAccounts.value.map(a => a.id)
}

const clearAllAccounts = () => {
  form.value.account_ids = []
}

const removeAccount = (accountId) => {
  form.value.account_ids = form.value.account_ids.filter(id => id !== accountId)
}

const removeTag = (index) => {
  form.value.video_tags_array.splice(index, 1)
}

const handleVideoSourceChange = () => {
  if (videoSource.value === 'library') {
    loadVideoLibrary()
  }
}

const handleVideoSelect = (videoId) => {
  const video = videoLibrary.value.find(v => v.id === videoId)
  if (video) {
    form.value.video_url = video.video_url
    form.value.video_title = video.video_name || form.value.video_title
    form.value.thumbnail_url = video.thumbnail_url || form.value.thumbnail_url
  }
}

const handleUploadVideo = () => {
  uploadDialogVisible.value = true
}

const handleUploadThumbnail = () => {
  // TODO: 实现上传缩略图功能
  ElMessage.info('上传缩略图功能待实现')
}

const beforeUpload = (file) => {
  const isVideo = /\.(mp4|mov|avi|flv|wmv|webm)$/i.test(file.name)
  const isLt500M = file.size / 1024 / 1024 < 500

  if (!isVideo) {
    ElMessage.error('只能上传视频文件!')
    return false
  }
  if (!isLt500M) {
    ElMessage.error('视频大小不能超过 500MB!')
    return false
  }
  return true
}

const handleUploadSuccess = (response) => {
  // 处理不同的响应格式
  if (response && (response.success || response.code === 200)) {
    const data = response.data || response
    // 构建完整的URL
    const videoUrl = data.url || data
    form.value.video_url = videoUrl.startsWith('http') ? videoUrl : `${window.location.origin}${videoUrl}`
    ElMessage.success('上传成功')
    uploadDialogVisible.value = false
  } else {
    ElMessage.error(response?.message || response?.error || '上传失败')
  }
}

const handleUploadError = () => {
  ElMessage.error('上传失败，请重试')
}

const handlePublishTypeChange = () => {
  if (publishType.value === 'immediate') {
    form.value.publish_date = ''
  }
}

const nextStep = () => {
  if (currentStep.value === 0) {
    if (videoSource.value === 'url' && !form.value.video_url) {
      ElMessage.warning('请输入视频URL')
      return
    }
    if (videoSource.value === 'library' && !form.value.video_id) {
      ElMessage.warning('请选择视频')
      return
    }
  }
  if (currentStep.value === 1) {
    if (!form.value.account_ids || form.value.account_ids.length === 0) {
      ElMessage.warning('请至少选择一个账号')
      return
    }
  }
  if (currentStep.value < 3) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const handleSubmit = async () => {
  if (!form.value.video_url && !form.value.video_id) {
    ElMessage.warning('请选择或输入视频')
    return
  }
  if (!form.value.account_ids || form.value.account_ids.length === 0) {
    ElMessage.warning('请至少选择一个账号')
    return
  }
  if (!form.value.video_title) {
    ElMessage.warning('请输入视频标题')
    return
  }

  try {
    submitting.value = true
    const data = {
      video_id: form.value.video_id,
      video_url: form.value.video_url,
      video_title: form.value.video_title,
      video_description: form.value.video_description,
      video_tags: form.value.video_tags_array,
      thumbnail_url: form.value.thumbnail_url,
      account_ids: form.value.account_ids,
      publish_date: publishType.value === 'scheduled' ? form.value.publish_date : undefined,
      publish_type: publishType.value,
      publish_interval: publishType.value === 'interval' ? publishInterval.value : undefined,
      priority: form.value.priority,
      after_publish_actions: form.value.after_publish_actions,
      retry_on_failure: form.value.retry_on_failure,
      retry_count: form.value.retry_count
    }

    const response = await api.post('/publish/submit', data)
    if (response.code === 200) {
      const taskCount = response.data?.total_tasks || form.value.account_ids.length
      ElMessage.success(`发布任务已创建，共 ${taskCount} 个任务（${form.value.account_ids.length} 个账号）`)
      handleReset()
      // 自动显示发布历史
      if (!showHistory.value) {
        showHistory.value = true
      }
      loadPublishHistory()
    } else {
      ElMessage.error(response.message || '发布失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '发布失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

const handleViewDetail = (row) => {
  ElMessageBox.alert(
    `<div style="text-align: left;">
      <p><strong>任务ID:</strong> ${row.id}</p>
      <p><strong>视频标题:</strong> ${row.video_title || '-'}</p>
      <p><strong>账号:</strong> ${row.account_name || '-'}</p>
      <p><strong>平台:</strong> ${getPlatformText(row.platform)}</p>
      <p><strong>状态:</strong> ${getStatusText(row.status)}</p>
      <p><strong>进度:</strong> ${row.progress || 0}%</p>
      <p><strong>创建时间:</strong> ${row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-'}</p>
      <p><strong>开始时间:</strong> ${row.started_at ? new Date(row.started_at).toLocaleString('zh-CN') : '-'}</p>
      <p><strong>完成时间:</strong> ${row.completed_at ? new Date(row.completed_at).toLocaleString('zh-CN') : '-'}</p>
      ${row.error_message ? `<p><strong>错误信息:</strong> <span style="color: #f56c6c;">${row.error_message}</span></p>` : ''}
    </div>`,
    '任务详情',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '关闭'
    }
  )
}

const handleDeleteTask = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？', '提示', {
      type: 'warning'
    })
    
    const response = await api.video.deleteTask(row.id)
    if (response.code === 200) {
      ElMessage.success('删除成功')
      loadPublishHistory()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
      console.error(error)
    }
  }
}

const handleReset = () => {
  form.value = {
    video_id: null,
    video_url: '',
    video_title: '',
    video_description: '',
    video_tags_array: [],
    thumbnail_url: '',
    account_ids: [],
    publish_date: '',
    priority: 'normal',
    after_publish_actions: [],
    retry_on_failure: false,
    retry_count: 3
  }
  currentStep.value = 0
  videoSource.value = 'url'
  selectedPlatforms.value = []
  publishType.value = 'immediate'
  publishInterval.value = 30
}

onMounted(() => {
  loadAccounts()
})
</script>

<style scoped>
.publish-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.history-section h4 {
  margin: 0 0 15px 0;
  color: #303133;
}

.pagination-wrapper {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}

.step-content {
  margin: 30px 0;
}

.selected-accounts {
  margin-top: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  min-height: 40px;
}

.tags-display {
  margin-top: 10px;
}

.thumbnail-preview {
  display: flex;
  align-items: center;
}

.video-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 20px;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.preview-placeholder p {
  margin: 10px 0 0 0;
  font-size: 14px;
}

.form-actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 15px;
  padding: 20px 0;
}

.upload-demo {
  width: 100%;
}
</style>
