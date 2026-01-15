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

  <!-- 登录对话框 -->
  <el-dialog
    v-model="loginDialogVisible"
    :title="`${getPlatformText(currentLoginAccount?.platform || 'douyin')}账号登录`"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="true"
  >
    <div v-if="loginStatus === 'loading'" style="text-align: center; padding: 40px;">
      <el-icon class="is-loading" style="font-size: 48px; color: #409eff;"><Loading /></el-icon>
      <p style="margin-top: 20px; color: #666;">正在启动浏览器...</p>
    </div>
    
    <div v-else-if="loginStatus === 'waiting' || loginStatus === 'scanning'" style="text-align: center; padding: 40px;">
      <el-icon style="font-size: 48px; color: #409eff;"><Loading /></el-icon>
      <p style="margin-top: 20px; color: #666; font-size: 16px;">
        <span v-if="loginStatus === 'waiting'">等待用户扫码登录...</span>
        <span v-else-if="loginStatus === 'scanning'">已扫描，等待用户确认登录...</span>
      </p>
      <p style="margin-top: 10px; color: #999; font-size: 14px;">
        请使用抖音APP扫描浏览器中的二维码完成登录
      </p>
    </div>
    
    <div v-else-if="loginStatus === 'logged_in'" style="text-align: center; padding: 40px;">
      <el-icon style="font-size: 48px; color: #67c23a;"><Check /></el-icon>
      <p style="margin-top: 20px; color: #67c23a; font-size: 16px;">登录成功！正在保存cookies...</p>
    </div>
    
    <div v-else-if="loginStatus === 'failed'" style="text-align: center; padding: 40px;">
      <el-icon style="font-size: 48px; color: #f56c6c;"><Close /></el-icon>
      <p style="margin-top: 20px; color: #f56c6c; font-size: 16px;">登录失败</p>
      <p style="margin-top: 10px; color: #666; font-size: 14px;">{{ loginErrorMessage }}</p>
      <el-button type="primary" @click="retryLogin" style="margin-top: 20px;">重试</el-button>
    </div>

    <template #footer>
      <el-button @click="cancelLogin" :disabled="loginStatus === 'logged_in'">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Check, Close } from '@element-plus/icons-vue'
import api from '../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'success'])

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const activeTab = ref('list')
const accounts = ref([])
const deviceOptions = ref([])
const loading = ref(false)

// 登录对话框相关
const loginDialogVisible = ref(false)
const currentLoginAccount = ref(null)
const loginStatus = ref('loading') // loading, waiting, scanning, logged_in, failed
const loginErrorMessage = ref('')
let loginStatusPollTimer = null

// 确保accounts始终是数组
const safeAccounts = computed(() => {
  return Array.isArray(accounts.value) ? accounts.value : []
})

const getPlatformText = (platform) => {
  const map = {
    'douyin': '抖音',
    'kuaishou': '快手',
    'xiaohongshu': '小红书'
  }
  return map[platform] || platform
}

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
      loadAccounts() // 刷新对话框内的账号列表
      activeTab.value = 'list' // 切换到账号列表标签页
      emit('success') // 通知父组件刷新账号列表
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '创建失败')
  }
}

const handleLogin = async (account) => {
  try {
    currentLoginAccount.value = account
    loginDialogVisible.value = true
    loginStatus.value = 'loading'
    loginErrorMessage.value = ''
    
    // 启动登录会话（后端会自动打开浏览器）
    const response = await api.login.getQrcode(account.id)
    
    if (response.code === 200) {
      loginStatus.value = 'waiting'
      // 开始轮询登录状态
      startLoginStatusPolling(account.id)
      ElMessage.success('浏览器已打开，请扫码登录')
    } else {
      loginStatus.value = 'failed'
      loginErrorMessage.value = response.message || '启动登录失败'
      ElMessage.error(loginErrorMessage.value)
    }
  } catch (error) {
    console.error('登录失败:', error)
    loginStatus.value = 'failed'
    loginErrorMessage.value = error.message || '启动登录失败'
    ElMessage.error(loginErrorMessage.value)
  }
}

// 开始轮询登录状态
const startLoginStatusPolling = (accountId) => {
  // 清除之前的定时器
  if (loginStatusPollTimer) {
    clearInterval(loginStatusPollTimer)
  }
  
  // 立即检查一次
  checkLoginStatus(accountId)
  
  // 每3秒检查一次
  loginStatusPollTimer = setInterval(() => {
    checkLoginStatus(accountId)
  }, 3000)
}

// 检查登录状态
const checkLoginStatus = async (accountId) => {
  try {
    const response = await api.login.getStatus(accountId)
    
    if (response.code === 200 && response.data) {
      const data = response.data
      loginStatus.value = data.status
      
      if (data.status === 'logged_in') {
        // 登录成功，停止轮询
        if (loginStatusPollTimer) {
          clearInterval(loginStatusPollTimer)
          loginStatusPollTimer = null
        }
        
        // 自动完成登录并保存cookies
        await completeLogin(accountId)
      } else if (data.status === 'failed') {
        // 登录失败，停止轮询
        if (loginStatusPollTimer) {
          clearInterval(loginStatusPollTimer)
          loginStatusPollTimer = null
        }
        loginErrorMessage.value = data.message || '登录失败'
      }
    }
  } catch (error) {
    console.error('检查登录状态失败:', error)
  }
}

// 完成登录并保存cookies
const completeLogin = async (accountId) => {
  try {
    const response = await api.login.complete({ account_id: accountId })
    
    if (response.code === 200) {
      ElMessage.success('登录完成，cookies已保存！')
      
      // 延迟关闭对话框，让用户看到成功提示
      setTimeout(() => {
        loginDialogVisible.value = false
        // 刷新账号列表
        loadAccounts()
        emit('success') // 通知父组件刷新账号列表
      }, 1500)
    } else {
      loginStatus.value = 'failed'
      loginErrorMessage.value = response.message || '保存cookies失败'
      ElMessage.error(loginErrorMessage.value)
    }
  } catch (error) {
    loginStatus.value = 'failed'
    loginErrorMessage.value = error.message || '保存cookies失败'
    ElMessage.error(loginErrorMessage.value)
    console.error('完成登录失败:', error)
  }
}

// 取消登录
const cancelLogin = async () => {
  if (loginStatusPollTimer) {
    clearInterval(loginStatusPollTimer)
    loginStatusPollTimer = null
  }
  
  if (currentLoginAccount.value) {
    try {
      await api.login.cancel({ account_id: currentLoginAccount.value.id })
    } catch (error) {
      console.warn('取消登录会话失败:', error)
    }
  }
  
  loginDialogVisible.value = false
  currentLoginAccount.value = null
  loginStatus.value = 'loading'
  loginErrorMessage.value = ''
}

// 重试登录
const retryLogin = () => {
  if (currentLoginAccount.value) {
    handleLogin(currentLoginAccount.value)
  }
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

onUnmounted(() => {
  // 清理定时器
  if (loginStatusPollTimer) {
    clearInterval(loginStatusPollTimer)
    loginStatusPollTimer = null
  }
  
  // 取消登录会话
  if (currentLoginAccount.value) {
    api.login.cancel({ account_id: currentLoginAccount.value.id }).catch(err => {
      console.warn('取消登录会话失败:', err)
    })
  }
})
</script>

