<template>
  <div class="accounts-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>授权管理</h3>
          <el-button type="primary" @click="handleAddAccount">
            <el-icon><Plus /></el-icon>
            添加账号
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
        <el-select v-model="filters.login_status" placeholder="登录状态" clearable style="width: 150px; margin-right: 10px;">
          <el-option label="已登录" value="logged_in" />
          <el-option label="未登录" value="logged_out" />
        </el-select>
        <el-input
          v-model="filters.search"
          placeholder="搜索账号名称"
          style="width: 250px; margin-right: 10px;"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="loadAccounts">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <!-- 表格 -->
      <el-table :data="accounts" v-loading="loading" stripe style="width: 100%; margin-top: 20px;">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="account_name" label="账号名称" min-width="200" />
        <el-table-column prop="platform" label="平台" width="100">
          <template #default="{ row }">
            <el-tag>{{ getPlatformText(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="device_id" label="设备ID" width="120" />
        <el-table-column prop="login_status" label="登录状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.login_status === 'logged_in' ? 'success' : 'info'">
              {{ row.login_status === 'logged_in' ? '已登录' : '未登录' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_time" label="最后登录时间" width="180">
          <template #default="{ row }">
            {{ row.last_login_time ? new Date(row.last_login_time).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleLogin(row)">登录</el-button>
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

    <!-- 添加/编辑账号对话框 -->
    <AccountModal v-model="accountModalVisible" :account="currentAccount" @success="loadAccounts" />

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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Check, Close } from '@element-plus/icons-vue'
import api from '../api'
import AccountModal from '../components/AccountModal.vue'

const loading = ref(false)
const accounts = ref([])
const accountModalVisible = ref(false)
const currentAccount = ref(null)

// 登录对话框相关
const loginDialogVisible = ref(false)
const currentLoginAccount = ref(null)
const loginStatus = ref('loading') // loading, waiting, scanning, logged_in, failed
const loginErrorMessage = ref('')
let loginStatusPollTimer = null

const filters = ref({
  platform: '',
  login_status: '',
  search: ''
})

const pagination = ref({
  page: 1,
  size: 20,
  total: 0
})

const getPlatformText = (platform) => {
  const map = {
    'douyin': '抖音',
    'kuaishou': '快手',
    'xiaohongshu': '小红书'
  }
  return map[platform] || platform
}

const loadAccounts = async () => {
  try {
    loading.value = true
    const params = {
      platform: filters.value.platform || undefined,
      login_status: filters.value.login_status || undefined,
      search: filters.value.search || undefined,
      limit: pagination.value.size,
      offset: (pagination.value.page - 1) * pagination.value.size
    }
    
    const response = await api.accounts.list(params)
    if (response.code === 200) {
      accounts.value = response.data?.accounts || []
      pagination.value.total = response.data?.total || 0
    } else {
      ElMessage.error(response.message || '加载账号列表失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '加载账号列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    platform: '',
    login_status: '',
    search: ''
  }
  loadAccounts()
}

const handleSizeChange = (size) => {
  pagination.value.size = size
  pagination.value.page = 1
  loadAccounts()
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadAccounts()
}

const handleAddAccount = () => {
  currentAccount.value = null
  accountModalVisible.value = true
}

const handleEdit = (row) => {
  currentAccount.value = row
  accountModalVisible.value = true
}

const handleLogin = async (row) => {
  try {
    currentLoginAccount.value = row
    loginDialogVisible.value = true
    loginStatus.value = 'loading'
    loginErrorMessage.value = ''
    
    // 启动登录会话（后端会自动打开浏览器）
    const response = await api.login.getQrcode(row.id)
    
    if (response.code === 200) {
      loginStatus.value = 'waiting'
      // 开始轮询登录状态
      startLoginStatusPolling(row.id)
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

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该账号吗？', '提示', {
      type: 'warning'
    })
    
    const response = await api.accounts.delete(row.id)
    if (response.code === 200) {
      ElMessage.success('删除成功')
      loadAccounts()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
      console.error(error)
    }
  }
}

onMounted(() => {
  loadAccounts()
})

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

<style scoped>
.accounts-page {
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
