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
        <el-form-item label="选择账号" required>
          <el-select
            v-model="form.account_ids"
            multiple
            filterable
            placeholder="请选择要使用的账号（可多选）"
            style="width: 100%;"
          >
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="account.account_name"
              :value="account.id"
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
        <el-divider>视频与发布方式</el-divider>
        <el-form-item label="发布方式" required>
          <el-radio-group v-model="form.publish_mode">
            <el-radio label="phased">分阶段（按固定时间逐个发出）</el-radio>
            <el-radio label="batch">分批次（一次选择多个视频）</el-radio>
          </el-radio-group>
        </el-form-item>
        <div v-if="form.publish_mode === 'phased'">
          <el-form-item label="阶段列表" required>
            <div style="width: 100%;">
              <el-button type="primary" link @click="addPhaseItem" style="margin-bottom: 8px;">添加阶段</el-button>
              <el-table :data="phasedItems" size="small" style="width: 100%;" v-loading="videoLoading">
                <el-table-column label="视频" min-width="220">
                  <template #default="{ row, $index }">
                    <el-select v-model="row.video_id" placeholder="选择视频" filterable style="width: 100%;" @visible-change="onVideoDropdownOpened">
                      <el-option
                        v-for="video in videoLibrary"
                        :key="video.id"
                        :label="video.video_name || video.video_url"
                        :value="video.id"
                      />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="发布时间" width="240">
                  <template #default="{ row }">
                    <el-date-picker
                      v-model="row.schedule_time"
                      type="datetime"
                      placeholder="选择时间"
                      value-format="YYYY-MM-DD HH:mm:ss"
                      style="width: 100%;"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="{ $index }">
                    <el-button link type="danger" size="small" @click="removePhaseItem($index)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-if="phasedItems.length === 0" style="margin-top: 8px;">
                <el-text type="info" size="small">请添加至少一个阶段并选择视频与时间</el-text>
              </div>
            </div>
          </el-form-item>
        </div>
        <div v-else>
          <el-form-item label="选择视频" required>
            <el-select
              v-model="batchVideoIds"
              multiple
              filterable
              placeholder="从视频库选择多个视频"
              style="width: 100%;"
              @visible-change="onVideoDropdownOpened"
            >
              <el-option
                v-for="video in videoLibrary"
                :key="video.id"
                :label="video.video_name || video.video_url"
                :value="video.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="批次统一时间">
            <el-date-picker
              v-model="batchTime"
              type="datetime"
              placeholder="不选则使用上方发布时间或立即"
              style="width: 100%;"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPublishPlans, createPublishPlan, updatePublishPlan, deletePublishPlan, addVideoToPlan, savePublishInfo } from '../api/publishPlans'
import { getMerchants } from '../api/merchants'
import { getVideos } from '../api/videoLibrary'
import api from '../api/index'

const loading = ref(false)
const plans = ref([])
const merchants = ref([])
const accounts = ref([])

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
  publish_time: '',
  publish_mode: 'batch',
  account_ids: []
})
const videoLibrary = ref([])
const videoLoading = ref(false)
const phasedItems = ref([])
const batchVideoIds = ref([])
const batchTime = ref('')

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
            if (response.code === 200) {
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
            if (response.code === 200) {
              merchants.value = response.data.merchants
            }
  } catch (error) {
    console.error('加载商家列表失败:', error)
  }
}

const loadAccounts = async (platform = 'douyin') => {
  try {
    const response = await api.accounts.list({ platform, limit: 100 })
    if (response.code === 200) {
      accounts.value = response.data.accounts
    }
  } catch (error) {
    console.error('加载账号列表失败:', error)
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
    publish_time: '',
    publish_mode: 'batch',
    account_ids: []
  }
  phasedItems.value = []
  batchVideoIds.value = []
  batchTime.value = ''
  loadAccounts('douyin')
  dialogVisible.value = true
}

