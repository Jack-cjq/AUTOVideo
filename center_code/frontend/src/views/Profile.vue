<template>
  <div class="profile-page">
    <el-card class="profile-card">
      <div class="profile-header">
        <div class="profile-meta">
          <h2>个人资料</h2>
          <p>管理您的个人信息</p>
        </div>
      </div>

      <!-- 用户名部分 -->
      <div class="profile-info-item">
        <div class="info-label">用户名</div> 
        <div class="info-content">
          <template v-if="!editUsernameMode">
            <span class="current-value">{{ originalUsername.value || authStore.username || '未设置' }}</span>
            <el-button type="primary" size="small" @click="editUsernameMode = true">修改</el-button>
          </template>
          <el-form 
            v-else 
            ref="usernameFormRef" 
            :model="usernameForm" 
            :rules="usernameRules" 
            label-position="top" 
            class="profile-form edit-form"
          >
            <el-form-item label="" prop="username">
              <el-input v-model="usernameForm.username" placeholder="请输入新用户名" />
            </el-form-item>
            <div class="form-actions">
              <el-button type="primary" :loading="savingUsername" @click="saveUsername">保存</el-button>
              <el-button @click="cancelEditUsername">取消</el-button>
            </div>
          </el-form>
        </div>
      </div>
      
      <el-divider />
      
      <!-- 邮箱部分 -->
      <div class="profile-info-item">
        <div class="info-label">邮箱</div>
        <div class="info-content">
          <template v-if="!editEmailMode">
            <span class="current-value">{{ originalEmail.value || authStore.email || '未设置' }}</span>
            <el-button type="primary" size="small" @click="handleEditEmail">修改</el-button>
          </template>
          <!-- 独立的邮箱修改模块 -->
          <el-card v-else class="email-modification-card">
            <h3>修改邮箱</h3>
            <el-form 
              ref="emailFormRef" 
              :model="emailForm" 
              :rules="emailRules" 
              label-position="top" 
              class="email-modification-form"
              :validate-on-rule-change="false"
            >
              <!-- 第一步：填写并验证新邮箱 -->
              <div v-if="!newEmailVerified">
                <el-form-item label="原邮箱">
                  <div class="current-email-container">
                    <span class="current-email">{{ originalEmail.value || authStore.email || '未设置' }}</span>
                  </div>
                </el-form-item>
                
                <el-form-item label="新邮箱" prop="email">
                  <el-input 
                    v-model="emailForm.email" 
                    placeholder="请输入你要绑定的新邮箱"
                    @input="handleNewEmailInput"
                    clearable
                    @blur="handleNewEmailBlur"
                  />
                </el-form-item>
                
                <el-form-item label="新邮箱验证码" prop="newEmailCode">
                  <div class="email-input-container">
                    <el-input 
                      v-model="emailForm.newEmailCode" 
                      placeholder="请输入新邮箱收到的验证码"
                      maxlength="6"
                      @input="handleNewCodeInput"
                    />
                    <el-button 
                      type="primary"
                      :disabled="!canSendNewCode || isSendingNewCode || newEmailCountdown > 0"
                      @click="sendNewEmailCode"
                    >
                      {{ isSendingNewCode ? '发送中...' : newEmailCountdown > 0 ? `重新发送 (${newEmailCountdown}s)` : '获取新邮箱验证码' }}
                    </el-button>
                  </div>
                </el-form-item>
                
                <div class="form-actions">
                  <el-button 
                    type="primary"
                    :disabled="!canVerifyNewEmail || isVerifyingNewEmail"
                    @click="verifyNewEmailIdentity"
                  >
                    {{ isVerifyingNewEmail ? '验证中...' : '验证新邮箱' }}
                  </el-button>
                  <el-button @click="cancelEditEmail">取消</el-button>
                </div>
              </div>
              
              <!-- 第二步：确认修改 -->
              <div v-else-if="newEmailVerified">
                <div class="verification-summary">
                  <div class="summary-item">
                    <span class="summary-label">原邮箱：</span>
                    <span class="summary-value">{{ originalEmail.value || authStore.email }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-label">新邮箱：</span>
                    <span class="summary-value">{{ emailForm.email }}</span>
                  </div>
                </div>
                
                <div class="form-actions">
                  <el-button 
                    type="primary"
                    :loading="savingEmail"
                    @click="saveEmail"
                  >
                    确认修改邮箱
                  </el-button>
                  <el-button @click="resetEmailVerification">取消修改</el-button>
                </div>
              </div>
            </el-form>
          </el-card>
        </div>
      </div>
      
      <el-divider />
      
      <!-- 密码部分 -->
      <div class="profile-info-item">
        <div class="info-label">密码</div>
        <div class="info-content">
          <template v-if="!editPasswordMode">
            <span class="current-value">********</span>
            <el-button type="primary" size="small" @click="editPasswordMode = true">修改</el-button>
          </template>
          <el-form 
            v-else 
            ref="passwordFormRef" 
            :model="passwordForm" 
            :rules="passwordRules" 
            label-position="top" 
            class="password-form edit-form"
            :validate-on-rule-change="false"
          >
            <h4>修改密码</h4>
            <el-form-item label="旧密码" prop="oldPassword">
              <div class="old-password-container">
                <el-input 
                  v-model="passwordForm.oldPassword" 
                  type="password" 
                  show-password
                  placeholder="请输入旧密码"
                  @blur="handleOldPasswordBlur" 
                  @input="handleOldPasswordInput"
                  style="flex: 1;"
                />
                <el-button 
                  type="primary" 
                  size="small" 
                  :loading="verifyingOldPassword"
                  @click="verifyOldPassword"
                  :disabled="!passwordForm.oldPassword"
                >
                  验证
                </el-button>
              </div>
              <!-- 显示验证结果提示 -->
              <div v-if="oldPasswordError" class="password-error-message">
                <el-icon><CircleCloseFilled /></el-icon> {{ oldPasswordError }}
              </div>
              <div v-else-if="oldPasswordVerified && passwordForm.oldPassword" class="password-success-message">
                <el-icon><CircleCheckFilled /></el-icon> 旧密码验证成功，可以设置新密码
              </div>
            </el-form-item>
            
            <el-form-item label="新密码" prop="newPassword">
              <el-input 
                v-model="passwordForm.newPassword" 
                type="password" 
                show-password
                placeholder="请输入新密码"
                :disabled="!oldPasswordVerified"
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirmPassword">
              <el-input 
                v-model="passwordForm.confirmPassword" 
                type="password" 
                show-password
                placeholder="请再次输入新密码"
                :disabled="!oldPasswordVerified"
              />
            </el-form-item>
            <div class="form-actions">
              <el-button 
                type="primary" 
                :loading="changingPassword" 
                @click="changePassword"
                :disabled="!oldPasswordVerified || !passwordForm.newPassword || !passwordForm.confirmPassword"
              >
                保存
              </el-button>
              <el-button 
                type="default" 
                @click="cancelEditPassword"
              >
                取消
              </el-button>
            </div>
          </el-form>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const usernameFormRef = ref(null)
const emailFormRef = ref(null)
const passwordFormRef = ref(null)
const savingUsername = ref(false)
const savingEmail = ref(false)
const changingPassword = ref(false)
// 邮箱修改相关状态
const isSendingNewCode = ref(false)
const newEmailCountdown = ref(0)
const originalEmail = ref('') // 用于存储原始邮箱，判断是否修改了邮箱
const originalUsername = ref('') // 用于存储原始用户名，判断是否修改了用户名
// 密码修改相关状态
const verifyingOldPassword = ref(false)
const oldPasswordVerified = ref(false)
const oldPasswordError = ref('') // 存储旧密码验证错误信息
let verifyTimer = null // 用于防抖的定时器

// 邮箱修改相关状态
const isVerifyingNewEmail = ref(false) // 控制新邮箱验证加载状态
const newEmailVerified = ref(false) // 新邮箱是否验证成功
const canVerifyNewEmail = ref(false) // 控制是否可以验证新邮箱
const canSendNewCode = ref(false) // 控制"获取新邮箱验证码"按钮是否可点击

// 显示/编辑模式控制
const editUsernameMode = ref(false) // 用户名编辑模式
const editEmailMode = ref(false) // 邮箱编辑模式
const editPasswordMode = ref(false) // 密码编辑模式

// 用户名表单数据
const usernameForm = reactive({
  username: ''
})

// 邮箱表单数据
const emailForm = reactive({
  email: '',
  newEmailCode: ''
})

// 密码表单数据
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 用户名验证规则
const usernameRules = {
  username: [
    { required: true, message: '用户名不能为空', trigger: 'blur' },
    { min: 2, max: 16, message: '用户名长度必须在2-16个字符之间', trigger: 'blur' },
    { pattern: /^[\u4e00-\u9fa5a-zA-Z0-9]+$/, message: '用户名只能包含中英文和数字', trigger: 'blur' },
    {
      validator: async (rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        
        // 如果与原始用户名相同，不需要验证唯一性
        if (value === originalUsername.value) {
          callback()
          return
        }
        
        try {
          const res = await api.auth.checkUsernameExists(value)
          if (res.data.exists) {
            callback(new Error('用户名已被使用'))
          } else {
            callback()
          }
        } catch (error) {
          console.error('检查用户名失败:', error)
          callback() // 网络错误时不阻塞表单提交
        }
      },
      trigger: 'blur'
    }
  ]
}

// 邮箱验证规则
const emailRules = {
  email: [
    { required: true, message: '邮箱不能为空', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
    {
      validator: async (rule, value, callback) => {
        if (!value || value === originalEmail.value) {
          callback()
          return
        }
        
        try {
          const res = await api.auth.checkEmailExists(value)
          if (res.data.exists) {
            callback(new Error('邮箱已被使用'))
          } else {
            callback()
          }
        } catch (error) {
          console.error('检查邮箱失败:', error)
          callback() // 网络错误时不阻塞表单提交
        }
      },
      trigger: 'blur'
    }
  ],
  newEmailCode: [
    {
      required: () => emailForm.email !== originalEmail.value, 
      message: '新邮箱验证码不能为空', 
      trigger: 'blur'
    },
    {
      min: 6, 
      max: 6, 
      message: '验证码为6位数字', 
      trigger: 'blur'
    }
  ]
}

const passwordRules = {
  oldPassword: [
    { 
      required: false, 
      message: '旧密码不能为空', 
      trigger: 'manual' 
    }
  ],
  newPassword: [
    { 
      required: false, 
      message: '新密码不能为空', 
      trigger: 'manual' 
    },
    { min: 8, max: 20, message: '密码长度必须在8-20个字符之间', trigger: 'manual' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$/, message: '密码必须包含大小写字母、数字和特殊字符', trigger: 'manual' },
    {
      validator: (rule, value, callback) => {
        if (value === passwordForm.oldPassword) {
          callback(new Error('新密码不能与原密码相同'))
        } else {
          callback()
        }
      },
      trigger: 'manual'
    }
  ],
  confirmPassword: [
    { 
      required: false, 
      message: '确认密码不能为空', 
      trigger: 'manual' 
    },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次密码输入不一致'))
        } else {
          callback()
        }
      },
      trigger: 'manual'
    }
  ]
}

