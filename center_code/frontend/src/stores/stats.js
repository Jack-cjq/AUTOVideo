import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useStatsStore = defineStore('stats', () => {
  const onlineDevices = ref('-')
  const loggedInAccounts = ref('-')
  const pendingTasks = ref('-')
  const systemStatus = ref('-')

  const loadStats = async () => {
    try {
      const res = await api.stats.get()
      if (res.code === 200) {
        onlineDevices.value = res.data.online_devices || 0
        loggedInAccounts.value = res.data.logged_in_accounts || 0
        const pending = (res.data.pending_video_tasks || 0) + (res.data.pending_chat_tasks || 0)
        pendingTasks.value = pending
        systemStatus.value = '正常'
      }
    } catch (error) {
      console.error('Load stats error:', error)
      systemStatus.value = '离线'
    }
  }

  return {
    onlineDevices,
    loggedInAccounts,
    pendingTasks,
    systemStatus,
    loadStats
  }
})

