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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import AccountModal from '../components/AccountModal.vue'

const loading = ref(false)
const accounts = ref([])
const accountModalVisible = ref(false)
const currentAccount = ref(null)

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
    // 调用登录接口，获取登录助手页面URL
    const response = await api.login.start({ account_id: row.id })
    
    if (response.code === 200 && response.data) {
      // 打开登录助手页面
      const loginUrl = response.data.login_url || `/login-helper?account_id=${row.id}`
      window.open(loginUrl, '_blank', 'width=1000,height=800')
      ElMessage.success('已打开登录助手页面，请在新窗口中完成登录')
    } else {
      ElMessage.error(response.message || '打开登录助手页面失败')
    }
  } catch (error) {
    console.error('登录失败:', error)
    ElMessage.error(error.message || '打开登录助手页面失败')
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