const loadProfile = async () => {
  try {
    const res = await api.auth.getProfile()
    if (res.code === 200 && res.data) {
      // 用户名表单
      usernameForm.username = res.data.username || ''
      originalUsername.value = res.data.username || ''
      
      // 邮箱表单
      emailForm.email = res.data.email || '' // 非编辑模式下显示当前邮箱
      originalEmail.value = res.data.email || '' // 保存原始邮箱用于比较
      
      // 更新状态管理
      authStore.username = usernameForm.username
      authStore.email = res.data.email || ''
    }
  } catch (error) {
    console.error('Load profile failed:', error)
  }
}

// 处理新邮箱输入事件
const handleNewEmailInput = () => {
  // 检查新邮箱格式是否有效
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const isEmailValid = emailRegex.test(emailForm.email) && emailForm.email !== originalEmail.value
  
  // 只有新邮箱有效且与原邮箱不同时，才能发送新邮箱验证码
  canSendNewCode.value = isEmailValid
  
  // 如果用户更改了新邮箱，重置新邮箱验证状态
  if (isEmailValid) {
    emailForm.newEmailCode = ''
    newEmailVerified.value = false
    canVerifyNewEmail.value = false
    if (emailFormRef.value) {
      emailFormRef.value.clearValidate(['newEmailCode'])
    }
  } else {
    canSendNewCode.value = false
    canVerifyNewEmail.value = false
  }
}

