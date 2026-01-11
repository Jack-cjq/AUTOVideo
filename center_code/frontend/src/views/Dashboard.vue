<template>
  <div class="dashboard">
    <!-- 视频数据统计区域 -->
    <el-card class="video-data-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <h3>视频数据</h3>
            <p class="subtitle">最近统计: {{ dateRange }}</p>
          </div>
          <div class="platform-selector">
            <el-radio-group v-model="selectedPlatform" size="small">
              <el-radio-button label="douyin">
                <el-icon><VideoPlay /></el-icon>
                抖音
              </el-radio-button>
              <el-radio-button label="kuaishou">
                <el-icon><VideoPlay /></el-icon>
                快手
              </el-radio-button>
              <el-radio-button label="xiaohongshu">
                <el-icon><VideoPlay /></el-icon>
                小红书
              </el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div class="filters">
          <el-input
            v-model="searchAccount"
            placeholder="搜索账号"
            style="width: 200px; margin-right: 10px;"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="timeRange" style="width: 120px;">
            <el-option label="最近7天" value="7" />
            <el-option label="最近30天" value="30" />
            <el-option label="最近90天" value="90" />
          </el-select>
        </div>
      </template>
      
      <!-- KPI 指标卡片 -->
      <div class="kpi-grid">
        <div class="kpi-item" v-for="kpi in kpiList" :key="kpi.key">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value">{{ kpi.value }}</div>
          <el-icon class="kpi-arrow" v-if="kpi.clickable"><ArrowRight /></el-icon>
        </div>
      </div>
    </el-card>
    
    <div class="content-row">
      <!-- 私信/评论区域 -->
      <el-card class="message-card" shadow="never">
        <el-tabs v-model="messageTab">
          <el-tab-pane label="私信" name="private">
            <div class="message-empty">
              <p>共收到{{ privateMessageCount }}条私信,<a href="#" @click.prevent>去看看</a></p>
            </div>
          </el-tab-pane>
          <el-tab-pane label="评论" name="comment">
            <div class="message-empty">
              <p>共收到{{ commentCount }}条评论,<a href="#" @click.prevent>去看看</a></p>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
    
    <!-- 最近发布计划 -->
    <el-card class="publish-plan-card" shadow="never">
      <template #header>
        <div class="card-header">
          <h3>最近发布计划</h3>
          <div class="header-actions">
            <el-select v-model="planPlatform" size="small" style="width: 100px; margin-right: 10px;">
              <el-option label="抖音" value="douyin" />
              <el-option label="快手" value="kuaishou" />
              <el-option label="小红书" value="xiaohongshu" />
            </el-select>
            <el-link type="primary" :underline="false">查看全部 ></el-link>
          </div>
        </div>
      </template>
      
      <el-table :data="safePublishPlans" stripe style="width: 100%">
        <el-table-column prop="id" label="发布计划ID" width="120" />
        <el-table-column label="计划名称" width="250">
          <template #default="{ row }">
            <div class="plan-name-cell">
              <el-image
                v-if="row.thumbnail"
                :src="row.thumbnail"
                style="width: 40px; height: 40px; margin-right: 10px;"
                fit="cover"
              />
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="videoCount" label="视频数" width="80" />
        <el-table-column prop="merchant" label="关联商家" width="120" />
        <el-table-column prop="published" label="发布成功" width="100" />
        <el-table-column prop="pending" label="待发布" width="100" />
        <el-table-column prop="claimed" label="已领取" width="100" />
        <el-table-column prop="accountCount" label="账号数量" width="100" />
        <el-table-column prop="distributionMode" label="分发模式" width="140" />
        <el-table-column prop="status" label="发布状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="publishTime" label="发布时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small">查看</el-button>
            <el-button link type="primary" size="small" v-if="row.status === '待发布'">保存发布信息</el-button>
            <el-button link type="primary" size="small" v-if="row.status === '待发布'">添加视频</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { getVideoStats } from '../api/dataCenter'
import { getPublishPlans } from '../api/publishPlans'
import api from '../api'

const router = useRouter()

const selectedPlatform = ref('douyin')
const searchAccount = ref('')
const timeRange = ref('7')
const messageTab = ref('private')
const planPlatform = ref('douyin')
const loading = ref(false)

const dateRange = computed(() => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - parseInt(timeRange.value))
  return `${formatDate(start)}~${formatDate(end)}`
})

const formatDate = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const kpiList = ref([
  { key: 'accounts', label: '授权账号', value: 0, clickable: true },
  { key: 'videos', label: '发布视频数', value: 0, clickable: true },
  { key: 'followers', label: '截止昨日总粉丝数', value: 0, clickable: true },
  { key: 'playbacks', label: '播放量', value: 0, clickable: true },
  { key: 'likes', label: '点赞数', value: 0, clickable: true },
  { key: 'comments', label: '评论数', value: 0, clickable: true },
  { key: 'newFollowers', label: '近7天净增粉丝数', value: 0, clickable: true },
  { key: 'shares', label: '分享数', value: 0, clickable: true }
])

const privateMessageCount = ref(0)
const commentCount = ref(0)
const publishPlans = ref([])