const handleEdit = (row) => {
  form.value = {
    id: row.id,
    plan_name: row.plan_name,
    platform: row.platform,
    merchant_id: row.merchant_id,
    distribution_mode: row.distribution_mode,
    publish_time: row.publish_time ? new Date(row.publish_time).toISOString().slice(0, 19).replace('T', ' ') : '',
    publish_mode: 'batch',
    account_ids: []
  }
  phasedItems.value = []
  batchVideoIds.value = []
  batchTime.value = ''
  loadAccounts(row.platform)
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该发布计划吗？', '提示', {
      type: 'warning'
    })
    
    const response = await deletePublishPlan(row.id)
            if (response.code === 200) {
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
  if (!form.value.account_ids || form.value.account_ids.length === 0) {
    ElMessage.warning('请至少选择一个账号')
    return
  }
  if (form.value.publish_mode === 'phased') {
    const invalid = phasedItems.value.some(it => !it.video_id || !it.schedule_time)
    if (invalid) {
      ElMessage.warning('分阶段需为每行选择视频并设置时间')
      return
    }
  } else {
    if (!batchVideoIds.value || batchVideoIds.value.length === 0) {
      ElMessage.warning('请至少选择一个视频')
      return
    }
  }
  
  try {
    const data = {
      plan_name: form.value.plan_name,
      platform: form.value.platform,
      merchant_id: form.value.merchant_id || undefined,
      distribution_mode: form.value.distribution_mode,
      publish_time: form.value.publish_time || undefined,
      account_ids: form.value.account_ids
    }
    
    let response
    if (form.value.id) {
      response = await updatePublishPlan(form.value.id, data)
    } else {
      response = await createPublishPlan(data)
    }
    
    if (response.code === 200 || response.code === 201) {
      const planId = form.value.id ? form.value.id : response.data?.id
      if (!planId) {
        ElMessage.warning('计划创建成功但未获取到ID')
      } else {
        if (form.value.publish_mode === 'phased') {
          for (const it of phasedItems.value) {
            const video = videoLibrary.value.find(v => v.id === it.video_id)
            if (video) {
              await addVideoToPlan(planId, {
                video_url: video.video_url,
                video_title: video.video_name || '',
                thumbnail_url: video.thumbnail_url || ''
              })
            }
          }
          await savePublishInfo(planId, {
            publish_schedule: {
              mode: 'phased',
              items: phasedItems.value.map(it => {
                const v = videoLibrary.value.find(x => x.id === it.video_id)
                return {
                  video_id: it.video_id,
                  video_url: v?.video_url,
                  schedule_time: it.schedule_time
                }
              })
            }
          })
        } else {
          for (const vid of batchVideoIds.value) {
            const video = videoLibrary.value.find(v => v.id === vid)
            if (video) {
              await addVideoToPlan(planId, {
                video_url: video.video_url,
                video_title: video.video_name || '',
                thumbnail_url: video.thumbnail_url || ''
              })
            }
          }
          await savePublishInfo(planId, {
            publish_schedule: {
              mode: 'batch',
              items: batchVideoIds.value.map(vid => {
                const v = videoLibrary.value.find(x => x.id === vid)
                return {
                  video_id: vid,
                  video_url: v?.video_url
                }
              }),
              batch_time: batchTime.value || form.value.publish_time || ''
            }
          })
        }
      }
      ElMessage.success(form.value.id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      loadPlans()
    } else {
      ElMessage.error(response.message || (form.value.id ? '更新失败' : '创建失败'))
    }
  } catch (error) {
    ElMessage.error(form.value.id ? '更新失败' : '创建失败')
    console.error(error)
  }
}

// 监听平台变化，更新账号列表
watch(() => form.value.platform, (newPlatform) => {
  loadAccounts(newPlatform)
  // 清空已选择的账号，因为平台变了
  form.value.account_ids = []
})

onMounted(() => {
  loadPlans()
  loadMerchants()
  loadVideoLibrary()
})

const loadVideoLibrary = async () => {
  try {
    videoLoading.value = true
    const res = await getVideos({ limit: 200 })
    if (res.code === 200) {
      videoLibrary.value = res.data?.videos || []
    }
  } catch (e) {
    console.error('加载视频库失败', e)
  } finally {
    videoLoading.value = false
  }
}

const onVideoDropdownOpened = (opened) => {
  if (opened && videoLibrary.value.length === 0 && !videoLoading.value) {
    loadVideoLibrary()
  }
}

const addPhaseItem = () => {
  phasedItems.value.push({ video_id: null, schedule_time: '' })
}

const removePhaseItem = (idx) => {
  phasedItems.value.splice(idx, 1)
}
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