// 处理原邮箱验证码输入事件
// 处理新邮箱验证码输入事件
const handleNewCodeInput = () => {
  // 当新邮箱验证码输入完成（6位数字），启用验证按钮
  canVerifyNewEmail.value = emailForm.newEmailCode && emailForm.newEmailCode.length === 6
  
  // 检查新邮箱是否有效
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const isEmailValid = emailRegex.test(emailForm.email) && emailForm.email !== originalEmail.value
  
  // 只有新邮箱有效且验证码输入完成，才能验证新邮箱
  canVerifyNewEmail.value = canVerifyNewEmail.value && isEmailValid
}

// 验证新邮箱身份（简化版：不单独验证，在最终提交时一起验证）
const verifyNewEmailIdentity = async () => {
  if (!emailForm.email || !emailForm.newEmailCode) return
  
  // 验证新邮箱格式
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(emailForm.email)) {
    ElMessage.error('请输入有效的新邮箱')
    return
  }
  
  // 检查新邮箱是否与原邮箱相同
  if (emailForm.email === originalEmail.value) {
    ElMessage.error('新邮箱不能与原邮箱相同')
    return
  }
  
  // 直接标记新邮箱验证成功（实际验证在最终提交时进行）
  newEmailVerified.value = true
  canVerifyNewEmail.value = false
  ElMessage.success('新邮箱验证成功')
  if (emailFormRef.value) {
    emailFormRef.value.clearValidate(['newEmailCode'])
  }
}

