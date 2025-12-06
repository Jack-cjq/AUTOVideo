import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const isLoggedIn = ref(false)
  const username = ref('')
  const showLoginDialog = ref(false)
  const isCheckingLogin = ref(false)  // 标记是否正在检查登录状态

  const checkLogin = async () => {
    // 如果正在检查，直接返回当前状态
    if (isCheckingLogin.value) {
      return isLoggedIn.value
    }
    
    isCheckingLogin.value = true
    try {
      console.log('Checking login status...')
      const res = await api.auth.checkLogin()
      console.log('Login check response:', res)
      if (res && res.code === 200 && res.data && res.data.logged_in) {
        isLoggedIn.value = true
        username.value = res.data.username || ''
        showLoginDialog.value = false  // 已登录，确保不显示登录对话框
        console.log('User is logged in:', username.value)
        return true
      } else {
        isLoggedIn.value = false
        username.value = ''
        console.log('User is not logged in')
        // 如果未登录，显示登录对话框
        showLoginDialog.value = true
        return false
      }
    } catch (error) {
      console.error('Check login error:', error)
      isLoggedIn.value = false
      // 只有在网络错误时才显示登录对话框，如果是401等认证错误，说明确实未登录
      if (!error.code || error.code === 500) {
        // 网络错误或服务器错误，可能是后端未运行，显示登录对话框
        console.log('Showing login dialog due to network/server error')
        showLoginDialog.value = true
      } else {
        // 其他错误（如401），说明确实未登录
        showLoginDialog.value = true
      }
      return false
    } finally {
      isCheckingLogin.value = false
    }
  }

  const login = async (usernameInput, password) => {
    try {
      const res = await api.auth.login(usernameInput, password)
      if (res.code === 200) {
        isLoggedIn.value = true
        username.value = res.data.username || usernameInput
        showLoginDialog.value = false
        return { success: true }
      } else {
        return { success: false, message: res.message || '登录失败' }
      }
    } catch (error) {
      return { success: false, message: error.message || '登录失败' }
    }
  }

  const logout = async () => {
    try {
      await api.auth.logout()
      isLoggedIn.value = false
      username.value = ''
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  return {
    isLoggedIn,
    username,
    showLoginDialog,
    isCheckingLogin,
    checkLogin,
    login,
    logout
  }
})

