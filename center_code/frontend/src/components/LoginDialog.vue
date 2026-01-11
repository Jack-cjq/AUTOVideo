<template>
  <el-dialog
    v-model="dialogVisible"
    title="登录"
    width="400px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    :modal="true"
    :append-to-body="true"
    z-index="3000"
  >
    <el-form @submit.prevent="handleLogin">
      <el-form-item label="用户名">
        <el-input v-model="username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input
          v-model="password"
          type="password"
          placeholder="请输入密码"
          @keyup.enter="handleLogin"
        />
      </el-form-item>
    </el-form>
    <div v-if="errorMessage" style="color: red; margin-bottom: 15px;">
      {{ errorMessage }}
    </div>
    <template #footer>
      <el-button @click="handleLogin" type="primary" :loading="loading">登录</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const authStore = useAuthStore()
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const loading = ref(false)

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

watch(() => props.modelValue, (val) => {
  if (val) {
    username.value = ''
    password.value = ''
    errorMessage.value = ''
  }
})

const handleLogin = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  errorMessage.value = ''

  const result = await authStore.login(username.value, password.value)
  
  loading.value = false

  if (!result.success) {
    errorMessage.value = result.message || '登录失败'
    }
}
</script>

