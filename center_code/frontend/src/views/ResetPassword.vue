<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="brand">
        <div class="brand-mark">AUTO</div>
        <div class="brand-title">矩阵宝</div>
        <div class="brand-subtitle">重置您的密码</div>
      </div>

      <el-steps :active="currentStep" class="reset-steps">
        <el-step title="验证邮箱" />
        <el-step title="设置新密码" />
      </el-steps>

      <!-- 第一步：输入邮箱获取验证码 -->
      <el-form v-if="currentStep === 0" ref="formRef" :model="form" :rules="step1Rules" label-position="top">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="you@example.com" />
        </el-form-item>
        <el-button type="primary" class="full-button" :loading="loading" @click="sendResetCode">
          发送验证码
        </el-button>
      </el-form>

      <!-- 第二步：输入验证码和新密码 -->
      <el-form v-else-if="currentStep === 1" ref="formRef" :model="form" :rules="step2Rules" label-position="top">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" disabled />
        </el-form-item>
        <el-form-item label="验证码" prop="code">
          <div class="code-row">
            <el-input v-model="form.code" placeholder="6位验证码" />
            <el-button :disabled="countdown > 0" @click="sendResetCode">
              {{ countdown > 0 ? `重新发送 (${countdown}s)` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        <el-button type="primary" class="full-button" :loading="loading" @click="resetPassword">
          重置密码
        </el-button>
      </el-form>

      <div class="auth-footer">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const currentStep = ref(0)

const form = reactive({
  email: '',
  code: '',
  password: ''
})

const step1Rules = {
  email: [
    { required: true, message: '邮箱不能为空', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ]
}

const step2Rules = {
  code: [
    { required: true, message: '验证码不能为空', trigger: 'blur' },
    { min: 6, max: 6, message: '验证码必须是6位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '密码不能为空', trigger: 'blur' },
    { min: 8, message: '密码至少8个字符', trigger: 'blur' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/, message: '密码必须包含大小写字母、数字和特殊字符', trigger: 'blur' }
  ]
}

const countdown = ref(0)
let timer = null

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})

const sendResetCode = async () => {
  if (!form.email) {
    ElMessage.error('请先输入邮箱')
    return
  }

  loading.value = true
  try {
    await api.auth.forgotPassword({ email: form.email })
    ElMessage.success('验证码已发送，请查收邮箱')
    
    // 开始倒计时
    countdown.value = 60
    timer = setInterval(() => {
      if (countdown.value <= 1) {
        clearInterval(timer)
        countdown.value = 0
        return
      }
      countdown.value -= 1
    }, 1000)
    
    // 如果是第二步发送验证码，不需要切换步骤
    if (currentStep.value === 0) {
      currentStep.value = 1
    }
  } catch (error) {
    ElMessage.error(error.message || '发送验证码失败')
  } finally {
    loading.value = false
  }
}

const resetPassword = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const response = await api.auth.resetPassword({
        email: form.email,
        code: form.code,
        password: form.password
      })
      if (response.code === 200) {
        ElMessage.success('密码重置成功，请使用新密码登录')
        router.push('/login')
      } else {
        ElMessage.error(response.message || '密码重置失败')
      }
    } catch (error) {
      ElMessage.error(error.message || '密码重置失败')
    } finally {
      loading.value = false
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
  max-width: 420px;
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

.reset-steps {
  margin-bottom: 24px;
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
  color: #2563eb;
}
</style>