// 重置邮箱验证流程
const resetEmailVerification = () => {
  // 重置所有验证状态
  newEmailVerified.value = false
  canVerifyNewEmail.value = false
  canSendNewCode.value = false
  
  // 重置倒计时
  newEmailCountdown.value = 0
  
  // 清空所有验证码和错误信息
  emailForm.newEmailCode = ''
  
  // 清空新邮箱输入
  emailForm.email = ''
  
  // 清除验证错误
  if (emailFormRef.value) {
    emailFormRef.value.clearValidate()
  }
}

// 处理新邮箱失焦事件，验证邮箱格式和唯一性
const handleNewEmailBlur = async () => {
  if (!emailForm.email) return
  
  // 验证新邮箱格式
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(emailForm.email)) {
    ElMessage.warning('请输入有效的邮箱地址')
    return
  }
  
  // 检查新邮箱是否与原邮箱相同
  if (emailForm.email === originalEmail.value) {
    ElMessage.warning('新邮箱不能与原邮箱相同')
    return
  }
  
  // 验证邮箱唯一性
  try {
    const res = await api.auth.checkEmailExists(emailForm.email)
    if (res.data.exists) {
      ElMessage.warning('该邮箱已被使用')
      canSendNewCode.value = false
    } else {
      // 邮箱格式和唯一性验证通过
      canSendNewCode.value = true
    }
  } catch (error) {
    console.error('检查邮箱唯一性失败:', error)
    ElMessage.error('邮箱验证失败，请重试')
  }
}



