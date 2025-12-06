<template>
  <div class="publish-plan-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>发布计划管理</h3>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建发布计划
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
        <el-select v-model="filters.status" placeholder="选择状态" clearable style="width: 150px; margin-right: 10px;">
          <el-option label="待发布" value="pending" />
          <el-option label="发布中" value="publishing" />
          <el-option label="发布成功" value="completed" />
          <el-option label="发布失败" value="failed" />
        </el-select>
        <el-input
          v-model="filters.search"
          placeholder="搜索计划名称"
          style="width: 250px; margin-right: 10px;"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="loadPlans">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <!-- 表格 -->
      <el-table :data="plans" v-loading="loading" stripe style="width: 100%; margin-top: 20px;">
        <el-table-column prop="id" label="计划ID" width="100" />
        <el-table-column prop="plan_name" label="计划名称" min-width="200" />
        <el-table-column prop="platform" label="平台" width="100">
          <template #default="{ row }">
            <el-tag>{{ getPlatformText(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="merchant_name" label="关联商家" width="150" />
        <el-table-column prop="video_count" label="视频数" width="100" />
        <el-table-column prop="published_count" label="已发布" width="100" />
        <el-table-column prop="pending_count" label="待发布" width="100" />
        <el-table-column prop="distribution_mode" label="分发模式" width="150">
          <template #default="{ row }">
            {{ getDistributionModeText(row.distribution_mode) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="publish_time" label="发布时间" width="180">
          <template #default="{ row }">
            {{ row.publish_time ? new Date(row.publish_time).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item label="计划名称" required>
          <el-input v-model="form.plan_name" placeholder="请输入计划名称" />
        </el-form-item>
        <el-form-item label="平台" required>
          <el-select v-model="form.platform" placeholder="请选择平台" style="width: 100%;">
            <el-option label="抖音" value="douyin" />
            <el-option label="快手" value="kuaishou" />
            <el-option label="小红书" value="xiaohongshu" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联商家">
          <el-select v-model="form.merchant_id" placeholder="请选择商家" clearable style="width: 100%;">
            <el-option
              v-for="merchant in merchants"
              :key="merchant.id"
              :label="merchant.merchant_name"
              :value="merchant.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="分发模式">
          <el-select v-model="form.distribution_mode" placeholder="请选择分发模式" style="width: 100%;">
            <el-option label="手动分发" value="manual" />
            <el-option label="接收短信派发" value="sms" />
            <el-option label="扫二维码派发" value="qrcode" />
            <el-option label="AI智能分发" value="ai" />
          </el-select>
        </el-form-item>
        <el-form-item label="发布时间">
          <el-date-picker
            v-model="form.publish_time"
            type="datetime"
            placeholder="选择发布时间"
            style="width: 100%;"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
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
import { getPublishPlans, createPublishPlan, updatePublishPlan, deletePublishPlan } from '../api/publishPlans'
import { getMerchants } from '../api/merchants'

const loading = ref(false)
const plans = ref([])
const merchants = ref([])

const filters = ref({
  platform: '',
  status: '',
  search: ''
})

const pagination = ref({
  page: 1,
  size: 20,
  total: 0
})

const dialogVisible = ref(false)
const form = ref({
  id: null,
  plan_name: '',
  platform: 'douyin',
  merchant_id: null,
  distribution_mode: 'manual',
  publish_time: ''
})

const dialogTitle = computed(() => {
  return form.value.id ? '编辑发布计划' : '新建发布计划'
})

const getPlatformText = (platform) => {
  const map = {
    'douyin': '抖音',
    'kuaishou': '快手',
    'xiaohongshu': '小红书'
  }
  return map[platform] || platform
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
    'pending': 'warning',
    'publishing': 'info',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

const loadPlans = async () => {
  try {
    loading.value = true
    const params = {
      platform: filters.value.platform || undefined,
      status: filters.value.status || undefined,
      limit: pagination.value.size,
      offset: (pagination.value.page - 1) * pagination.value.size
    }
    
    const response = await getPublishPlans(params)
    if (response.success) {
      plans.value = response.data.plans
      pagination.value.total = response.data.total
    }
  } catch (error) {
    ElMessage.error('加载发布计划失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadMerchants = async () => {
  try {
    const response = await getMerchants({ limit: 100 })
    if (response.success) {
      merchants.value = response.data.merchants
    }
  } catch (error) {
    console.error('加载商家列表失败:', error)
  }
}

const resetFilters = () => {
  filters.value = {
    platform: '',
    status: '',
    search: ''
  }
  loadPlans()
}

const handleSizeChange = (size) => {
  pagination.value.size = size
  pagination.value.page = 1
  loadPlans()
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadPlans()
}

const handleCreate = () => {
  form.value = {
    id: null,
    plan_name: '',
    platform: 'douyin',
    merchant_id: null,
    distribution_mode: 'manual',
    publish_time: ''
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  form.value = {
    id: row.id,
    plan_name: row.plan_name,
    platform: row.platform,
    merchant_id: row.merchant_id,
    distribution_mode: row.distribution_mode,
    publish_time: row.publish_time ? new Date(row.publish_time).toISOString().slice(0, 19).replace('T', ' ') : ''
  }
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该发布计划吗？', '提示', {
      type: 'warning'
    })
    
    const response = await deletePublishPlan(row.id)
    if (response.success) {
      ElMessage.success('删除成功')
      loadPlans()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

const handleSubmit = async () => {
  if (!form.value.plan_name) {
    ElMessage.warning('请输入计划名称')
    return
  }
  
  try {
    const data = {
      plan_name: form.value.plan_name,
      platform: form.value.platform,
      merchant_id: form.value.merchant_id || undefined,
      distribution_mode: form.value.distribution_mode,
      publish_time: form.value.publish_time || undefined
    }
    
    let response
    if (form.value.id) {
      response = await updatePublishPlan(form.value.id, data)
    } else {
      response = await createPublishPlan(data)
    }
    
    if (response.success) {
      ElMessage.success(form.value.id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      loadPlans()
    }
  } catch (error) {
    ElMessage.error(form.value.id ? '更新失败' : '创建失败')
    console.error(error)
  }
}

onMounted(() => {
  loadPlans()
  loadMerchants()
})
</script>

<style scoped>
.publish-plan-page {
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
