<template>
  <div class="data-center-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>数据中心</h3>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filters">
        <el-select v-model="filters.platform" placeholder="选择平台" clearable style="width: 150px; margin-right: 10px;">
          <el-option label="抖音" value="douyin" />
          <el-option label="快手" value="kuaishou" />
          <el-option label="小红书" value="xiaohongshu" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 300px; margin-right: 10px;"
        />
        <el-button type="primary" @click="loadStats">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 左侧账号列表 -->
        <div class="left-panel">
          <el-card shadow="hover" style="margin-bottom: 20px;">
            <template #header>
              <div class="card-header">
                <h4>{{ selectedPlatformLabel }}授权账号</h4>
              </div>
            </template>
            <el-table :data="filteredAccounts" style="width: 100%" v-loading="accountLoading" stripe>
              <el-table-column prop="account_name" label="账号名称" min-width="150" show-overflow-tooltip>
                <template #default="scope">
                  <el-button 
                    type="text" 
                    @click="handleAccountClick(scope.row)"
                    :class="{ 'selected': selectedAccount?.id === scope.row.id }"
                  >
                    {{ scope.row.account_name }}
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column prop="platform" label="平台" width="100">
                <template #default="scope">
                  <el-tag size="small">{{ scope.row.platform }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <!-- 右侧账号和视频数据 -->
        <div class="right-panel">
          <div v-loading="selectedAccountLoading" class="right-panel-loading">
            <!-- 账号数据卡片 -->
            <el-card shadow="hover" v-if="selectedAccount && Object.keys(selectedAccountStats).length > 0" style="margin-bottom: 20px;">
              <template #header>
                <div class="card-header">
                  <h4>{{ selectedAccount.account_name }} 账号数据</h4>
                </div>
              </template>
              <div class="account-stats">
                <div class="stat-item">
                  <div class="stat-label">发布视频数</div>
                  <div class="stat-value">{{ selectedAccountStats.published_videos || 0 }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">总粉丝数</div>
                  <div class="stat-value">{{ selectedAccountStats.total_followers || 0 }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">净增粉丝数</div>
                  <div class="stat-value" :class="selectedAccountStats.net_followers > 0 ? 'text-success' : (selectedAccountStats.net_followers < 0 ? 'text-danger' : '')">
                    {{ selectedAccountStats.net_followers > 0 ? '+' : '' }}{{ selectedAccountStats.net_followers || 0 }}
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 视频数据列表 -->
            <el-card shadow="hover" v-if="selectedAccount && videoStatsList.length > 0">
              <template #header>
                <div class="card-header">
                  <h4>{{ selectedAccount.account_name }} 视频数据</h4>
                </div>
              </template>
              <el-table :data="videoStatsList" style="width: 100%" stripe>
                <el-table-column prop="video_title" label="视频标题" min-width="200" show-overflow-tooltip />
                <el-table-column prop="publish_time" label="发布时间" width="180" align="center" sortable>
                  <template #default="scope">
                    {{ 
                      scope.row.status === 'completed' && scope.row.completed_at 
                        ? formatDate(scope.row.completed_at) 
                        : scope.row.created_at 
                        ? formatDate(scope.row.created_at) 
                        : '-' 
                    }}
                  </template>
                </el-table-column>
                <el-table-column prop="playbacks" label="播放量" width="120" align="center" sortable />
                <el-table-column prop="likes" label="点赞数" width="120" align="center" sortable />
                <el-table-column prop="comments" label="评论数" width="120" align="center" sortable />
                <el-table-column prop="shares" label="分享数" width="120" align="center" sortable />
              </el-table>
              
              <!-- 分页组件 -->
              <div class="pagination-container">
                <el-pagination
                  v-model:current-page="currentPage"
                  v-model:page-size="pageSize"
                  :page-sizes="[5, 10, 20, 50, 100]"
                  :total="totalVideos"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="handleSizeChange"
                  @current-change="handleCurrentChange"
                  style="margin-top: 20px; text-align: center;"
                />
              </div>
            </el-card>
          </div>
          
          <!-- 数据加载中提示 -->
          <el-empty v-if="selectedAccount && !selectedAccountLoading && Object.keys(selectedAccountStats).length === 0 && videoStatsList.length === 0" description="暂无数据" />
          
          <!-- 未选择账号提示 -->
          <el-empty v-else-if="!selectedAccount" description="请从左侧选择一个账号查看详情" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getVideoStats, getAccountRanking, getAccountVideos } from '../api/dataCenter'
import api from '../api'

const loading = ref(false)
const accountLoading = ref(false)
const videoStatsLoading = ref(false)
const selectedAccountLoading = ref(false) // 用于管理当前选中账号数据的加载状态
const stats = ref({})
const accounts = ref([])
const dateRange = ref([])
const videoStatsList = ref([])

// 分页相关变量
const currentPage = ref(1)
const pageSize = ref(5)
const totalVideos = ref(0)

// 选择的账号和对应的统计数据
const selectedAccount = ref(null)
const selectedAccountStats = ref({})

const filters = ref({
  platform: 'douyin',
  account_id: null
})

// 根据平台筛选后的账号列表
const filteredAccounts = computed(() => {
  if (!filters.value.platform) {
    return accounts.value
  }
  return accounts.value.filter(account => account.platform === filters.value.platform)
})

// 当前选择的平台显示标签
const selectedPlatformLabel = computed(() => {
  const platformMap = {
    'douyin': '抖音',
    'kuaishou': '快手',
    'xiaohongshu': '小红书'
  }
  return filters.value.platform ? platformMap[filters.value.platform] : '所有'
})

// 监听平台选择变化，当切换到无账号的平台时，重置选中的账号和相关数据
watch(
  () => filters.value.platform,
  (newPlatform, oldPlatform) => {
    if (newPlatform !== oldPlatform) {
      // 获取新平台下的账号列表
      const accountsForNewPlatform = accounts.value.filter(account => account.platform === newPlatform)
      
      // 如果新平台下没有账号，则重置选中的账号和相关数据
      if (accountsForNewPlatform.length === 0) {
        selectedAccount.value = null
        selectedAccountStats.value = {}
        videoStatsList.value = []
      } else if (selectedAccount.value) {
        // 如果新平台下有账号，检查当前选中的账号是否属于新平台
        const isCurrentAccountInNewPlatform = accountsForNewPlatform.some(account => account.id === selectedAccount.value.id)
        
        // 如果当前选中的账号不属于新平台，则重置选中的账号和相关数据
        if (!isCurrentAccountInNewPlatform) {
          selectedAccount.value = null
          selectedAccountStats.value = {}
          videoStatsList.value = []
        }
      }
    }
  }
)

const loadStats = async () => {
  try {
    loading.value = true
    const params = {
      platform: filters.value.platform || undefined,
      account_id: selectedAccount.value?.id || undefined
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString()
      params.end_date = dateRange.value[1].toISOString()
    }
    
    const response = await getVideoStats(params)
    if (response.code === 200) {
      stats.value = response.data
    }
    
  } catch (error) {
    ElMessage.error('加载统计数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadAccounts = async () => {
  try {
    accountLoading.value = true
    const response = await api.accounts.list({ limit: 1000 })
    if (response && response.code === 200) {
      const list = response.data?.accounts || response.data || []
      accounts.value = Array.isArray(list) ? list : []
    }
  } catch (error) {
    console.error('加载账号列表失败:', error)
  } finally {
    accountLoading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    platform: '',
    account_id: null
  }
  dateRange.value = []
  selectedAccount.value = null
  selectedAccountStats.value = {}
  videoStatsList.value = []
  loadStats()
}

// 处理账号点击事件
const handleAccountClick = async (account) => {
  // 立即重置当前选中账号的所有相关状态，避免数据残留
  selectedAccount.value = null
  selectedAccountStats.value = {}
  videoStatsList.value = []
  
  // 然后设置新选中的账号
  selectedAccount.value = account
  
  // 加载新账号的数据
  await loadAccountData(account)
}

// 加载账号数据和视频数据
const loadAccountData = async (account) => {
  selectedAccountLoading.value = true
  try {
    // 再次确保所有相关数据已重置
    selectedAccountStats.value = {}
    videoStatsList.value = []
    
    // 加载账号统计数据
    const accountParams = {
      account_id: account.id
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      accountParams.start_date = dateRange.value[0].toISOString()
      accountParams.end_date = dateRange.value[1].toISOString()
    }
    
    // 获取账号统计数据
    const accountStatsResponse = await getVideoStats(accountParams)
    if (accountStatsResponse.code === 200) {
      selectedAccountStats.value = {
        published_videos: accountStatsResponse.data.published_videos || 0,
        total_followers: accountStatsResponse.data.total_followers || 0,
        net_followers: accountStatsResponse.data.net_followers || 0
      }
    }
    
    // 获取视频列表数据（带分页）
    const videosResponse = await getAccountVideos({
      account_id: account.id,
      page: currentPage.value,
      page_size: pageSize.value
    })
    if (videosResponse.code === 200) {
      videoStatsList.value = videosResponse.data.videos || []
      totalVideos.value = videosResponse.data.total || 0
    }
  } catch (error) {
    console.error('加载账号数据失败:', error)
    ElMessage.error('加载账号数据失败')
    
    // 发生错误时确保状态也是干净的
    selectedAccountStats.value = {}
    videoStatsList.value = []
  } finally {
    selectedAccountLoading.value = false
  }
}

// 日期格式化
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 处理页面大小变化
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1 // 重置到第一页
  if (selectedAccount.value) {
    loadAccountData(selectedAccount.value)
  }
}

// 处理当前页码变化
const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
  if (selectedAccount.value) {
    loadAccountData(selectedAccount.value)
  }
}

onMounted(() => {
  loadAccounts()
  loadStats()
})
</script>

<style scoped>
.data-center-page {
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

/* 主要内容区域布局 */
.main-content {
  display: flex;
  gap: 20px;
}

/* 左侧面板 */
.left-panel {
  width: 300px;
  flex-shrink: 0;
}

/* 右侧面板 */
.right-panel {
  flex: 1;
  min-width: 0;
}

/* 账号统计数据样式 */
.account-stats {
  display: flex;
  gap: 20px;
  justify-content: center;
  padding: 20px 0;
}

.stat-item {
  text-align: center;
  flex: 1;
  max-width: 200px;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

/* 选中账号的高亮样式 */
.selected {
  color: #409eff;
  font-weight: bold;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .main-content {
    flex-direction: column;
  }
  
  .left-panel {
    width: 100%;
  }
  
  .account-stats {
    flex-direction: column;
    align-items: center;
  }
}
</style>
