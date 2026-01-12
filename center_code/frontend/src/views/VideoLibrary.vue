<template>
  <div class="video-library-container">
    <!-- 主内容区 -->
    <div class="main-content">
      <div class="topbar">
        <div class="topbar-title">{{ pageTitle }}</div>
        <div class="topbar-actions" v-if="currentView === 'cloud'">
          <label class="btn" title="上传素材（视频/音频）">
            <input 
              ref="uploadInput" 
              type="file" 
              style="display:none" 
              accept=".mp4,.avi,.mov,.mp3,.wav,.flac"
              @change="handleUpload"
            />
            <span>上传素材</span>
          </label>
          <button class="btn danger" @click="handleClearMaterials" title="清空素材库（视频/音频）">
            <span>清空素材库</span>
          </button>
        </div>
      </div>

      <!-- 云素材库视图 -->
      <section class="view" :class="{ active: currentView === 'cloud' }" v-if="currentView === 'cloud'">
        <div class="tabs">
          <div 
            class="tab" 
            :class="{ active: cloudTab === 'videos' }"
            @click="setCloudTab('videos')"
          >
            视频素材库
          </div>
          <div 
            class="tab" 
            :class="{ active: cloudTab === 'outputs' }"
            @click="setCloudTab('outputs')"
          >
            成品库
          </div>
          <div 
            class="tab" 
            :class="{ active: cloudTab === 'bgm' }"
            @click="setCloudTab('bgm')"
          >
            BGM库
          </div>
        </div>

        <div class="panel">
          <div class="row">
            <div class="field">
              <div class="label">搜索（按文件名）</div>
              <input 
                v-model="cloudSearch" 
                class="input" 
                placeholder="输入关键词搜索…"
                @input="renderCloud"
              />
            </div>
            <div class="field">
              <div class="label">筛选（预留）</div>
              <select v-model="cloudFilter" class="select" @change="renderCloud">
                <option value="all">全部</option>
                <option value="recent">最近上传/生成</option>
              </select>
            </div>
          </div>
          <div class="label" style="margin-top:10px;">
            提示：点击"添加到剪辑轨道"可在 AI 模块一键生成，无需输入编号。
          </div>
          <div class="grid" ref="cloudGrid"></div>
        </div>
      </section>

      <!-- AI视频剪辑视图 -->
      <section class="view" :class="{ active: currentView === 'ai' }" v-if="currentView === 'ai'">
        <VideoEditorView 
          :materials="materials"
          :timeline="timeline"
          @update-timeline="updateTimeline"
          @refresh-materials="bootstrapData"
          @refresh-outputs="loadOutputs"
          @open-outputs="() => { setView('cloud'); setCloudTab('outputs'); }"
          @preview-audio="(url) => openModal('TTS 试听', 'audio', url)"
        />
      </section>
    </div>

    <!-- Toast 提示 -->
    <div class="toast" :class="{ show: toast.show }" ref="toast">
      {{ toast.message }}
    </div>

    <!-- 预览模态框 -->
    <div class="mask" :class="{ show: modal.show }" @click="handleMaskClick">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <div class="modal-title">{{ modal.title }}</div>
          <button class="modal-close" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <video 
            v-if="modal.kind === 'video'"
            ref="modalVideo"
            class="media" 
            controls
            :src="modal.url"
          ></video>
          <audio 
            v-if="modal.kind === 'audio'"
            ref="modalAudio"
            class="audio" 
            controls
            preload="auto"
          ></audio>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import VideoEditorView from './VideoEditorView.vue'
import * as materialApi from '../api/material'
import * as editorApi from '../api/editor'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()

// 状态管理
const currentView = ref('cloud')
const cloudTab = ref('videos')
const cloudSearch = ref('')
const cloudFilter = ref('all')
const materials = ref([])
const outputs = ref([])
const timeline = ref({
  clips: [],
  voice: null,
  bgm: null,
  global: { speed: 1.0 }
})

// UI 状态
const toast = ref({ show: false, message: '' })
const modal = ref({ show: false, title: '', kind: '', url: '' })
const uploadInput = ref(null)
const cloudGrid = ref(null)
const modalVideo = ref(null)
const modalAudio = ref(null)

// 计算属性
const pageTitle = computed(() => {
  return currentView.value === 'cloud' ? '云素材库' : 'AI视频剪辑'
})

