<template>
  <div style="padding: 20px;">
    <h1>测试页面</h1>
    <p>如果你能看到这个页面，说明路由和组件加载正常。</p>
    <el-button type="primary" @click="test">测试按钮</el-button>
    <p>登录状态: {{ authStore.isLoggedIn ? '已登录' : '未登录' }}</p>
    <p>用户名: {{ authStore.username || '无' }}</p>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
const authStore = useAuthStore()

const test = () => {
  alert('按钮点击正常！')
}
</script>

