<template>
  <el-dialog
    v-model="dialogVisible"
    title="账号管理"
    width="80%"
    :before-close="handleClose"
  >
    <el-tabs v-model="activeTab">
      <el-tab-pane label="账号列表" name="list">
        <el-table
          v-loading="loading"
          :data="safeAccounts"
          style="width: 100%"
          stripe
        >
          <el-table-column prop="account_name" label="账号名称" />
          <el-table-column prop="platform" label="平台" />
          <el-table-column prop="login_status" label="登录状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.login_status === 'logged_in' ? 'success' : 'info'">
                {{ row.login_status === 'logged_in' ? '已登录' : '未登录' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button size="small" @click="handleLogin(row)">登录</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="添加账号" name="add">
        <el-form :model="form" label-width="120px">
          <el-form-item label="设备ID">
            <el-select v-model="form.device_id" placeholder="请选择设备">
              <el-option
                v-for="device in deviceOptions"
                :key="device.device_id"
                :label="`${device.device_name} (${device.device_id})`"
                :value="device.device_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="账号名称">
            <el-input v-model="form.account_name" placeholder="请输入账号名称" />
          </el-form-item>
          <el-form-item label="平台">
            <el-select v-model="form.platform" placeholder="请选择平台">
              <el-option label="抖音" value="douyin" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleCreate">创建</el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" @click="loadAccounts" :loading="loading">刷新</el-button>
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
const accounts = ref([])
const deviceOptions = ref([])
const loading = ref(false)

const form = ref({
  device_id: '',
  account_name: '',
  platform: 'douyin'
})

watch(() => props.modelValue, (val) => {
  if (val) {
    loadAccounts()
    loadDeviceOptions()
  }
})

const loadAccounts = async () => {
  loading.value = true
  try {
    const res = await api.accounts.list()
    if (res && res.code === 200) {
      // 处理不同的数据格式
      let accountsData = []
      if (Array.isArray(res.data)) {
        accountsData = res.data
      } else if (res.data && Array.isArray(res.data.accounts)) {
        accountsData = res.data.accounts
      } else if (res.data && typeof res.data === 'object') {
        // 如果是对象，尝试转换为数组
        accountsData = Object.values(res.data)
      }
      
      // 确保 accounts 始终是数组
      accounts.value = Array.isArray(accountsData) ? accountsData : []
    } else {
      accounts.value = []
    }
  } catch (error) {
    console.error('Load accounts error:', error)
    // 确保 accounts 始终是数组
    accounts.value = []
    // 如果是401错误，不显示错误（已经由拦截器处理）
    if (error.code !== 401) {
      ElMessage.error(error.message || '加载账号列表失败')
    }
  } finally {
    loading.value = false
  }
}

const loadDeviceOptions = async () => {
  try {
    const res = await api.devices.list()
    if (res.code === 200) {
      deviceOptions.value = res.data || []
    }
  } catch (error) {
    console.error('Load devices error:', error)
  }
}

const handleCreate = async () => {
  if (!form.value.device_id || !form.value.account_name) {
    ElMessage.warning('请填写完整信息')
    return
  }

  try {
    const res = await api.accounts.create(form.value)
    if (res.code === 200 || res.code === 201) {
      ElMessage.success('创建成功')
      resetForm()
      loadAccounts()
      activeTab.value = 'list'
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '创建失败')
  }
}

const handleLogin = async (account) => {
  // TODO: 实现登录逻辑
  ElMessage.info('登录功能待实现')
}

const handleDelete = async (account) => {
  try {
    await ElMessageBox.confirm('确定要删除该账号吗？', '提示', {
      type: 'warning'
    })
    
    const res = await api.accounts.delete(account.id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      loadAccounts()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const resetForm = () => {
  form.value = {
    device_id: '',
    account_name: '',
    platform: 'douyin'
  }
}

const handleClose = () => {
    emit('update:modelValue', false)
}
</script>

