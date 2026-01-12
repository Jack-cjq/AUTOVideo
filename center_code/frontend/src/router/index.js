import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { requiresAuth: true, title: '首页' }
      },
      {
        path: 'publish',
        name: 'Publish',
        component: () => import('../views/Publish.vue'),
        meta: { requiresAuth: true, title: '立即发布' }
      },
      {
        path: 'publish-plan',
        name: 'PublishPlan',
        component: () => import('../views/PublishPlan.vue'),
        meta: { requiresAuth: true, title: '发布计划' }
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('../views/Accounts.vue'),
        meta: { requiresAuth: true, title: '授权管理' }
      },
      {
        path: 'data-center',
        name: 'DataCenter',
        component: () => import('../views/DataCenter.vue'),
        meta: { requiresAuth: true, title: '数据中心' }
      },
      {
        path: 'merchants',
        name: 'Merchants',
        component: () => import('../views/Merchants.vue'),
        meta: { requiresAuth: true, title: '商家管理' }
      },
      {
        path: 'video-library',
        name: 'VideoLibrary',
        component: () => import('../views/VideoLibrary.vue'),
        meta: { requiresAuth: true, title: '云视频库' }
      },
      {
        path: 'video-editor',
        name: 'VideoEditor',
        component: () => import('../views/VideoLibrary.vue'),
        meta: { requiresAuth: true, title: 'AI视频剪辑' }
      }
    ]
  },
  {
    path: '/login-helper',
    name: 'LoginHelper',
    component: () => import('../views/LoginHelper.vue')
  },
  {
    path: '/test',
    name: 'Test',
    component: () => import('../views/TestPage.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 如果路由需要认证，先检查登录状态
  if (to.meta.requiresAuth) {
    // 如果正在检查登录状态，等待检查完成
    if (authStore.isCheckingLogin) {
      // 等待检查完成（轮询等待，最多等待 5 秒）
      let waitCount = 0
      while (authStore.isCheckingLogin && waitCount < 50) {
        await new Promise(resolve => setTimeout(resolve, 100))
        waitCount++
      }
    }
    
    // 如果还没有检查过登录状态（不在检查中且未登录），先检查
    if (!authStore.isCheckingLogin && !authStore.isLoggedIn) {
      // 等待登录检查完成
      const isLoggedIn = await authStore.checkLogin()
      
      // 检查完成后，如果仍未登录，显示登录对话框
      if (!isLoggedIn) {
        authStore.showLoginDialog = true
        // 注意：这里仍然允许导航，让用户看到页面和登录对话框
        // 如果希望阻止未登录用户访问，可以改为：next(false) 或 next('/login')
      }
    } else if (authStore.isLoggedIn) {
      // 已登录，确保不显示登录对话框
      authStore.showLoginDialog = false
    } else if (!authStore.isLoggedIn && !authStore.isCheckingLogin) {
      // 未登录且不在检查中，显示登录对话框
      authStore.showLoginDialog = true
    }
  } else {
    // 不需要认证的路由，确保不显示登录对话框
    authStore.showLoginDialog = false
  }
  
  // 允许导航（即使未登录也允许，让用户看到登录对话框）
  // 如果需要更严格的控制，可以在未登录时阻止导航：
  // if (to.meta.requiresAuth && !authStore.isLoggedIn) {
  //   next(false) // 阻止导航
  // } else {
  //   next()
  // }
  next()
})

export default router

