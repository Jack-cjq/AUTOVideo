<template>
  <div class="side-navbar" :class="{ collapsed: collapsed }">
    <div class="collapse-btn" @click="$emit('toggle')">
      <el-icon><ArrowLeft v-if="!collapsed" /><ArrowRight v-else /></el-icon>
    </div>
    
    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      :collapse-transition="false"
      router
      class="sidebar-menu"
    >
      <el-menu-item index="/dashboard" route="/dashboard">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>首页</template>
      </el-menu-item>
      
      <el-menu-item index="/publish">
        <el-icon><Promotion /></el-icon>
        <template #title>立即发布</template>
      </el-menu-item>
      
      <el-menu-item index="/publish-plan">
        <el-icon><Calendar /></el-icon>
        <template #title>发布计划</template>
      </el-menu-item>
      
      <el-menu-item index="/publish-history">
        <el-icon><Clock /></el-icon>
        <template #title>发布历史</template>
      </el-menu-item>
      
      <el-menu-item index="/accounts">
        <el-icon><UserFilled /></el-icon>
        <template #title>授权管理</template>
      </el-menu-item>
      
      <el-menu-item index="/data-center">
        <el-icon><DataAnalysis /></el-icon>
        <template #title>数据中心</template>
      </el-menu-item>
      
      <el-menu-item index="/merchants">
        <el-icon><OfficeBuilding /></el-icon>
        <template #title>商家管理</template>
      </el-menu-item>
      
      <el-menu-item index="/video-library">
        <el-icon><VideoCamera /></el-icon>
        <template #title>云视频库</template>
      </el-menu-item>
      
      <el-menu-item index="/video-editor">
        <el-icon><Edit /></el-icon>
        <template #title>AI视频剪辑</template>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
// 图标已在 main.js 中全局注册

defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle'])

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.side-navbar {
  position: fixed;
  left: 0;
  top: 60px;
  width: 200px;
  height: calc(100vh - 60px);
  background: #e6f7ff;
  transition: width 0.3s;
  z-index: 999;
}

.side-navbar.collapsed {
  width: 64px;
}

.collapse-btn {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #bae7ff;
  border-bottom: 1px solid #91d5ff;
  transition: background 0.3s;
}

.collapse-btn:hover {
  background: #91d5ff;
}

.sidebar-menu {
  border: none;
  background: #e6f7ff;
  height: calc(100% - 40px);
  overflow-y: auto;
}

.sidebar-menu :deep(.el-menu-item) {
  color: #1890ff;
  height: 50px;
  line-height: 50px;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: #1890ff;
  color: #fff;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: #bae7ff;
  color: #1890ff;
}

.sidebar-menu :deep(.el-menu-item.is-active:hover) {
  background: #1890ff;
  color: #fff;
}
</style>

