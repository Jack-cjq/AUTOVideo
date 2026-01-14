<template>
  <div class="top-navbar">
    <div class="navbar-left">
      <div class="logo">
        <span class="logo-text">矩阵宝</span>
      </div>
      <div class="quick-actions">
        <el-button type="primary" size="large" @click="handlePublish"> 
          <el-icon><Plus /></el-icon>
          立即发布
        </el-button>
        <el-button type="primary" size="large" @click="handleAuthorize">
          <el-icon><Plus /></el-icon>
          添加授权
        </el-button>
      </div>
    </div>

    <div class="navbar-right">
      <el-badge :value="messageCount" :hidden="messageCount === 0" class="icon-badge">
        <el-icon class="navbar-icon" size="20"><Message /></el-icon>   
      </el-badge>
      <el-badge :value="notificationCount" :hidden="notificationCount === 0" class="icon-badge">
        <el-icon class="navbar-icon" size="20"><Bell /></el-icon>      
      </el-badge>

      <el-dropdown @command="handleUserCommand">
        <div class="user-info">
          <el-avatar :size="32" :src="authStore.avatarUrl" />
          <span class="username">{{ authStore.email || authStore.username || '用户' }}</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人资料</el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const messageCount = ref(0)
const notificationCount = ref(0)

const handlePublish = () => {
  router.push('/publish')
}

const handleAuthorize = () => {
  console.log('添加授权')
}

const handleUserCommand = async (command) => {
  if (command === 'logout') {
    await authStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.top-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: 1000;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 30px;
}

.logo {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
}

.logo-text {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.quick-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.icon-badge {
  cursor: pointer;
}

.navbar-icon {
  color: #606266;
  cursor: pointer;
  transition: color 0.3s;
}

.navbar-icon:hover {
  color: #409eff;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  transition: background 0.3s;
}

.user-info:hover {
  background: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #303133;
}
</style>
