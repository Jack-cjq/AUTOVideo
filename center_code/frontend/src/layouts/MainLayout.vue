<template>
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <TopNavbar />
    
    <div class="layout-body">
      <!-- 左侧导航栏 -->
      <SideNavbar :collapsed="sidebarCollapsed" @toggle="sidebarCollapsed = !sidebarCollapsed" />
      
      <!-- 主内容区 -->
      <div class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <router-view v-if="$route.matched.length > 0" />
        <div v-else style="padding: 20px;">
          <h2>页面加载中...</h2>
          <p>如果长时间显示此页面，请检查控制台错误信息。</p>
        </div>
      </div>
    </div>
    
    <!-- 登录对话框 -->
    <LoginDialog v-model="authStore.showLoginDialog" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import TopNavbar from '../components/layout/TopNavbar.vue'
import SideNavbar from '../components/layout/SideNavbar.vue'
import LoginDialog from '../components/LoginDialog.vue'

const authStore = useAuthStore()
const sidebarCollapsed = ref(false)
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  background: #f5f7fa;
}

.layout-body {
  display: flex;
  height: calc(100vh - 60px);
  margin-top: 60px;
}

.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  transition: margin-left 0.3s;
  margin-left: 200px;
}

.main-content.sidebar-collapsed {
  margin-left: 64px;
}
</style>

