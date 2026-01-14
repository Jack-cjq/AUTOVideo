<template>
  <div class="home-container">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <div>
            <h1>🎬 抖音中心管理平台</h1>
            <p>轻量级设备管理系统，支持远程登录、视频上传和对话功能</p>
          </div>
          <div v-if="authStore.isLoggedIn" class="user-info">
            <span>欢迎，{{ authStore.username }}</span>
            <el-button type="info" size="small" @click="handleLogout">登出</el-button>
          </div>
        </div>
      </el-header>

      <el-main>
        <!-- 统计卡片 -->
        <el-row :gutter="20" class="stats-grid">
          <el-col :xs="12" :sm="12" :md="6" :lg="6">
            <el-card class="stat-card">
              <div class="stat-content">
                <h3>在线设备</h3>
                <div class="number">{{ stats.onlineDevices }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="12" :sm="12" :md="6" :lg="6">
            <el-card class="stat-card">
              <div class="stat-content">
                <h3>已登录账号</h3>
                <div class="number">{{ stats.loggedInAccounts }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="12" :sm="12" :md="6" :lg="6">
            <el-card class="stat-card">
              <div class="stat-content">
                <h3>待处理任务</h3>
                <div class="number">{{ stats.pendingTasks }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="12" :sm="12" :md="6" :lg="6">
            <el-card class="stat-card">
              <div class="stat-content">
                <h3>系统状态</h3>
                <div class="number">{{ stats.systemStatus }}</div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 功能卡片 -->
        <el-row :gutter="20" class="main-grid">
          <el-col :xs="24" :sm="12" :md="12" :lg="6">
            <el-card class="feature-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">📱</span>
                  <span>设备管理</span>
                </div>
              </template>
              <p>查看客户端设备状态，设备由客户端自动注册</p>
              <ul class="feature-list">
                <li>设备自动注册</li>
                <li>在线状态监控</li>
                <li>心跳检测</li>
                <li>设备详情查看</li>
              </ul>
              <el-button type="primary" @click="showDeviceModal">查看设备</el-button>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="12" :lg="6">
            <el-card class="feature-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">👤</span>
                  <span>账号管理</span>
                </div>
              </template>
              <p>绑定账号到客户端，每个客户端对应一个账号（一对一）</p>
              <ul class="feature-list">
                <li>账号绑定（通过设备ID）</li>
                <li>登录状态管理</li>
                <li>一对一关系</li>
                <li>Cookie管理</li>
              </ul>
              <el-button type="primary" @click="showAccountModal">管理账号</el-button>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="12" :lg="6">
            <el-card class="feature-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">🎥</span>
                  <span>视频上传</span>
                </div>
              </template>
              <p>下发视频上传任务，跟踪上传进度</p>
              <ul class="feature-list">
                <li>任务下发</li>
                <li>进度跟踪</li>
                <li>元数据管理</li>
                <li>批量操作</li>
              </ul>
              <el-button type="primary" @click="showVideoModal">创建任务</el-button>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="12" :lg="6">
            <el-card class="feature-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">💬</span>
                  <span>消息管理</span>
                </div>
              </template>
              <p>监听和发送消息，管理多账号对话</p>
              <ul class="feature-list">
                <li>消息监听</li>
                <li>消息查阅</li>
                <li>消息发送</li>
                <li>多账号支持</li>
              </ul>
              <el-button type="primary" @click="showMessageModal">管理消息</el-button>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>

    <!-- 登录对话框 -->

    <!-- 设备管理对话框 -->
    <DeviceModal v-model="deviceModalVisible" />

    <!-- 账号管理对话框 -->
    <AccountModal v-model="accountModalVisible" />

    <!-- 视频上传对话框 -->
    <VideoModal v-model="videoModalVisible" />

    <!-- 消息管理对话框 -->
    <MessageModal v-model="messageModalVisible" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useStatsStore } from '../stores/stats'
import DeviceModal from '../components/DeviceModal.vue'
import AccountModal from '../components/AccountModal.vue'
import VideoModal from '../components/VideoModal.vue'
import MessageModal from '../components/MessageModal.vue'

const authStore = useAuthStore()
const statsStore = useStatsStore()

const deviceModalVisible = ref(false)
const accountModalVisible = ref(false)
const videoModalVisible = ref(false)
const messageModalVisible = ref(false)

const stats = computed(() => ({
  onlineDevices: statsStore.onlineDevices || '-',
  loggedInAccounts: statsStore.loggedInAccounts || '-',
  pendingTasks: statsStore.pendingTasks || '-',
  systemStatus: statsStore.systemStatus || '-'
}))

let statsInterval = null

onMounted(async () => {
  if (authStore.isLoggedIn) {
    await statsStore.loadStats()
    statsInterval = setInterval(() => {
      statsStore.loadStats()
    }, 5000)
  }
})

onUnmounted(() => {
  if (statsInterval) {
    clearInterval(statsInterval)
  }
})

const showDeviceModal = () => {
  if (!authStore.isLoggedIn) {
    return
  }
  deviceModalVisible.value = true
}

const showAccountModal = () => {
  if (!authStore.isLoggedIn) {
    return
  }
  accountModalVisible.value = true
}

const showVideoModal = () => {
  if (!authStore.isLoggedIn) {
    return
  }
  videoModalVisible.value = true
}

const showMessageModal = () => {
  if (!authStore.isLoggedIn) {
    return
  }
  messageModalVisible.value = true
}

const handleLogout = async () => {
  await authStore.logout()
  if (statsInterval) {
    clearInterval(statsInterval)
    statsInterval = null
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  padding: 20px;
}

.header {
  background: white;
  border-radius: 10px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  color: #333;
  font-size: 28px;
  margin-bottom: 10px;
}

.header p {
  color: #666;
  font-size: 14px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stats-grid {
  margin-bottom: 30px;
}

.stat-card {
  text-align: center;
}

.stat-content h3 {
  color: #666;
  font-size: 14px;
  margin-bottom: 10px;
  text-transform: uppercase;
}

.stat-content .number {
  color: #667eea;
  font-size: 32px;
  font-weight: bold;
}

.main-grid {
  margin-top: 20px;
}

.feature-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
}

.card-icon {
  font-size: 24px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 15px 0;
  font-size: 13px;
  color: #666;
}

.feature-list li {
  padding: 5px 0;
  padding-left: 20px;
  position: relative;
}

.feature-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #667eea;
}
</style>

