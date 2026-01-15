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
            <el-table-column prop="publish_time" label="发布时间" width="180">
              <template #default="{ row }">
                {{
                  row.status === 'completed' && row.completed_at
                    ? new Date(row.completed_at).toLocaleString('zh-CN')
                    : row.created_at
                    ? new Date(row.created_at).toLocaleString('zh-CN')
                    : '-'
                }}
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
              <el-radio label="upload">本地上传</el-radio>
              <el-radio label="library">从视频库选择</el-radio>
            </el-radio-group>

            <div v-if="videoSource === 'upload'" style="margin-top: 20px;">
              <el-form-item label="上传视频" required>
                <el-upload
                  class="video-uploader"
                  :action="uploadAction"
                  :headers="uploadHeaders"
                  :on-success="handleUploadSuccess"
                  :on-error="handleUploadError"
                  :before-upload="beforeUpload"
                  :show-file-list="false"
                  accept="video/*"
                >
                  <el-button type="primary">
                    <el-icon><UploadFilled /></el-icon>
                    选择视频文件
                  </el-button>
                  <template #tip>
                    <div class="el-upload__tip">支持 mp4、mov、avi 格式，文件大小不超过 500MB</div>
                  </template>
                </el-upload>
                <div v-if="form.video_url" style="margin-top: 10px;">
                  <el-text type="success" size="small">
                    <el-icon><Check /></el-icon>
                    已上传: {{ getVideoFileName(form.video_url) }}
                  </el-text>
                  <el-button 
                    link 
                    type="danger" 
                    size="small" 
                    @click="clearVideo"
                    style="margin-left: 10px;"
                  >
                    清除
                  </el-button>
                </div>
              </el-form-item>
              <el-form-item label="视频预览">
                <div class="video-preview">
                  <video
                    v-if="form.video_url"
                    :key="form.video_url"
                    :src="getVideoPreviewUrl(form.video_url)"
                    controls
                    preload="metadata"
                    style="max-width: 100%; max-height: 300px;"
                    @error="handleVideoError"
                    @loadedmetadata="handleVideoLoaded"
                    @loadstart="handleVideoLoadStart"
                  >
                    您的浏览器不支持视频播放
                  </video>
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
                        :src="getThumbnailPreviewUrl(video.thumbnail_url)"
                        style="width: 60px; height: 40px; margin-right: 10px; border-radius: 4px;"
                        fit="cover"
                      />
                      <span>{{ video.video_name || video.video_url }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              <el-button type="primary" link @click="loadVideoLibrary">刷新视频库</el-button>
              <el-form-item label="视频预览" style="margin-top: 20px;">
                <div class="video-preview">
                  <video
                    v-if="form.video_url"
                    :key="form.video_url"
                    :src="getVideoPreviewUrl(form.video_url)"
                    controls
                    preload="metadata"
                    style="max-width: 100%; max-height: 300px;"
                    @error="handleVideoError"
                    @loadedmetadata="handleVideoLoaded"
                    @loadstart="handleVideoLoadStart"
                  >
                    您的浏览器不支持视频播放
                  </video>
                  <div v-else class="preview-placeholder">
                    <el-icon size="48"><VideoPlay /></el-icon>
                    <p>请先选择视频</p>
                  </div>
                </div>
              </el-form-item>
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
                <el-checkbox label="douyin">
                  抖音
                  <el-text type="info" size="small" style="margin-left: 5px;">
                    ({{ getPlatformAccountCount('douyin') }})
                  </el-text>
                </el-checkbox>
                <el-checkbox label="kuaishou">
                  快手
                  <el-text type="info" size="small" style="margin-left: 5px;">
                    ({{ getPlatformAccountCount('kuaishou') }})
                  </el-text>
                </el-checkbox>
                <el-checkbox label="xiaohongshu">
                  小红书
                  <el-text type="info" size="small" style="margin-left: 5px;">
                    ({{ getPlatformAccountCount('xiaohongshu') }})
                  </el-text>
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="选择账号" required>
              <div style="margin-bottom: 10px;">
                <el-text type="info" size="small">
                  已选择 {{ form.account_ids.length }} 个账号
                  <span v-if="filteredAccounts.length > 0">
                    / 当前筛选显示 {{ filteredAccounts.length }} 个账号
                  </span>
                </el-text>
              </div>
              <el-select
                v-model="form.account_ids"
                placeholder="请选择发布账号（可多选）"
                multiple
                filterable
                style="width: 100%;"
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="3"
                @change="handleAccountChange"
              >
                <el-option
                  v-for="account in filteredAccounts"
                  :key="account.id"
                  :label="`${account.account_name} (${getPlatformText(account.platform)})`"
                  :value="account.id"
                  :disabled="account.login_status !== 'logged_in'"
                >
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <span>{{ account.account_name }}</span>
                      <el-tag size="small" :type="getPlatformTagType(account.platform)">
                        {{ getPlatformText(account.platform) }}
                      </el-tag>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <el-tag 
                        size="small" 
                        :type="account.login_status === 'logged_in' ? 'success' : 'warning'"
                        v-if="account.login_status"
                      >
                        {{ account.login_status === 'logged_in' ? '已登录' : '未登录' }}
                      </el-tag>
                    </div>
                  </div>
                </el-option>
              </el-select>
              <div v-if="filteredAccounts.length === 0" style="margin-top: 10px;">
                <el-text type="warning" size="small">
                  <el-icon style="margin-right: 5px;"><Warning /></el-icon>
                  当前筛选条件下没有可用的账号
                </el-text>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary" 
                link 
                @click="selectAllAccounts"
                :disabled="filteredAccounts.length === 0"
              >
                全选当前平台 ({{ filteredAccounts.length }})
              </el-button>
              <el-button 
                link 
                @click="clearAllAccounts"
                :disabled="form.account_ids.length === 0"
              >
                清空选择
              </el-button>
              <el-button 
                link 
                type="info"
                @click="clearPlatformFilter"
                v-if="selectedPlatforms.length > 0"
              >
                清除平台筛选
              </el-button>
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
                placeholder="选择或输入标签（最多10个）"
                style="width: 100%;"
                :max-collapse-tags="3"
                collapse-tags
                collapse-tags-tooltip
                @change="handleTagsChange"
              >
                <el-option
                  v-for="tag in popularTags"
                  :key="tag"
                  :label="tag"
                  :value="tag"
                />
              </el-select>
              <div v-if="form.video_tags_array && form.video_tags_array.length > 0" class="tags-display" style="margin-top: 10px;">
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
              <div v-if="form.video_tags_array && form.video_tags_array.length >= 10" style="margin-top: 5px;">
                <el-text type="warning" size="small">最多只能添加10个标签</el-text>
              </div>
            </el-form-item>
            <el-form-item label="封面图片">
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <el-upload
                  class="thumbnail-uploader"
                  :action="thumbnailUploadAction"
                  :headers="uploadHeaders"
                  :on-success="handleThumbnailUploadSuccess"
                  :on-error="handleThumbnailUploadError"
                  :before-upload="beforeThumbnailUpload"
                  :show-file-list="false"
                  accept="image/*"
                >
                  <el-button type="primary">
                    <el-icon><UploadFilled /></el-icon>
                    上传封面图片
                  </el-button>
                  <template #tip>
                    <div class="el-upload__tip">支持 jpg、png、gif 格式，文件大小不超过 5MB</div>
                  </template>
                </el-upload>
                <el-input
                  v-model="form.thumbnail_url"
                  placeholder="或输入封面图片URL"
                  clearable
                  style="margin-top: 10px;"
                />
                <div v-if="form.thumbnail_url" class="thumbnail-preview" style="margin-top: 10px;">
                  <el-image
                    :src="getThumbnailPreviewUrl(form.thumbnail_url)"
                    fit="cover"
                    style="width: 200px; height: 120px; border-radius: 4px; cursor: pointer;"
                    :preview-src-list="[getThumbnailPreviewUrl(form.thumbnail_url)]"
                    @error="handleThumbnailError"
                  />
                  <el-button 
                    link 
                    type="danger" 
                    size="small" 
                    @click="clearThumbnail"
                    style="margin-left: 10px;"
                  >
                    清除
                  </el-button>
                </div>
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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, VideoPlay, Promotion, UploadFilled, Warning, Check } from '@element-plus/icons-vue'
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
const videoSource = ref('upload')
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