// 确保表格数据始终是数组的计算属性
const safePublishPlans = computed(() => {
  const plans = publishPlans.value
  if (!Array.isArray(plans)) {
    console.warn('publishPlans is not an array, converting to array:', plans)
    return []
  }
  return plans
})

// 加载视频统计数据
const loadVideoStats = async () => {
  try {
    loading.value = true
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - parseInt(timeRange.value))
    
    const response = await getVideoStats({
      platform: selectedPlatform.value,
      start_date: start.toISOString(),
      end_date: end.toISOString()
    })
    
    if (response.code === 200) {
              const data = response.data
              kpiList.value[0].value = data.authorized_accounts || 0
      kpiList.value[1].value = data.published_videos || 0
      kpiList.value[2].value = data.total_followers || 0
      kpiList.value[3].value = data.playbacks || 0
      kpiList.value[4].value = data.likes || 0
      kpiList.value[5].value = data.comments || 0
      kpiList.value[6].value = data.net_followers || 0
      kpiList.value[7].value = data.shares || 0
    }
  } catch (error) {
    // 如果是401错误，不显示错误（已经由拦截器处理）
    if (error.code !== 401) {
      console.error('加载视频统计数据失败:', error)
    }
  } finally {
    loading.value = false
  }
}

// 加载发布计划
const loadPublishPlans = async () => {
  try {
    const response = await getPublishPlans({
      platform: planPlatform.value,
      limit: 10,
      offset: 0
            })
            
            if (response && response.code === 200 && response.data) {
              // 确保 plans 是数组
      let plans = []
      if (Array.isArray(response.data.plans)) {
        plans = response.data.plans
      } else if (Array.isArray(response.data)) {
        plans = response.data
      } else if (response.data.plans && typeof response.data.plans === 'object') {
        // 如果是对象，尝试转换为数组
        plans = Object.values(response.data.plans)
      }
      
      // 确保 plans 是数组后再 map
      if (!Array.isArray(plans)) {
        console.warn('Plans is not an array after processing:', plans)
        plans = []
      }
      
      publishPlans.value = plans.map(plan => ({
        id: plan.id,
        name: plan.plan_name,
        thumbnail: '',
        videoCount: plan.video_count || 0,
        merchant: plan.merchant_name || '',
        published: plan.published_count || 0,
        pending: plan.pending_count || 0,
        claimed: plan.claimed_count || 0,
        accountCount: plan.account_count || 0,
        distributionMode: getDistributionModeText(plan.distribution_mode),
        status: getStatusText(plan.status),
        publishTime: plan.publish_time ? new Date(plan.publish_time).toLocaleString('zh-CN') : ''
      }))
    } else {
      // 如果响应格式不对，设置为空数组
      publishPlans.value = []
    }
  } catch (error) {
    // 如果是401错误，不显示错误（已经由拦截器处理）
    if (error.code !== 401) {
      console.error('加载发布计划失败:', error)
    }
    // 确保 publishPlans 始终是数组
    publishPlans.value = []
  }
}

// 加载消息统计
const loadMessageStats = async () => {
  try {
    // TODO: 实现消息统计API
    // const response = await api.messages.getStats({ platform: selectedPlatform.value })
    // privateMessageCount.value = response.data.private_messages || 0
    // commentCount.value = response.data.comments || 0
  } catch (error) {
    console.error('加载消息统计失败:', error)
  }
}

const getDistributionModeText = (mode) => {
  const map = {
    'manual': '手动分发',
    'sms': '接收短信派发',
    'qrcode': '扫二维码派发',
    'ai': 'AI智能分发'
  }
  return map[mode] || mode
}

const getStatusText = (status) => {
  const map = {
    'pending': '待发布',
    'publishing': '发布中',
    'completed': '发布成功',
    'failed': '发布失败'
  }
  return map[status] || status
}

const getStatusType = (status) => {
  const map = {
    '待发布': 'warning',
    '发布中': 'info',
    '发布成功': 'success',
    '发布失败': 'danger'
  }
  return map[status] || 'info'
}

// 监听平台变化
watch([selectedPlatform, timeRange], () => {
  loadVideoStats()
})

watch(planPlatform, () => {
  loadPublishPlans()
})

onMounted(async () => {
  // 先检查登录状态
  const authStore = useAuthStore()
  const isLoggedIn = await authStore.checkLogin()
  
  // 只有登录后才加载数据
  if (isLoggedIn) {
    loadVideoStats()
    loadPublishPlans()
    loadMessageStats()
  }
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.video-data-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.subtitle {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #909399;
}

.platform-selector {
  margin-left: auto;
}

.filters {
  display: flex;
  align-items: center;
  margin-top: 15px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-top: 20px;
}

.kpi-item {
  position: relative;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.kpi-item:hover {
  background: #e6f7ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.kpi-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.kpi-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.kpi-arrow {
  position: absolute;
  right: 15px;
  top: 50%;
  transform: translateY(-50%);
  color: #909399;
}

.content-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.message-card {
  min-height: 200px;
}

.message-empty {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}

.message-empty a {
  color: #409eff;
  text-decoration: none;
}

.message-empty a:hover {
  text-decoration: underline;
}

.publish-plan-card {
  margin-top: 20px;
}

.header-actions {
  display: flex;
  align-items: center;
}

.plan-name-cell {
  display: flex;
  align-items: center;
}
</style>

