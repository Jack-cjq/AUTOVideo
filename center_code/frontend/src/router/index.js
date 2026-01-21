import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guestOnly: true, title: 'Login' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guestOnly: true, title: 'Register' }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../views/ResetPassword.vue'),
    meta: { guestOnly: true, title: 'Reset Password' }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { requiresAuth: true, title: 'Dashboard' }
      },
      {
        path: 'publish',
        name: 'Publish',
        component: () => import('../views/Publish.vue'),
        meta: { requiresAuth: true, title: 'Publish' }
      },
      {
        path: 'publish-plan',
        name: 'PublishPlan',
        component: () => import('../views/PublishPlan.vue'),
        meta: { requiresAuth: true, title: 'Publish Plan' }
      },
      {
        path: 'publish-history',
        name: 'PublishHistory',
        component: () => import('../views/PublishHistory.vue'),
        meta: { requiresAuth: true, title: 'Publish History' }
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('../views/Accounts.vue'),
        meta: { requiresAuth: true, title: 'Accounts' }
      },
      {
        path: 'data-center',
        name: 'DataCenter',
        component: () => import('../views/DataCenter.vue'),
        meta: { requiresAuth: true, title: 'Data Center' }
      },
      {
        path: 'merchants',
        name: 'Merchants',
        component: () => import('../views/Merchants.vue'),
        meta: { requiresAuth: true, title: 'Merchants' }
      },
      {
        path: 'video-library',
        name: 'VideoLibrary',
        component: () => import('../views/VideoLibrary.vue'),
        meta: { requiresAuth: true, title: 'Video Library' }
      },
      {
        path: 'video-editor',
        name: 'VideoEditor',
        // Use the same page container as VideoLibrary so the editor and cloud library
        // can share timeline/material state and switch views smoothly.
        component: () => import('../views/VideoLibrary.vue'),
        meta: { requiresAuth: true, title: 'Video Editor' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue'),
        meta: { requiresAuth: true, title: 'Profile' }
      },

    ]
  },
  {
    path: '/login-helper',
    name: 'LoginHelper',
    component: () => import('../views/LoginHelper.vue'),
    meta: { requiresAuth: true }
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

  const needsAuth = to.meta.requiresAuth
  const isGuestOnly = to.meta.guestOnly

  if (needsAuth) {
    if (authStore.isLoggedIn) {
      return next()
    }
    if (authStore.token) {
      const ok = await authStore.checkLogin()
      if (ok) {
        return next()
      }
    }
    return next('/login')
  }

  if (isGuestOnly) {
    if (authStore.isLoggedIn) {
      return next('/')
    }
    if (authStore.token) {
      const ok = await authStore.checkLogin()
      if (ok) {
        return next('/')
      }
    }
  }

  return next()
})

export default router