// 工具函数
function showToast(message, type = 'info', duration = 2500) {
  toast.value = { show: true, message }
  setTimeout(() => {
    toast.value.show = false
  }, duration)
}

function openModal(title, kind, url) {
  if (!url) {
    showToast('预览地址无效', 'error')
    return
  }
  
  // 确保 URL 是完整的（如果是相对路径，添加基础路径）
  let fullUrl = url
  if (url.startsWith('/')) {
    // 相对路径，直接使用（会被代理处理）
    fullUrl = url
  } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
    // 可能是相对路径但没有前导斜杠
    fullUrl = '/' + url
  }
  
  console.log('[VideoLibrary] 打开预览模态框:', { title, kind, url, fullUrl })
  
  modal.value = { show: true, title, kind, url: fullUrl }
  
  // 对于音频，立即尝试播放（因为用户已经点击了试听按钮，在用户交互上下文中）
  if (kind === 'audio') {
    // 使用 requestAnimationFrame 确保在下一个渲染帧中执行，此时模态框已经显示
    requestAnimationFrame(() => {
      nextTick(() => {
        if (modalAudio.value) {
          const audio = modalAudio.value
          audio.src = fullUrl
          
          // 清除之前的事件监听器
          audio.onerror = null
          audio.onloadeddata = null
          audio.oncanplay = null
          audio.oncanplaythrough = null
          audio.onstalled = null
          audio.onabort = null
          audio.onplay = null
          audio.onpause = null
          audio.onvolumechange = null
          
          audio.onerror = (e) => {
            console.error('[VideoLibrary] 音频加载失败:', {
              error: audio.error,
              errorCode: audio.error?.code,
              errorMessage: audio.error?.message,
              networkState: audio.networkState,
              readyState: audio.readyState,
              src: fullUrl,
              event: e
            })
            let errorMsg = '音频加载失败'
            if (audio.error) {
              switch (audio.error.code) {
                case audio.error.MEDIA_ERR_ABORTED:
                  errorMsg = '音频加载被中止'
                  break
                case audio.error.MEDIA_ERR_NETWORK:
                  errorMsg = '网络错误，无法加载音频'
                  break
                case audio.error.MEDIA_ERR_DECODE:
                  errorMsg = '音频解码失败'
                  break
                case audio.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                  errorMsg = '音频格式不支持或文件不存在'
                  break
              }
            }
            showToast(errorMsg, 'error')
          }
          audio.onloadeddata = () => {
            console.log('[VideoLibrary] 音频元数据加载成功:', {
              duration: audio.duration,
              src: fullUrl,
              volume: audio.volume,
              muted: audio.muted,
              paused: audio.paused
            })
            
            // 确保音量设置正确
            audio.volume = 1.0
            audio.muted = false
            
            // 尝试自动播放（在元数据加载后，此时仍在用户交互上下文中）
            audio.play().catch(err => {
              console.log('[VideoLibrary] 自动播放需要用户交互，请手动点击播放按钮:', err.message)
              // 不显示错误，因为这是正常的浏览器行为
            })
          }
          audio.oncanplay = () => {
            console.log('[VideoLibrary] 音频可以播放:', {
              src: fullUrl,
              volume: audio.volume,
              muted: audio.muted,
              paused: audio.paused
            })
          }
          audio.oncanplaythrough = () => {
            console.log('[VideoLibrary] 音频可以完整播放:', fullUrl)
            // 再次确保音量设置
            audio.volume = 1.0
            audio.muted = false
          }
          audio.onstalled = () => {
            console.warn('[VideoLibrary] 音频加载停滞:', fullUrl)
          }
          audio.onabort = () => {
            console.warn('[VideoLibrary] 音频加载被中止:', fullUrl)
          }
          audio.onplay = () => {
            console.log('[VideoLibrary] 音频开始播放:', fullUrl)
          }
          audio.onpause = () => {
            console.log('[VideoLibrary] 音频已暂停:', fullUrl)
          }
          audio.onvolumechange = () => {
            console.log('[VideoLibrary] 音量变化:', {
              volume: audio.volume,
              muted: audio.muted
            })
          }
          
          // 设置音量（确保不是静音）
          audio.volume = 1.0
          audio.muted = false
          
          console.log('[VideoLibrary] 开始加载音频:', fullUrl)
          audio.load()
          
          // 延迟尝试自动播放（等待加载完成）
          setTimeout(() => {
            if (audio.readyState >= 2) { // HAVE_CURRENT_DATA
              audio.play().catch(err => {
                console.log('[VideoLibrary] 自动播放需要用户交互，请手动点击播放按钮')
                // 不显示错误，因为这是正常的浏览器行为
              })
            }
          }, 100)
        }
      })
    })
    return
  }
  
  nextTick(() => {
    if (kind === 'video' && modalVideo.value) {
      const video = modalVideo.value
      video.src = fullUrl
      
      // 清除之前的事件监听器
      video.onerror = null
      video.onloadeddata = null
      video.oncanplay = null
      
      video.onerror = (e) => {
        console.error('[VideoLibrary] 视频加载失败:', e, video.error, fullUrl)
        showToast('视频加载失败，请检查文件是否存在', 'error')
      }
      video.onloadeddata = () => {
        console.log('[VideoLibrary] 视频加载成功:', fullUrl)
      }
      video.oncanplay = () => {
        console.log('[VideoLibrary] 视频可以播放:', fullUrl)
      }
      
      video.load()
    }
    // 注意：音频处理已经在上面提前返回了，这里不再处理
  })
}

