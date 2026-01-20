<template>
  <div class="publish-history-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>发布历史</h3>
        </div>
      </template>

      <!-- 标签页切换 -->
      <el-tabs v-model="activeTab" type="card" @tab-change="handleTabChange">
        <el-tab-pane label="立即发布历史" name="instant">
          <el-table :data="instantHistory" stripe style="width: 100%" v-loading="instantLoading">
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
                {{ formatDateTime(row.created_at) }}
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
              :current-page="instantPagination.page"
              :page-size="instantPagination.size"
              :total="instantPagination.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @size-change="(size) => { instantPagination.size = size; loadInstantHistory(); }"
              @current-change="(page) => { instantPagination.page = page; loadInstantHistory(); }"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="发布计划历史" name="plan">
          <el-table :data="planHistory" stripe style="width: 100%" v-loading="planLoading">
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
            <el-table-column prop="scheduled_time" label="计划时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.scheduled_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="publish_time" label="实际发布时间" width="180">
              <template #default="{ row }">
                {{ row.completed_at ? formatDateTime(row.completed_at) : '-' }}
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
              :current-page="planPagination.page"
              :page-size="planPagination.size"
              :total="planPagination.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @size-change="(size) => { planPagination.size = size; loadPlanHistory(); }"
              @current-change="(page) => { planPagination.page = page; loadPlanHistory(); }"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import * as publishPlanApi from '../api/publishPlans'

// 标签页
const activeTab = ref('instant')

// 立即发布历史
const instantHistory = ref([])
const instantLoading = ref(false)
const instantPagination = ref({
  page: 1,
  size: 10,
  total: 0
})

// 发布计划历史
const planHistory = ref([])
const planLoading = ref(false)
const planPagination = ref({
  page: 1,
  size: 10,
  total: 0
})

// 格式化日期时间
const formatDateTime = (datetime) => {
  if (!datetime) return '-'
  try {
    return new Date(datetime).toLocaleString('zh-CN')
  } catch (e) {
    return datetime
  }
}

// 获取平台文本
const getPlatformText = (platform) => {
  const platformMap = {
    'douyin': '抖音',
    'kuaishou': '快手',
    'xiaohongshu': '小红书',
    'bilibili': 'B站'
  }
  return platformMap[platform] || platform
}

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    'pending': 'warning',
    'processing': 'info',
    'completed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'pending': '待发布',
    'processing': '发布中',
    'completed': '已发布',
    'failed': '发布失败'
  }
  return statusMap[status] || status
}

// 加载立即发布历史
const loadInstantHistory = async () => {
  instantLoading.value = true
  try {
    const params = {
      page: instantPagination.value.page,
      size: instantPagination.value.size
    }
    const response = await api.post('/publish/history', params)
    if (response.code === 200) {
      instantHistory.value = response.data?.list || []
      instantPagination.value.total = response.data?.total || 0
    } else {
      ElMessage.error(response.message || '加载立即发布历史失败')
    }
  } catch (error) {
    console.error('加载立即发布历史失败:', error)
    ElMessage.error('加载立即发布历史失败')
  } finally {
    instantLoading.value = false
  }
}

// 加载发布计划历史
const loadPlanHistory = async () => {
  planLoading.value = true
  try {
    const params = {
      page: planPagination.value.page,
      size: planPagination.value.size
    }
    const response = await publishPlanApi.getPublishPlans(params)
    if (response.code === 200) {
      planHistory.value = response.data?.items || []
      planPagination.value.total = response.data?.total || 0
    } else {
      ElMessage.error(response.message || '加载发布计划历史失败')
    }
  } catch (error) {
    console.error('加载发布计划历史失败:', error)
    ElMessage.error('加载发布计划历史失败')
  } finally {
    planLoading.value = false
  }
}

// 处理标签页切换
const handleTabChange = (tab) => {
  if (tab === 'instant' && instantHistory.value.length === 0) {
    loadInstantHistory()
  } else if (tab === 'plan' && planHistory.value.length === 0) {
    loadPlanHistory()
  }
}

// 查看详情
const handleViewDetail = (row) => {
  // 这里可以跳转到详情页面或显示详情对话框
  console.log('查看详情:', row)
  ElMessage.info('详情功能待实现')
}

// 删除任务
const handleDeleteTask = async (row) => {
  try {
    if (activeTab.value === 'instant') {
      await api.video.deleteTask(row.id)
    } else {
      await publishPlanApi.deletePublishPlan(row.id)
    }
    ElMessage.success('删除成功')
    // 重新加载数据
    if (activeTab.value === 'instant') {
      loadInstantHistory()
    } else {
      loadPlanHistory()
    }
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

// 初始化
onMounted(() => {
  loadInstantHistory()
})
</script>

<style scoped>
.publish-history-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>