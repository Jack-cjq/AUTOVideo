<template>
  <el-config-provider :locale="locale">
    <div id="app-container">
      <router-view v-if="isInitialized" />
      <div v-else class="loading-container">
        <el-loading :loading="true" text="正在初始化..." />
      </div>
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const locale = zhCn
const isInitialized = ref(false)
const authStore = useAuthStore()

onMounted(async () => {
  console.log('App mounted, checking login...')
  try {
    const isLoggedIn = await authStore.checkLogin()
    console.log('Login check completed, isLoggedIn:', isLoggedIn)
    // checkLogin 内部已经处理了 showLoginDialog 的设置，这里不需要再设置
  } catch (error) {
    console.error('初始化失败:', error)
    // 即使检查登录失败，也显示页面（让用户看到登录对话框）
  } finally {
    // 无论成功失败，都显示页面
    console.log('Setting isInitialized to true')
    isInitialized.value = true
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  width: 100%;
  height: 100%;
}

#app-container {
  width: 100%;
  min-height: 100vh;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
  min-height: 100vh;
  margin: 0;
  padding: 0;
}

.loading-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>

