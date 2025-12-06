<template>
  <el-dialog
    v-model="dialogVisible"
    title="消息管理"
    width="80%"
    :before-close="handleClose"
  >
    <el-tabs v-model="activeTab">
      <el-tab-pane label="监听管理" name="listen">
        <el-form :inline="true" style="margin-bottom: 20px;">
          <el-form-item label="选择账号">
            <el-select v-model="selectedAccountId" placeholder="请选择账号" @change="loadListenTasks">
              <el-option
                v-for="account in accountOptions"
                :key="account.id"
                :label="account.account_name"
                :value="account.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleStartListen" :disabled="!selectedAccountId">开始监听</el-button>
            <el-button type="danger" @click="handleStopListen" :disabled="!selectedAccountId">停止监听</el-button>
          </el-form-item>
        </el-form>

        <el-table
          v-loading="loading"
          :data="listenTasks"
          style="width: 100%"
          stripe
        >
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'running' ? 'success' : 'info'">
                {{ row.status === 'running' ? '运行中' : row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="消息列表" name="messages">
        <el-form :inline="true" style="margin-bottom: 20px;">
          <el-form-item label="选择账号">
            <el-select v-model="messageAccountId" placeholder="请选择账号" @change="loadMessages">
              <el-option
                v-for="account in accountOptions"
                :key="account.id"
                :label="account.account_name"
                :value="account.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button @click="loadMessages">刷新</el-button>
            <el-button type="danger" @click="handleClearMessages" :disabled="!messageAccountId">清空消息</el-button>
          </el-form-item>
        </el-form>

        <el-table
          v-loading="messageLoading"
          :data="messages"
          style="width: 100%"
          stripe
        >
          <el-table-column prop="user_name" label="用户名" width="150" />
          <el-table-column prop="text" label="消息内容" />
          <el-table-column prop="is_me" label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_me ? 'success' : 'info'">
                {{ row.is_me ? '我发送' : '接收' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message_time" label="消息时间" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
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

const activeTab = ref('listen')
const accountOptions = ref([])
const selectedAccountId = ref('')
const messageAccountId = ref('')
const listenTasks = ref([])
const messages = ref([])
const loading = ref(false)
const messageLoading = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) {
    loadAccountOptions()
  }
})

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

const loadListenTasks = async () => {
  if (!selectedAccountId.value) return
  
  loading.value = true
  try {
    const res = await api.listen.tasks({ account_id: selectedAccountId.value })
    if (res.code === 200) {
      listenTasks.value = res.data || []
    }
  } catch (error) {
    console.error('Load listen tasks error:', error)
  } finally {
    loading.value = false
  }
}

const loadMessages = async () => {
  if (!messageAccountId.value) return
  
  messageLoading.value = true
  try {
    const res = await api.social.listen.messages({ account_id: messageAccountId.value, limit: 200 })
    if (res.code === 200) {
      messages.value = res.data || []
    }
  } catch (error) {
    console.error('Load messages error:', error)
  } finally {
    messageLoading.value = false
  }
}

const handleStartListen = async () => {
  try {
    const res = await api.social.listen.start({ account_id: selectedAccountId.value })
    if (res.code === 200) {
      ElMessage.success('监听已启动')
      loadListenTasks()
    } else {
      ElMessage.error(res.message || '启动失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '启动失败')
  }
}

const handleStopListen = async () => {
  try {
    const res = await api.social.listen.stop({ account_id: selectedAccountId.value })
    if (res.code === 200) {
      ElMessage.success('监听已停止')
      loadListenTasks()
    } else {
      ElMessage.error(res.message || '停止失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '停止失败')
  }
}

const handleClearMessages = async () => {
  try {
    await ElMessageBox.confirm('确定要清空该账号的所有消息吗？', '提示', {
      type: 'warning'
    })
    
    const res = await api.messages.clear(messageAccountId.value)
    if (res.code === 200) {
      ElMessage.success('清空成功')
      loadMessages()
    } else {
      ElMessage.error(res.message || '清空失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '清空失败')
    }
  }
}

const handleClose = () => {
    emit('update:modelValue', false)
}
</script>

