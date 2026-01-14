<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="brand">
        <div class="brand-mark">AUTO</div>
        <div class="brand-title">注册账号</div>
        <div class="brand-subtitle">使用邮箱注册</div>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="you@example.com" />
        </el-form-item>

        <el-form-item label="验证码" prop="code">
          <div class="code-row">
            <el-input v-model="form.code" placeholder="6位验证码" />
            <el-button :disabled="countdown > 0" @click="sendCode">
              {{ countdown > 0 ? `重新发送 (${countdown}s)` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="设置密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>

        <el-button type="primary" class="full-button" :loading="loading" @click="handleRegister">
          注册
        </el-button>
      </el-form>

      <div class="auth-footer">
        <span>已有账号？</span>
        <router-link to="/login">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const countdown = ref(0)
let timer = null

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})

const form = reactive({
  username: '',
  email: '',
  code: '',
  password: '',
  confirmPassword: ''
})

const rules = {
  username: [
    { required: true, message: '用户名不能为空', trigger: 'blur' },
    { min: 2, max: 16, message: '用户名长度必须在2-16个字符之间', trigger: 'blur' },
    { 
      validator: async (rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        try {
          const res = await api.auth.checkUsernameExists(value)
          if (res.data.exists) {
            callback(new Error('该用户名已被占用，请更换'))
          } else {
            callback()
          }
        } catch (error) {
          console.error('检查用户名失败:', error)
          callback() // 网络错误时不阻塞表单
        }
      },
      trigger: 'blur'
    }
  ],
  email: [
    { required: true, message: '邮箱不能为空', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
    { 
      validator: async (rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        try {
          const res = await api.auth.checkEmailExists(value)
          if (res.data.exists) {
            callback(new Error('该邮箱已注册，请直接登录'))
          } else {
            callback()
          }
        } catch (error) {
          console.error('检查邮箱失败:', error)
          callback() // 网络错误时不阻塞表单
        }
      },
      trigger: 'blur'
    }
  ],
  code: [
    { required: true, message: '验证码不能为空', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '密码不能为空', trigger: 'blur' },
    { min: 8, message: '密码至少8个字符', trigger: 'blur' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/, message: '密码必须包含大小写字母、数字和特殊字符', trigger: 'blur' }
  ],
  confirmPassword: [
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请确认密码'))
          return
        }
        if (value !== form.password) {
          callback(new Error('两次密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

const sendCode = async () => {
  // 验证邮箱是否为空
  if (!form.email) {
    ElMessage.error('请先输入邮箱')
    return
  }
  
  // 验证邮箱格式
  const emailRegex = /^[^@]+@[^@]+[^@]+$/
  if (!emailRegex.test(form.email)) {
    ElMessage.error('请输入有效的邮箱地址')
    return
  }
  
  // 验证邮箱是否已被注册
  try {
    const res = await api.auth.checkEmailExists(form.email)
    if (res.data.exists) {
      ElMessage.error('该邮箱已注册，请直接登录')
      return
    }
    
    // 邮箱验证通过，发送验证码
    await api.auth.sendCode(form.email)
    ElMessage.success('验证码已发送')
    countdown.value = 60
    timer = setInterval(() => {
      if (countdown.value <= 1) {
        clearInterval(timer)
        countdown.value = 0
        return
      }
      countdown.value -= 1
    }, 1000)
  } catch (error) {
    console.error('发送验证码失败:', error)
    ElMessage.error(error.message || '发送验证码失败')
  }
}

const handleRegister = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    const result = await authStore.register({
      username: form.username,
      email: form.email,
      password: form.password,
      code: form.code
    })
    loading.value = false
    if (result.success) {
      ElMessage.success('注册成功，请登录')
      router.push('/login')
    } else {
      ElMessage.error(result.message || '注册失败')
    }
  })
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top, #eef4ff 0%, #f8fafc 40%, #ffffff 100%);
  padding: 24px;
}

.auth-card {
  width: 100%;
  max-width: 460px;
  background: #ffffff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.12);
}

.brand {
  text-align: center;
  margin-bottom: 24px;
}

.brand-mark {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 12px;
}

.brand-title {
  margin-top: 12px;
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.brand-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}

.full-button {
  width: 100%;
  margin-top: 8px;
}

.code-row {
  display: flex;
  gap: 8px;
}

.code-row .el-button {
  width: 140px;
}

.auth-footer {
  margin-top: 16px;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

.auth-footer a {
  margin-left: 6px;
  color: #2563eb;
}
</style>
