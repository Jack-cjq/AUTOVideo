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
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getVideoStats } from '../api/dataCenter'
import api from '../api'

const loading = ref(false)
const stats = ref({})
const accounts = ref([])
const dateRange = ref([])

const filters = ref({
  platform: '',
  account_id: null
})

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
    if (response.success) {
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
    const response = await api.accounts.list({ limit: 1000 })
    if (response.success) {
      accounts.value = response.data.accounts || []
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
</style>
