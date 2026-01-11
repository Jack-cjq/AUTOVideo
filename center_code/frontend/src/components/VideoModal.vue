<template>
  <el-dialog
    v-model="dialogVisible"
    title="视频上传"
    width="80%"
    :before-close="handleClose"
  >
    <el-tabs v-model="activeTab">
      <el-tab-pane label="任务列表" name="list">
        <el-table
          v-loading="loading"
          :data="tasks"
          style="width: 100%"
          stripe
        >
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="video_title" label="视频标题" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="progress" label="进度" width="100">
            <template #default="{ row }">
              {{ row.progress }}%
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="创建任务" name="create">
        <el-form :model="form" label-width="120px">
          <el-form-item label="账号">
            <el-select v-model="form.account_id" placeholder="请选择账号">
              <el-option
                v-for="account in accountOptions"
                :key="account.id"
                :label="account.account_name"
                :value="account.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="视频URL">
            <el-input v-model="form.video_url" placeholder="请输入视频URL" />
          </el-form-item>
          <el-form-item label="视频标题">
            <el-input v-model="form.video_title" placeholder="请输入视频标题" />
          </el-form-item>
          <el-form-item label="视频标签">
            <el-input v-model="form.video_tags" placeholder="请输入视频标签，用逗号分隔" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleCreate">创建任务</el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" @click="loadTasks" :loading="loading">刷新</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const activeTab = ref('list')
const tasks = ref([])
const accountOptions = ref([])
const loading = ref(false)

const form = ref({
  account_id: '',
  video_url: '',
  video_title: '',
  video_tags: ''
})

watch(() => props.modelValue, (val) => {
  if (val) {
    loadTasks()
    loadAccountOptions()
  }
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await api.video.tasks()
    if (res.code === 200) {
      tasks.value = res.data || []
    }
  } catch (error) {
    console.error('Load tasks error:', error)
  } finally {
    loading.value = false
  }
}

const loadAccountOptions = async () => {
  try {
    const res = await api.accounts.list()
    if (res.code === 200) {
      accountOptions.value = res.data || []
    }
  } catch (error) {
    console.error('Load accounts error:', error)
  }
}

const handleCreate = async () => {
  if (!form.value.account_id || !form.value.video_url) {
    ElMessage.warning('请填写完整信息')
    return
  }

  try {
    const res = await api.video.upload(form.value)
    if (res.code === 200) {
      ElMessage.success('任务创建成功')
      resetForm()
      loadTasks()
      activeTab.value = 'list'
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '创建失败')
  }
}

const handleDelete = async (task) => {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？', '提示', {
      type: 'warning'
    })
    
    const res = await api.video.deleteTask(task.id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      loadTasks()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const getStatusType = (status) => {
  const map = {
    'pending': 'warning',
    'uploading': 'primary',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'pending': '等待中',
    'uploading': '上传中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status] || status
}

const resetForm = () => {
  form.value = {
    account_id: '',
    video_url: '',
    video_title: '',
    video_tags: ''
  }
}

const handleClose = () => {
    emit('update:modelValue', false)
}
</script>

