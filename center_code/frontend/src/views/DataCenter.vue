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
        <el-select v-model="filters.account_id" placeholder="选择账号" clearable filterable style="width: 200px; margin-right: 10px;">
          <el-option
            v-for="account in accounts"
            :key="account.id"
            :label="account.account_name"
            :value="account.id"
          />
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

      <!-- 统计数据卡片 -->
      <div class="stats-cards">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">授权账号</div>
          <div class="stat-value">{{ stats.authorized_accounts || 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">发布视频数</div>
          <div class="stat-value">{{ stats.published_videos || 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">总粉丝数</div>
          <div class="stat-value">{{ stats.total_followers || 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">播放量</div>
          <div class="stat-value">{{ stats.playbacks || 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">点赞数</div>
          <div class="stat-value">{{ stats.likes || 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">评论数</div>
          <div class="stat-value">{{ stats.comments || 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">净增粉丝数</div>
          <div class="stat-value">{{ stats.net_followers || 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <div class="stat-label">分享数</div>
          <div class="stat-value">{{ stats.shares || 0 }}</div>
        </el-card>
      </div>

      <!-- 账号数据明细 -->
      <el-card class="account-ranking-card" shadow="never" style="margin-top: 20px;">
        <template #header>
          <div class="card-header">
            <h4>账号数据明细</h4>
          </div>
        </template>
        <el-table :data="accountRankings" style="width: 100%" v-loading="rankingLoading" stripe>
          <el-table-column prop="account_name" label="账号名称" min-width="150" show-overflow-tooltip>
            <template #default="scope">
              <el-button type="text" @click="handleAccountClick(scope.row)">
                {{ scope.row.account_name }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="platform" label="平台" width="100">
            <template #default="scope">
              <el-tag size="small">{{ scope.row.platform }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="published_videos" label="发布视频数" sortable width="120" align="center" />
          <el-table-column prop="total_followers" label="总粉丝数" sortable width="120" align="center" />
          <el-table-column prop="playbacks" label="播放量" sortable width="120" align="center" />
          <el-table-column prop="likes" label="点赞数" sortable width="120" align="center" />
          <el-table-column prop="comments" label="评论数" sortable width="120" align="center" />
          <el-table-column prop="net_followers" label="净增粉丝数" sortable width="120" align="center">
            <template #default="scope">
              <span :class="scope.row.net_followers > 0 ? 'text-success' : (scope.row.net_followers < 0 ? 'text-danger' : '')">
                {{ scope.row.net_followers > 0 ? '+' : '' }}{{ scope.row.net_followers }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="shares" label="分享数" sortable width="120" align="center" />
        </el-table>
      </el-card>

      <!-- 图表区域 -->
      <el-card class="chart-card" shadow="never" style="margin-top: 20px;">
        <template #header>
          <h4>数据趋势</h4>
        </template>
        <div class="chart-placeholder">
          <!-- 图表功能待实现 -->
        </div>
      </el-card>
    </el-card>

    <!-- 视频数据对话框 -->
    <el-dialog
      v-model="videoDialogVisible"
      :title="videoDialogTitle"
      width="800px"
    >
      <el-table :data="videoStatsList" style="width: 100%" v-loading="videoStatsLoading" stripe>
        <el-table-column prop="video_title" label="视频标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="publish_date" label="发布日期" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.publish_date) }}
          </template>
        </el-table-column>
        <el-table-column prop="playbacks" label="播放量" width="120" align="center" sortable />
        <el-table-column prop="likes" label="点赞数" width="120" align="center" sortable />
        <el-table-column prop="comments" label="评论数" width="120" align="center" sortable />
        <el-table-column prop="shares" label="分享数" width="120" align="center" sortable />
      </el-table>
      <template #footer>
        <el-button @click="videoDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getVideoStats, getAccountRanking } from '../api/dataCenter'
import api from '../api'

const loading = ref(false)
const rankingLoading = ref(false)
const stats = ref({})
const accountRankings = ref([])
const accounts = ref([])
const dateRange = ref([])

// 视频数据对话框
const videoDialogVisible = ref(false)
const videoStatsLoading = ref(false)
const videoStatsList = ref([])
const selectedAccount = ref(null)
const videoDialogTitle = computed(() => {
  return selectedAccount.value ? `${selectedAccount.value.account_name} 的视频数据` : '视频数据'
})

const filters = ref({
  platform: '',
  account_id: null
})

const loadAccountRanking = async () => {
  try {
    rankingLoading.value = true
    const params = {
      platform: filters.value.platform || undefined,
      // 如果选择了账号，也可以筛选，虽然通常是看列表
      // account_id: filters.value.account_id || undefined 
    }
    const response = await getAccountRanking(params)
    if (response.code === 200) {
      accountRankings.value = response.data
    }
  } catch (error) {
    console.error('加载账号明细失败', error)
  } finally {
    rankingLoading.value = false
  }
}

const loadStats = async () => {
  try {
    loading.value = true
    const params = {
      platform: filters.value.platform || undefined,
      account_id: filters.value.account_id || undefined
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString()
      params.end_date = dateRange.value[1].toISOString()
    }
    
    const response = await getVideoStats(params)
            if (response.code === 200) {
              stats.value = response.data
            }
    
    // 同时加载账号明细
    loadAccountRanking()
    
  } catch (error) {
    ElMessage.error('加载统计数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadAccounts = async () => {
  try {
    const response = await api.accounts.list({ limit: 1000 })
    if (response && response.code === 200) {
      const list = response.data?.accounts || response.data || []
      accounts.value = Array.isArray(list) ? list : []
    }
  } catch (error) {
    console.error('加载账号列表失败:', error)
  }
}

const resetFilters = () => {
  filters.value = {
    platform: '',
    account_id: null
  }
  dateRange.value = []
  loadStats()
}

// 处理账号点击事件
const handleAccountClick = async (account) => {
  selectedAccount.value = account
  videoDialogVisible.value = true
  await loadVideoStats(account.account_id)
}

// 加载视频统计数据
const loadVideoStats = async (accountId) => {
  try {
    videoStatsLoading.value = true
    const response = await getVideoStats({ account_id: accountId })
    if (response.code === 200) {
      videoStatsList.value = response.data.videos
    }
  } catch (error) {
    console.error('加载视频统计数据失败:', error)
    ElMessage.error('加载视频统计数据失败')
  } finally {
    videoStatsLoading.value = false
  }
}

// 日期格式化
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
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

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-top: 20px;
}

.stat-card {
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}

.chart-card {
  min-height: 400px;
}

.chart-placeholder {
  text-align: center;
  padding: 100px 0;
  color: #909399;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}
</style>