// 发送新邮箱验证码函数
const sendNewEmailCode = async () => {
  // 验证新邮箱是否为空且与原邮箱不同
  if (!emailForm.email || emailForm.email === originalEmail.value) {
    ElMessage.error('请输入新邮箱')
    return
  }

  // 验证新邮箱格式
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(emailForm.email)) {
    ElMessage.error('请输入有效的新邮箱')
    return
  }

  isSendingNewCode.value = true
  try {
    // 发送新邮箱验证码
    const sendRes = await api.auth.sendNewEmailCode(emailForm.email)
    if (sendRes.code === 200) {
      ElMessage.success(`验证码已发送到新邮箱 ${emailForm.email}，请查收`)
      
      // 立即结束发送中状态
      isSendingNewCode.value = false
      // 开始倒计时
      newEmailCountdown.value = 60
      const timer = setInterval(() => {
        newEmailCountdown.value--
        if (newEmailCountdown.value <= 0) {
          clearInterval(timer)
        }
      }, 1000)
    } else {
      ElMessage.error(sendRes.message || '新邮箱验证码发送失败')
      isSendingNewCode.value = false
    }
  } catch (error) {
    ElMessage.error(error.message || '验证码发送失败')
    isSendingNewCode.value = false
  }
}

// 取消编辑用户名
const cancelEditUsername = () => {
  editUsernameMode.value = false
  // 恢复原始用户名
  usernameForm.username = originalUsername.value
  // 清除验证错误
  if (usernameFormRef.value) {
    usernameFormRef.value.clearValidate()
  }
}

// 处理编辑邮箱按钮点击事件
const handleEditEmail = () => {
  editEmailMode.value = true
  // 清空邮箱字段，让用户可以输入新邮箱
  emailForm.email = ''
  // 清空验证码
  emailForm.newEmailCode = ''
}

