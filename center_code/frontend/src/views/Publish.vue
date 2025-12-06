<template>
  <div class="publish-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>立即发布</h3>
        </div>
      </template>

      <el-form :model="form" label-width="120px" style="max-width: 800px;">
        <el-form-item label="选择账号" required>
          <el-select v-model="form.account_id" placeholder="请选择账号" filterable style="width: 100%;">
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="`${account.account_name} (${getPlatformText(account.platform)})`"
              :value="account.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="视频URL" required>
          <el-input v-model="form.video_url" placeholder="请输入视频URL" />
        </el-form-item>

        <el-form-item label="视频标题">
          <el-input v-model="form.video_title" placeholder="请输入视频标题" />
        </el-form-item>

        <el-form-item label="视频标签">
          <el-input v-model="form.video_tags" placeholder="请输入视频标签，用逗号分隔" />
        </el-form-item>

        <el-form-item label="发布时间">
          <el-date-picker
            v-model="form.publish_date"
            type="datetime"
            placeholder="选择发布时间（留空则立即发布）"
            style="width: 100%;"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">立即发布</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const form = ref({
  account_id: null,
  video_url: '',
  video_title: '',
  video_tags: '',
  publish_date: ''
})

const accounts = ref([])
const submitting = ref(false)

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
    const response = await api.accounts.list({ limit: 1000 })
    if (response.success) {
      accounts.value = response.data.accounts || []
    }
  } catch (error) {
    console.error('加载账号列表失败:', error)
  }
}

const handleSubmit = async () => {
  if (!form.value.account_id || !form.value.video_url) {
    ElMessage.warning('请选择账号并输入视频URL')
    return
  }

  try {
    submitting.value = true
    const data = {
      account_id: form.value.account_id,
      video_url: form.value.video_url,
      video_title: form.value.video_title,
      video_tags: form.value.video_tags,
      publish_date: form.value.publish_date || undefined
    }

    const response = await api.video.upload(data)
    if (response.success) {
      ElMessage.success('发布任务已创建')
      handleReset()
    }
  } catch (error) {
    ElMessage.error('发布失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

const handleReset = () => {
  form.value = {
    account_id: null,
    video_url: '',
    video_title: '',
    video_tags: '',
    publish_date: ''
  }
}

onMounted(() => {
  loadAccounts()
})
</script>

<style scoped>
.publish-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