const thumbnailUploadAction = computed(() => {
  return `${import.meta.env.VITE_API_BASE_URL || '/api'}/publish/upload-thumbnail`
})

const uploadHeaders = computed(() => {
  // Element Plus 的 upload 组件会自动设置 Content-Type，不需要手动设置
  // 添加认证 token
  const token = localStorage.getItem('auth_token')
  const headers = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
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
    if (response && response.code === 200) {
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
      
      // 初始化筛选后的账号列表（根据当前平台筛选）
      filterAccounts()
      
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
    if (response.code === 200) {
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

// 获取平台账号数量
const getPlatformAccountCount = (platform) => {
  return accounts.value.filter(account => account.platform === platform).length
}

// 获取平台标签类型
const getPlatformTagType = (platform) => {
  const typeMap = {
    'douyin': 'danger',
    'kuaishou': 'warning',
    'xiaohongshu': 'warning'
  }
  return typeMap[platform] || 'info'
}

// 筛选账号
const filterAccounts = () => {
  if (selectedPlatforms.value.length === 0) {
    // 如果没有选择平台，显示所有已登录的账号
    filteredAccounts.value = accounts.value.filter(account => 
      account.login_status === 'logged_in'
    )
  } else {
    // 根据选择的平台筛选，只显示已登录的账号
    filteredAccounts.value = accounts.value.filter(account =>
      selectedPlatforms.value.includes(account.platform) &&
      account.login_status === 'logged_in'
    )
  }
  
  // 如果当前已选择的账号不在筛选结果中，从选择列表中移除
  const validAccountIds = filteredAccounts.value.map(a => a.id)
  form.value.account_ids = form.value.account_ids.filter(id => 
    validAccountIds.includes(id) || accounts.value.find(a => a.id === id)
  )
}

// 全选当前平台账号
const selectAllAccounts = () => {
  // 只选择已登录的账号
  const availableAccounts = filteredAccounts.value.filter(
    account => account.login_status === 'logged_in'
  )
  
  if (availableAccounts.length === 0) {
    ElMessage.warning('当前筛选条件下没有可用的已登录账号')
    return
  }
  
  // 合并已选择的账号和新选择的账号（去重）
  const newAccountIds = availableAccounts.map(a => a.id)
  const existingIds = form.value.account_ids || []
  form.value.account_ids = [...new Set([...existingIds, ...newAccountIds])]
  
  ElMessage.success(`已选择 ${newAccountIds.length} 个账号`)
}

// 清空选择
const clearAllAccounts = () => {
  if (form.value.account_ids.length === 0) {
    return
  }
  
  form.value.account_ids = []
  ElMessage.info('已清空所有选择')
}

// 清除平台筛选
const clearPlatformFilter = () => {
  selectedPlatforms.value = []
  filterAccounts()
  ElMessage.info('已清除平台筛选')
}

// 账号选择变化处理
const handleAccountChange = (selectedIds) => {
  // 验证选择的账号是否都是已登录状态
  const invalidAccounts = selectedIds.filter(id => {
    const account = accounts.value.find(a => a.id === id)
    return account && account.login_status !== 'logged_in'
  })
  
  if (invalidAccounts.length > 0) {
    ElMessage.warning('只能选择已登录的账号')
    // 移除未登录的账号
    form.value.account_ids = selectedIds.filter(id => !invalidAccounts.includes(id))
  }
}

// 移除单个账号
const removeAccount = (accountId) => {
  const index = form.value.account_ids.indexOf(accountId)
  if (index > -1) {
    form.value.account_ids.splice(index, 1)
  }
}

const removeTag = (index) => {
  form.value.video_tags_array.splice(index, 1)
}

// 标签变化处理
const handleTagsChange = (tags) => {
  // 限制最多10个标签
  if (tags && tags.length > 10) {
    form.value.video_tags_array = tags.slice(0, 10)
    ElMessage.warning('最多只能添加10个标签')
  }
  // 去除重复标签
  if (tags && tags.length > 0) {
    form.value.video_tags_array = [...new Set(tags)]
  }
}

const handleVideoSourceChange = () => {
  if (videoSource.value === 'library') {
    loadVideoLibrary()
  } else if (videoSource.value === 'upload') {
    // 切换到本地上传时，清空视频URL
    form.value.video_url = ''
    form.value.video_id = null
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

// 获取视频文件名
const getVideoFileName = (url) => {
  if (!url) return ''
  // 从路径中提取文件名
  const parts = url.split('/')
  return parts[parts.length - 1] || url
}

// 获取视频预览URL
const getVideoPreviewUrl = (url) => {
  if (!url) return ''
  // 如果是相对路径（如 /uploads/videos/filename.mp4），添加完整的基础URL
  if (url.startsWith('/')) {
    // 使用后端 API 基础 URL 构建完整的URL
    // 如果设置了 VITE_API_BASE_URL，使用它；否则使用默认的后端地址
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api'
    // 从 API base URL 中提取基础 URL（去掉 /api 后缀）
    const baseUrl = apiBaseUrl.replace(/\/api\/?$/, '')
    const fullUrl = baseUrl + url
    return fullUrl
  }
  // 如果已经是完整URL，直接返回
  return url
}

// 视频加载错误处理
const handleVideoError = (event) => {
  const video = event.target
  const src = video.src
  console.error('视频加载失败:', {
    src: src,
    error: video.error,
    networkState: video.networkState,
    readyState: video.readyState
  })
  
  // 显示更详细的错误信息
  let errorMsg = '视频加载失败'
  if (video.error) {
    switch (video.error.code) {
      case video.error.MEDIA_ERR_ABORTED:
        errorMsg = '视频加载被中止'
        break
      case video.error.MEDIA_ERR_NETWORK:
        errorMsg = '网络错误，无法加载视频'
        break
      case video.error.MEDIA_ERR_DECODE:
        errorMsg = '视频解码失败'
        break
      case video.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
        errorMsg = '视频格式不支持或文件不存在'
        break
      default:
        errorMsg = `视频加载失败 (错误代码: ${video.error.code})`
    }
  }
  
  ElMessage.error(errorMsg)
}

// 视频加载开始
const handleVideoLoadStart = (event) => {
  console.log('视频开始加载:', event.target.src)
}

// 视频加载成功
const handleVideoLoaded = (event) => {
  console.log('视频加载成功:', event.target.src)
  console.log('视频时长:', event.target.duration, '秒')
}

// 清除视频
const clearVideo = () => {
  form.value.video_url = ''
  form.value.video_id = null
}

// 封面图片上传前验证
const beforeThumbnailUpload = (file) => {
  const isImage = /\.(jpg|jpeg|png|gif|webp|bmp)$/i.test(file.name)
  const isLt5M = file.size / 1024 / 1024 < 5

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过 5MB!')
    return false
  }
  return true
}

// 封面图片上传成功
const handleThumbnailUploadSuccess = (response) => {
  console.log('封面图片上传响应:', response)
  if (response && response.code === 200) {
    const data = response.data || response
    const thumbnailUrl = data.url || data
    console.log('存储的封面图片URL:', thumbnailUrl)
    form.value.thumbnail_url = thumbnailUrl
    ElMessage.success('封面图片上传成功')
  } else {
    console.error('封面图片上传失败，响应:', response)
    ElMessage.error(response?.message || response?.error || '上传失败')
  }
}

// 封面图片上传失败
const handleThumbnailUploadError = () => {
  ElMessage.error('封面图片上传失败，请重试')
}

// 获取封面图片预览URL
// 获取封面图片预览URL
const getThumbnailPreviewUrl = (url) => {
  if (!url) return ''
  // 如果是相对路径（如 /uploads/thumbnails/filename.jpg），添加完整的基础URL
  if (url.startsWith('/')) {
    // 使用后端 API 基础 URL 构建完整的URL
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api'
    // 从 API base URL 中提取基础 URL（去掉 /api 后缀）
    const baseUrl = apiBaseUrl.replace(/\/api\/?$/, '')
    return baseUrl + url
  }
  // 如果已经是完整URL，直接返回
  return url
}

// 封面图片加载错误
const handleThumbnailError = () => {
  ElMessage.warning('封面图片加载失败')
}

// 清除封面图片
const clearThumbnail = () => {
  form.value.thumbnail_url = ''
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
  console.log('上传响应:', response)
  // 处理不同的响应格式
  if (response && response.code === 200) {
    const data = response.data || response
    // 存储访问路径（后端返回的路径格式如：/uploads/videos/filename.mp4）
    const videoUrl = data.url || data
    console.log('存储的视频URL:', videoUrl)
    // 确保存储的是相对路径，用于数据库存储
    form.value.video_url = videoUrl
    console.log('form.video_url 已设置为:', form.value.video_url)
    
    // 如果视频标题为空，尝试从文件名提取
    if (!form.value.video_title && data.filename) {
      const filenameWithoutExt = data.filename.replace(/\.(mp4|mov|avi|flv|wmv|webm|mkv)$/i, '')
      // 移除时间戳前缀（格式：20251228_132342_）
      const title = filenameWithoutExt.replace(/^\d{8}_\d{6}_/, '')
      if (title) {
        form.value.video_title = title
      }
    }
    
    ElMessage.success('上传成功')
  } else {
    console.error('上传失败，响应:', response)
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
    if (videoSource.value === 'upload' && !form.value.video_url) {
      ElMessage.warning('请上传视频文件')
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
  if (currentStep.value === 2) {
    // 验证视频信息
    if (!form.value.video_title || form.value.video_title.trim() === '') {
      ElMessage.warning('请输入视频标题')
      return
    }
    if (form.value.video_title.length > 100) {
      ElMessage.warning('视频标题不能超过100个字符')
      return
    }
    if (form.value.video_description && form.value.video_description.length > 500) {
      ElMessage.warning('视频描述不能超过500个字符')
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
      loadPublishHistory().then(() => {
        // 提交任务后，如果有正在进行的任务，开始轮询
        if (hasRunningTasks.value) {
          startPolling()
        }
      })
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
  videoSource.value = 'upload'
  selectedPlatforms.value = []
  publishType.value = 'immediate'
  publishInterval.value = 30
}

// 任务状态轮询
let pollTimer = null
const POLL_INTERVAL = 3000 // 3秒轮询一次

// 检查是否有正在进行的任务
const hasRunningTasks = computed(() => {
  return publishHistory.value.some(task => 
    task.status === 'pending' || task.status === 'uploading'
  )
})

// 开始轮询任务状态
const startPolling = () => {
  // 如果已经有定时器，先清除
  if (pollTimer) {
    clearInterval(pollTimer)
  }
  
  // 如果有正在进行的任务且历史记录可见，开始轮询
  if (hasRunningTasks.value && showHistory.value) {
    pollTimer = setInterval(() => {
      if (hasRunningTasks.value && showHistory.value) {
        loadPublishHistory()
      } else {
        // 没有正在进行的任务，停止轮询
        stopPolling()
      }
    }, POLL_INTERVAL)
    console.log('[轮询] 开始轮询任务状态，间隔:', POLL_INTERVAL, 'ms')
  }
}

// 停止轮询
const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
    console.log('[轮询] 停止轮询任务状态')
  }
}

// 监听任务状态变化，自动开始/停止轮询
watch([hasRunningTasks, showHistory], ([hasRunning, isVisible]) => {
  if (hasRunning && isVisible) {
    startPolling()
  } else {
    stopPolling()
  }
}, { immediate: true })

onMounted(() => {
  loadAccounts()
})

onUnmounted(() => {
  // 组件卸载时清除定时器
  stopPolling()
})

onUnmounted(() => {
  // 组件卸载时清除定时器
  stopPolling()
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

.video-uploader {
  width: 100%;
}

.video-uploader .el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>
