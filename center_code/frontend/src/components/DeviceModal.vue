<template>
  <el-dialog
    v-model="dialogVisible"
    title="设备管理"
    width="80%"
    :before-close="handleClose"
  >
    <div style="padding: 20px; text-align: center; color: #666; margin-bottom: 20px;">
      <p style="margin-bottom: 15px;">设备由客户端自动注册，无需手动注册</p>
      <p style="font-size: 12px; color: #999;">客户端启动时会自动注册设备并发送心跳</p>
    </div>

    <el-table
      v-loading="loading"
      :data="devices"
      style="width: 100%"
      stripe
    >
      <el-table-column prop="device_id" label="设备ID" width="200" />
      <el-table-column prop="device_name" label="设备名称" />
      <el-table-column prop="ip_address" label="IP地址" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'online' ? 'success' : 'danger'">
            {{ row.status === 'online' ? '在线' : '离线' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_heartbeat" label="最后心跳" />
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" @click="loadDevices" :loading="loading">刷新</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import api from '../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const devices = ref([])
const loading = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) {
    loadDevices()
  }
})

const loadDevices = async () => {
  loading.value = true
  try {
    const res = await api.devices.list()
    if (res.code === 200) {
      devices.value = res.data || []
    }
  } catch (error) {
    console.error('Load devices error:', error)
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
    emit('update:modelValue', false)
}
</script>