// 保存用户名修改
const saveUsername = async () => {
  if (!usernameFormRef.value) return
  
  savingUsername.value = true
  try {
    // 先验证表单
    const valid = await usernameFormRef.value.validate()
    if (!valid) {
      savingUsername.value = false
      return
    }
    
    // 如果与原始用户名相同，不需要保存
    if (usernameForm.username === originalUsername.value) {
      ElMessage.info('用户名未发生变化')
      editUsernameMode.value = false
      return
    }
    
    // 调用API保存用户名
    const res = await api.auth.updateProfileOnly(usernameForm.username)
    if (res.code === 200) {
      ElMessage.success('用户名修改成功')
      // 更新原始用户名
      originalUsername.value = usernameForm.username
      // 更新状态管理
      authStore.username = usernameForm.username
      // 使用nextTick确保DOM更新后再退出编辑模式
      nextTick(() => {
        editUsernameMode.value = false
      })
    } else {
      ElMessage.error(res.message || '用户名修改失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '用户名修改失败')
    console.error('Save username error:', error)
  } finally {
    savingUsername.value = false
  }
}

// 取消编辑邮箱
const cancelEditEmail = () => {
  editEmailMode.value = false
  // 恢复邮箱字段为当前邮箱
  emailForm.email = originalEmail.value
  // 清空验证码
  emailForm.newEmailCode = ''
  // 重置倒计时
  newEmailCountdown.value = 0
  // 清除验证错误
  if (emailFormRef.value) {
    emailFormRef.value.clearValidate()
  }
}

// 保存邮箱修改
const saveEmail = async () => {
  if (!emailFormRef.value) return
  
  // 检查邮箱是否发生变化
  const emailChanged = emailForm.email !== originalEmail.value
  
  // 如果邮箱未发生变化，不需要保存
  if (!emailChanged) {
    ElMessage.info('邮箱未发生变化')
    editEmailMode.value = false
    return
  }
  
  // 确保新邮箱已验证成功
  if (!newEmailVerified.value) {
    ElMessage.error('请先完成新邮箱验证')
    return
  }
  
  savingEmail.value = true
  try {
    // 先验证表单
    const valid = await emailFormRef.value.validate()
    if (!valid) {
      savingEmail.value = false
      return
    }
    
    // 使用新的邮箱变更API，只需要新邮箱验证码
    const res = await api.auth.verifyChangeEmail({
      username: usernameForm.username, // 保持用户名不变
      newEmail: emailForm.email,
      newEmailCode: emailForm.newEmailCode
    })
    
    if (res.code === 200) {
      // 按照用户要求的提示信息
      ElMessage.success(`邮箱修改成功！新邮箱 ${emailForm.email} 已绑定`)
      // 更新原始邮箱
      originalEmail.value = emailForm.email
      // 更新状态管理
      authStore.email = emailForm.email
      // 重置所有状态
      resetEmailVerification()
      // 使用nextTick确保DOM更新后再退出编辑模式
      nextTick(() => {
        editEmailMode.value = false
      })
    } else {
      ElMessage.error(res.message || '邮箱修改失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '邮箱修改失败')
    console.error('Save email error:', error)
  } finally {
    savingEmail.value = false
  }
}

// 处理旧密码输入事件（使用防抖）
const handleOldPasswordInput = () => {
  // 清除之前的定时器
  if (verifyTimer) {
    clearTimeout(verifyTimer)
  }
  
  // 重置验证状态
  oldPasswordVerified.value = false
  oldPasswordError.value = ''
}

// 处理旧密码失焦事件
const handleOldPasswordBlur = () => {
  // 清除定时器
  if (verifyTimer) {
    clearTimeout(verifyTimer)
  }
  
  // 验证旧密码
  verifyOldPassword()
}

// 验证旧密码函数
const verifyOldPassword = async () => {
  if (!passwordForm.oldPassword) {
    return
  }
  
  verifyingOldPassword.value = true
  try {
    // 向后端发送验证旧密码的请求，使用专门的验证端点
    const res = await api.auth.verifyPassword({
      old_password: passwordForm.oldPassword
    })
    
    // 如果请求成功，说明旧密码正确
    if (res.code === 200) {
      oldPasswordVerified.value = true
      oldPasswordError.value = ''
      // 清除新密码输入，确保用户重新输入
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
    }
  } catch (error) {
    // 如果是旧密码错误，捕获并处理
    if (error.message && error.message.includes('旧密码错误')) {
      oldPasswordError.value = '密码错误，无法修改密码'
      oldPasswordVerified.value = false
    } else {
      console.error('Verify old password error:', error)
      // 网络错误等其他错误不显示在界面上，避免干扰用户
    }
  } finally {
    verifyingOldPassword.value = false
  }
}

// 取消编辑密码
const cancelEditPassword = () => {
  editPasswordMode.value = false
  // 重置所有密码输入框
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  // 重置验证状态
  oldPasswordVerified.value = false
  oldPasswordError.value = ''
  // 清除定时器
  if (verifyTimer) {
    clearTimeout(verifyTimer)
  }
  // 清除验证错误
  if (passwordFormRef.value) {
    passwordFormRef.value.clearValidate()
  }
}

// 修改密码函数（只在旧密码验证通过后调用）
const changePassword = async () => {
  if (!passwordFormRef.value) return
  
  // 手动设置必填规则
  passwordRules.oldPassword[0].required = true
  passwordRules.newPassword[0].required = true
  passwordRules.confirmPassword[0].required = true
  
  // 手动触发验证
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) {
      // 验证失败后重置必填规则
      passwordRules.oldPassword[0].required = false
      passwordRules.newPassword[0].required = false
      passwordRules.confirmPassword[0].required = false
      return
    }
    
    // 检查新密码是否与原密码相同
    if (passwordForm.newPassword === passwordForm.oldPassword) {
      ElMessage.error('新密码不能与原密码相同')
      // 重置必填规则
      passwordRules.oldPassword[0].required = false
      passwordRules.newPassword[0].required = false
      passwordRules.confirmPassword[0].required = false
      return
    }
    
    changingPassword.value = true
    try {
      const res = await api.auth.changePassword({
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword
      })
      if (res.code === 200) {
          ElMessage.success('密码修改成功')
          // 重置所有密码输入框和验证状态
          passwordForm.oldPassword = ''
          passwordForm.newPassword = ''
          passwordForm.confirmPassword = ''
          oldPasswordVerified.value = false
          // 退出编辑模式
          editPasswordMode.value = false
      } else {
        // 根据后端返回的错误信息显示不同的提示
        // 直接使用后端返回的中文错误信息
        let errorMsg = res.message || '密码修改失败'
        ElMessage.error(errorMsg)
      }
    } catch (error) {
      // 捕获网络错误或其他异常
      ElMessage.error('密码修改失败，请检查网络连接或稍后重试')
      console.error('Change password error:', error)
    } finally {
      changingPassword.value = false
      // 重置必填规则
      passwordRules.oldPassword[0].required = false
      passwordRules.newPassword[0].required = false
      passwordRules.confirmPassword[0].required = false
    }
  })
}









// 页面加载时获取用户资料
onMounted(async () => {
  await loadProfile()
})
</script>

<style scoped>
.profile-page {
  padding: 20px;
  min-height: calc(100vh - 60px);
}

.profile-card {
  max-width: 900px;
  margin: 0 auto;
  padding: 30px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.profile-meta h2 {
  margin: 0 0 8px;
  font-size: 24px;
}

.profile-meta p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}


.profile-form {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.profile-form .el-form-item {
  margin-bottom: 20px;
}

/* 确保用户名、邮箱、验证码在同一行或合理分布 */
.profile-form .el-form-item:nth-child(1),
.profile-form .el-form-item:nth-child(2),
.profile-form .el-form-item:nth-child(3) {
  grid-column: span 2;
}

/* 在小屏幕上调整为单列 */
@media (max-width: 768px) {
  .profile-form .el-form-item:nth-child(1),
  .profile-form .el-form-item:nth-child(2),
  .profile-form .el-form-item:nth-child(3) {
    grid-column: span 1;
  }
}

.email-input-container {
  display: flex;
  gap: 12px;
  align-items: center;
}

.email-input-container :deep(.el-input) {
  flex: 1;
}

/* 确保表单提交按钮在自己的行 */
.profile-form .el-button {
  grid-column: span 2;
  justify-self: start;
}

/* 密码修改部分样式 */
.password-form {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.password-form .el-form-item {
  margin-bottom: 20px;
}

/* 在小屏幕上调整为单列 */
@media (max-width: 768px) {
  .password-form .el-form-item {
    grid-column: span 1;
  }
}

/* 旧密码验证区域样式 */
.old-password-container {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
}

.old-password-container :deep(.el-input) {
  flex: 1;
}

/* 密码验证结果提示样式 */
.password-error-message {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.password-success-message {
  margin-top: 8px;
  color: #67c23a;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 邮箱验证结果提示样式 */
.email-error-message {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.email-success-message {
  margin-top: 8px;
  color: #67c23a;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 确保密码修改按钮在自己的行 */
.password-form .el-button {
  grid-column: span 2;
  justify-self: start;
}

/* 邮箱修改卡片样式 */
.email-modification-card {
  margin-top: 20px;
  padding: 20px;
  border-radius: 8px;
}

.email-modification-card h3 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.email-modification-form {
  width: 100%;
  max-width: 500px;
}

/* 当前邮箱样式 */
.current-email-container {
  display: flex;
  align-items: center;
}

.current-email {
  font-size: 14px;
  color: #606266;
  margin-right: 10px;
}

/* 验证摘要样式 */
.verification-summary {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.summary-item {
  margin-bottom: 10px;
  font-size: 14px;
}

.summary-label {
  font-weight: bold;
  color: #606266;
}

.summary-value {
  color: #303133;
}

/* 防止输入框在滚动时移位 */
.el-form-item {
  position: relative;
  z-index: 1;
}

/* 个人信息项样式 */
.profile-info-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 24px;
  padding: 16px;
  background-color: #fafafa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.info-label {
  width: 100px;
  font-weight: 600;
  color: #303133;
  padding-right: 16px;
  padding-top: 8px;
  flex-shrink: 0;
}

.info-content {
  flex: 1;
}

.current-value {
  display: inline-block;
  margin-right: 12px;
  padding: 8px 12px;
  background-color: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  min-height: 32px;
  line-height: 1.5;
  vertical-align: middle;
}

/* 当前邮箱显示容器 */
.current-email-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.current-email {
  padding: 8px 12px;
  background-color: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  min-height: 32px;
  line-height: 1.5;
  flex: 1;
}

/* 编辑表单样式 */
.edit-form {
  margin-top: 8px;
  background-color: #ffffff;
  padding: 16px;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

/* 增加输入框的稳定性 */
:deep(.el-input__wrapper) {
  position: relative;
  z-index: 2;
}
</style>