function closeModal() {
  if (modalVideo.value) {
    modalVideo.value.pause()
    modalVideo.value.src = ''
    modalVideo.value.onerror = null
  }
  if (modalAudio.value) {
    modalAudio.value.pause()
    modalAudio.value.src = ''
    modalAudio.value.onerror = null
    modalAudio.value.onloadeddata = null
  }
  modal.value.show = false
}

function handleMaskClick(e) {
  if (e.target.id === 'mask') {
    closeModal()
  }
}

function toUploadsUrl(path) {
  if (!path) return ''
  const p = String(path).replace(/\\/g, '/')
  const idx = p.indexOf('uploads/')
  if (idx >= 0) return `/uploads/${p.slice(idx + 'uploads/'.length)}`
  return `/uploads/${p.replace(/^\/+/, '')}`
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, '0')}`
}

function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// 视图切换
function setView(view) {
  currentView.value = view
  localStorage.setItem('ve.activeView', view)
  if (view === 'cloud') {
    renderCloud()
  }
  // 根据视图切换路由（但不触发导航，避免页面刷新）
  if (view === 'cloud' && route.name === 'VideoEditor') {
    router.replace({ name: 'VideoLibrary', query: {} })
  } else if (view === 'ai' && route.name === 'VideoLibrary') {
    router.replace({ name: 'VideoEditor' })
  }
}

function setCloudTab(tab) {
  cloudTab.value = tab
  localStorage.setItem('ve.cloudTab', tab)
  renderCloud()
}

// 数据加载
async function loadMaterials() {
  try {
    const response = await materialApi.getMaterials({ type: null })
    if (response.code === 200) {
      // 后端返回的 data 直接是数组，不是 { materials: [...] }
      materials.value = Array.isArray(response.data) ? response.data : (response.data?.materials || [])
      console.log('[VideoLibrary] 加载素材成功:', {
        total: materials.value.length,
        videos: materials.value.filter(m => m.type === 'video').length,
        audios: materials.value.filter(m => m.type === 'audio').length,
        all: materials.value
      })
    }
  } catch (error) {
    console.error('[VideoLibrary] 加载素材失败:', error)
    showToast(`加载素材失败：${error.message || '未知错误'}`, 'error')
  }
}

async function loadOutputs() {
  try {
    const response = await materialApi.getOutputs()
    if (response.code === 200) {
      outputs.value = response.data || []
    }
  } catch (error) {
    showToast(`加载成品失败：${error.message || '未知错误'}`, 'error')
  }
}

async function bootstrapData() {
  await Promise.all([loadMaterials(), loadOutputs()])
  await nextTick()
  renderCloud()
}

// 渲染云素材库
function renderCloud() {
  if (!cloudGrid.value) return
  
  const q = cloudSearch.value.trim().toLowerCase()
  const tab = cloudTab.value
  const grid = cloudGrid.value
  grid.innerHTML = ''

  let items = []
  if (tab === 'videos') {
    items = materials.value.filter(m => m.type === 'video')
  } else if (tab === 'bgm') {
    // 调试：打印所有素材的类型
    console.log('[VideoLibrary] 所有素材详情:', materials.value.map(m => ({
      id: m.id,
      name: m.name,
      type: m.type,
      typeValue: typeof m.type,
      path: m.path
    })))
    items = materials.value.filter(m => {
      const type = (m.type || '').toLowerCase()
      return type === 'audio'
    })
    console.log('[VideoLibrary] BGM库筛选:', {
      totalMaterials: materials.value.length,
      audioMaterials: materials.value.filter(m => (m.type || '').toLowerCase() === 'audio'),
      filteredItems: items,
      allTypes: [...new Set(materials.value.map(m => (m.type || '').toLowerCase()))]
    })
  } else {
    items = outputs.value
  }

  if (q) {
    items = items.filter(item => {
      const name = (item.name || item.filename || '').toLowerCase()
      const path = (item.path || '').toLowerCase()
      return name.includes(q) || path.includes(q)
    })
  }

  if (!items.length) {
    let emptyMessage = '暂无数据'
    if (tab === 'bgm') {
      emptyMessage = '暂无音频素材（BGM）<br><small style="color:#8a94a3;margin-top:8px;display:block;">请点击"上传素材"按钮上传音频文件（.mp3, .wav, .flac）</small>'
    } else if (tab === 'videos') {
      emptyMessage = '暂无视频素材<br><small style="color:#8a94a3;margin-top:8px;display:block;">请点击"上传素材"按钮上传视频文件（.mp4, .avi, .mov）</small>'
    } else if (tab === 'outputs') {
      emptyMessage = '暂无成品视频<br><small style="color:#8a94a3;margin-top:8px;display:block;">完成视频剪辑后，成品会显示在这里</small>'
    }
    grid.innerHTML = `<div class="label" style="text-align:center;padding:40px 20px;color:#8a94a3;">${emptyMessage}</div>`
    return
  }

  items.forEach(item => {
    const card = document.createElement('div')
    card.className = 'card'
    
    if (tab === 'outputs') {
      card.innerHTML = renderOutputCard(item)
      bindOutputCard(card, item)
    } else {
      card.innerHTML = renderMaterialCard(item)
      bindMaterialCard(card, item)
    }
    
    grid.appendChild(card)
  })
}

function renderMaterialCard(m) {
  const isVideo = m.type === 'video'
  const badge = isVideo ? 'video' : 'audio'
  const badgeLabel = isVideo ? '视频' : '音频'
  const coverText = isVideo ? '视频素材' : 'BGM素材'
  const filename = (m.path || '').split('/').pop() || '-'
  
  return `
    <div class="card-cover">
      <span class="badge ${badge}">${badgeLabel}</span>
      ${coverText}
    </div>
    <div class="card-body">
      <div class="card-title">${escapeHtml(m.name || filename)}</div>
      <div class="card-meta">
        <div>存储：${escapeHtml(filename)}</div>
        <div>上传：${escapeHtml((m.created_at || m.create_time) ? new Date(m.created_at || m.create_time).toLocaleString() : '-')}</div>
        <div>时长：<span data-meta="duration">-</span></div>
        <div>分辨率：<span data-meta="resolution">-</span></div>
      </div>
      <div class="card-actions">
        <button class="btn btn-mini" data-action="preview">预览</button>
        <a class="btn btn-mini" data-action="download" target="_blank">下载</a>
        <button class="btn btn-mini primary" data-action="add">添加到剪辑轨道</button>
        <button class="btn btn-mini danger" data-action="delete">删除</button>
      </div>
    </div>
  `
}

function renderOutputCard(o) {
  return `
    <div class="card-cover">
      <span class="badge output">成品</span>
      成品视频
    </div>
    <div class="card-body">
      <div class="card-title">${escapeHtml(o.filename || '-')}</div>
      <div class="card-meta">
        <div>大小：${formatSize(o.size)}</div>
        <div>更新时间：${escapeHtml(o.update_time || '-')}</div>
        <div>预览：在线播放</div>
        <div></div>
      </div>
      <div class="card-actions">
        <button class="btn btn-mini" data-action="preview">预览</button>
        <button class="btn btn-mini" data-action="edit">编辑</button>
        <button class="btn btn-mini danger" data-action="delete">删除</button>
        <button class="btn btn-mini" data-action="share">分享</button>
        <a class="btn btn-mini" data-action="download" target="_blank">下载</a>
      </div>
    </div>
  `
}

function bindMaterialCard(card, m) {
  const url = toUploadsUrl(m.path)
  const downloadBtn = card.querySelector('[data-action="download"]')
  const previewBtn = card.querySelector('[data-action="preview"]')
  const addBtn = card.querySelector('[data-action="add"]')
  const deleteBtn = card.querySelector('[data-action="delete"]')

  if (downloadBtn) downloadBtn.href = url
  
  if (previewBtn) {
    previewBtn.onclick = () => {
      openModal(m.name || '预览', m.type === 'audio' ? 'audio' : 'video', url)
    }
  }

  if (addBtn) {
    addBtn.onclick = () => {
      if (m.type === 'video') {
        addVideoClip(m.id)
        showToast('已添加到剪辑轨道')
      } else {
        setBgm(m.id)
        showToast('已选择 BGM')
      }
    }
  }

  if (deleteBtn) {
    deleteBtn.onclick = async () => {
      try {
        await ElMessageBox.confirm(`确定删除素材吗？\n${m.name || m.id}`, '提示', {
          type: 'warning'
        })
        
        try {
          let response = await materialApi.deleteMaterial(m.id, m.path, false)
          if (response.code === 200) {
            showToast('删除成功')
            await bootstrapData()
          } else {
            if (response.code === 409) {
              const ok = await ElMessageBox.confirm(
                `${response.message || '该素材被任务引用，确定强制删除吗？'}\n强制删除会导致历史任务引用变为无效。`,
                '提示',
                { type: 'warning' }
              )
              if (ok) {
                response = await materialApi.deleteMaterial(m.id, m.path, true)
                if (response.code === 200) {
                  showToast('已强制删除')
                  await bootstrapData()
                }
              }
            } else {
              showToast(`删除失败：${response.message || '未知错误'}`, 'error')
            }
          }
        } catch (error) {
          showToast(`删除异常：${error.message}`, 'error')
        }
      } catch (error) {
        // 用户取消
      }
    }
  }

  // 加载元数据
  if (m.type === 'video') loadVideoMeta(m, card)
  if (m.type === 'audio') loadAudioMeta(m, card)
}

function bindOutputCard(card, o) {
  const previewBtn = card.querySelector('[data-action="preview"]')
  const downloadBtn = card.querySelector('[data-action="download"]')
  const deleteBtn = card.querySelector('[data-action="delete"]')
  const editBtn = card.querySelector('[data-action="edit"]')
  const shareBtn = card.querySelector('[data-action="share"]')

  if (previewBtn) {
    previewBtn.onclick = () => {
      openModal(o.filename || '预览', 'video', o.preview_url)
    }
  }

  if (downloadBtn) {
    downloadBtn.href = o.download_url || '#'
  }

  if (deleteBtn) {
    deleteBtn.onclick = async () => {
      try {
        await ElMessageBox.confirm(`确定删除成品视频吗？\n${o.filename}`, '提示', {
          type: 'warning'
        })
        
        const response = await materialApi.deleteOutput(o.filename)
        if (response.code === 200) {
          showToast('删除成功')
          await bootstrapData()
        } else {
          showToast(`删除失败：${response.message || '未知错误'}`, 'error')
        }
      } catch (error) {
        if (error !== 'cancel') {
          showToast(`删除异常：${error.message}`, 'error')
        }
      }
    }
  }

  if (editBtn) {
    editBtn.onclick = () => {
      setView('ai')
      showToast('已进入 AI 视频剪辑（后续可扩展：成品回填时间线）。')
    }
  }

  if (shareBtn) {
    shareBtn.onclick = async () => {
      const url = window.location.origin + (o.preview_url || '')
      try {
        await navigator.clipboard.writeText(url)
        showToast('已复制分享链接到剪贴板')
      } catch (e) {
        showToast('复制失败，请手动复制预览链接', 'error')
      }
    }
  }
}

function loadVideoMeta(m, card) {
  try {
    const url = toUploadsUrl(m.path)
    const v = document.createElement('video')
    v.preload = 'metadata'
    v.src = url
    v.onloadedmetadata = () => {
      const durationEl = card.querySelector('[data-meta="duration"]')
      const resolutionEl = card.querySelector('[data-meta="resolution"]')
      if (durationEl) durationEl.innerText = formatDuration(v.duration)
      if (resolutionEl) resolutionEl.innerText = `${v.videoWidth}x${v.videoHeight}`
    }
  } catch (e) {}
}

function loadAudioMeta(m, card) {
  try {
    const url = toUploadsUrl(m.path)
    const a = document.createElement('audio')
    a.preload = 'metadata'
    a.src = url
    a.onloadedmetadata = () => {
      const durationEl = card.querySelector('[data-meta="duration"]')
      const resolutionEl = card.querySelector('[data-meta="resolution"]')
      if (durationEl) durationEl.innerText = formatDuration(a.duration)
      if (resolutionEl) resolutionEl.innerText = '-'
    }
  } catch (e) {}
}

// 时间线操作
function addVideoClip(materialId) {
  if (!timeline.value.clips) timeline.value.clips = []
  const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
  timeline.value.clips.push({ id, materialId })
  saveTimeline()
}

function setBgm(materialId) {
  timeline.value.bgm = { materialId }
  saveTimeline()
}

function saveTimeline() {
  try {
    localStorage.setItem('ve.timeline', JSON.stringify(timeline.value))
  } catch (e) {}
}

function updateTimeline(newTimeline) {
  timeline.value = newTimeline
  saveTimeline()
}

// 上传和清空
async function handleUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return

  try {
    const fileName = file.name
    const fileExt = fileName.split('.').pop()?.toLowerCase()
    const isAudio = ['.mp3', '.wav', '.flac'].includes('.' + fileExt)
    const isVideo = ['.mp4', '.avi', '.mov'].includes('.' + fileExt)
    
    console.log('[VideoLibrary] 上传文件:', {
      fileName,
      fileExt,
      isAudio,
      isVideo,
      fileType: file.type
    })
    
    showToast('正在上传…')
    const response = await materialApi.uploadMaterial(file)
    console.log('[VideoLibrary] 上传响应:', response)
    
    if (response.code === 200) {
      const uploadedType = response.data?.type
      console.log('[VideoLibrary] 上传成功，素材类型:', uploadedType)
      showToast('上传成功，已刷新素材库')
      
      // 如果是音频文件，自动切换到 BGM 库
      if (uploadedType === 'audio') {
        setCloudTab('bgm')
      }
      
      await bootstrapData()
      
      // 确保渲染
      await nextTick()
      renderCloud()
    } else {
      showToast(`上传失败：${response.message || '未知错误'}`, 'error', 3500)
    }
  } catch (error) {
    console.error('[VideoLibrary] 上传异常:', error)
    showToast(`上传失败：${error.message}`, 'error', 3500)
  } finally {
    e.target.value = ''
  }
}

async function handleClearMaterials() {
  try {
    await ElMessageBox.confirm(
      '确定清空素材库吗？此操作将删除视频/音频素材文件与数据库记录。',
      '提示',
      { type: 'warning' }
    )
    
    const response = await materialApi.clearMaterials()
    if (response.code === 200) {
      showToast('素材库已清空')
      timeline.value = { clips: [], voice: null, bgm: null, global: { speed: 1.0 } }
      saveTimeline()
      await bootstrapData()
    } else {
      showToast(`清空失败：${response.message || '未知错误'}`, 'error', 3500)
    }
  } catch (error) {
    if (error !== 'cancel') {
      showToast(`清空失败：${error.message}`, 'error', 3500)
    }
  }
}

function handleGenerate(data) {
  // 由 VideoEditorView 组件处理
}

// 监听路由变化
watch(() => route.name, (newName) => {
  if (newName === 'VideoEditor') {
    setView('ai')
  } else if (newName === 'VideoLibrary') {
    const viewFromQuery = route.query.view
    setView(viewFromQuery === 'ai' ? 'ai' : 'cloud')
  }
}, { immediate: true })

// 初始化
onMounted(async () => {
  // 根据路由确定初始视图
  const isVideoEditorRoute = route.name === 'VideoEditor'
  const viewFromQuery = route.query.view
  
  let initialView = 'cloud'
  if (isVideoEditorRoute || viewFromQuery === 'ai') {
    initialView = 'ai'
  }
  
  const savedTab = localStorage.getItem('ve.cloudTab') || 'videos'
  
  // 恢复时间线
  try {
    const savedTimeline = localStorage.getItem('ve.timeline')
    if (savedTimeline) {
      timeline.value = JSON.parse(savedTimeline)
    }
  } catch (e) {}

  setView(initialView)
  setCloudTab(savedTab)
  await bootstrapData()
  
  // 监听键盘事件
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal()
  })
})
</script>

<style>
/* 完全复制 AI-Video 的样式 */
:root {
  --bg: #f5f7fa;
  --panel: #fff;
  --border: #e0e0e0;
  --muted: #6b7785;
  --text: #1f2d3d;
  --primary: #1677ff;
  --primaryWeak: rgba(22, 119, 255, 0.12);
  --danger: #dc3545;
  --orange: #ff7a00;
}

.video-library-container {
  --bg: #f5f7fa;
  --panel: #fff;
  --border: #e0e0e0;
  --muted: #6b7785;
  --text: #1f2d3d;
  --primary: #1677ff;
  --primaryWeak: rgba(22, 119, 255, 0.12);
  --danger: #dc3545;
  --orange: #ff7a00;
  
  width: 100%;
  min-height: calc(100vh - 60px);
  font-family: "Microsoft YaHei", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
}

.main-content {
  width: 100%;
  padding: 18px 18px 26px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.topbar-title {
  font-size: 18px;
  font-weight: 800;
  color: #2c3e50;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.btn {
  border: 1px solid var(--border);
  background: #fff;
  color: #2c3e50;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: transform 0.08s, background-color 0.16s, border-color 0.16s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  font-family: inherit;
}

.btn:hover {
  background: #f6f8fa;
  border-color: #d6d6d6;
}

.btn:active {
  transform: translateY(1px);
}

.btn.primary {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.btn.primary:hover {
  background: #0f66e2;
  border-color: #0f66e2;
}

.btn.danger {
  background: var(--danger);
  border-color: var(--danger);
  color: #fff;
}

.btn.danger:hover {
  background: #c82333;
  border-color: #c82333;
}

.view {
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 0.22s, transform 0.22s;
  display: none;
}

.view.active {
  display: block;
  opacity: 1;
  transform: translateY(0);
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.tab {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  color: #2c3e50;
  transition: background-color 0.16s, border-color 0.16s, color 0.16s;
  user-select: none;
}

.tab:hover {
  background: #f6f8fa;
}

.tab.active {
  background: var(--primaryWeak);
  border-color: rgba(22, 119, 255, 0.35);
  color: var(--primary);
  font-weight: 800;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
}

.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 12px;
  color: var(--muted);
}

.input,
.select,
.textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  outline: none;
  font-size: 13px;
  background: #fff;
  font-family: inherit;
}

.textarea {
  min-height: 92px;
  resize: vertical;
}

.input:focus,
.select:focus,
.textarea:focus {
  border-color: rgba(22, 119, 255, 0.55);
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.12);
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.card {
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  display: flex;
  flex-direction: column;
  min-height: 220px;
}

.card-cover {
  height: 120px;
  background: linear-gradient(135deg, rgba(22, 119, 255, 0.15), rgba(255, 122, 0, 0.1));
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 13px;
  position: relative;
}

.badge {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.06);
  color: #2c3e50;
}

.badge.video {
  background: rgba(22, 119, 255, 0.12);
  color: #0f66e2;
}

.badge.audio {
  background: rgba(220, 53, 69, 0.1);
  color: #c82333;
}

.badge.output {
  background: rgba(46, 204, 113, 0.12);
  color: #1e8f4d;
}

.card-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
}

.card-title {
  font-weight: 800;
  font-size: 13px;
  line-height: 1.25;
  word-break: break-word;
}

.card-meta {
  font-size: 12px;
  color: var(--muted);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
}

.card-actions {
  margin-top: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn-mini {
  padding: 7px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.toast {
  position: fixed;
  right: 16px;
  top: 16px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  font-size: 13px;
  display: none;
  z-index: 999;
  max-width: 420px;
}

.toast.show {
  display: block;
}

.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.mask.show {
  display: flex;
}

.modal {
  width: 980px;
  max-width: 100%;
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 16px 44px rgba(0, 0, 0, 0.22);
}

.modal-header {
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.modal-title {
  font-weight: 800;
  font-size: 14px;
  color: #2c3e50;
}

.modal-close {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
  color: #596979;
  padding: 0;
}

.modal-body {
  padding: 14px;
}

.media {
  width: 100%;
  height: 520px;
  background: #000;
  border-radius: 12px;
}

.audio {
  width: 100%;
}

@media (max-width: 980px) {
  .row {
    grid-template-columns: 1fr;
  }
  
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
