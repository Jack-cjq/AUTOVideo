<template>
  <div class="video-library-container">
    <!-- 主内容区 -->
    <div class="main-content">
      <div class="topbar">
        <div class="topbar-title">{{ pageTitle }}</div>
        <div class="topbar-actions" v-if="currentView === 'cloud'">
          <input 
            ref="uploadInput" 
            type="file" 
            style="display:none" 
            accept="video/*,audio/*,image/*,.mp4,.avi,.mov,.mp3,.wav,.flac,.jpg,.jpeg,.png,.gif,.webp"
            @change="handleUpload"
          />
          <button class="btn" type="button" title="上传素材（视频/音频/图片）" @click="triggerUpload">
            <span>上传素材</span>
          </button>
          <button class="btn danger" @click="handleClearMaterials" title="清空素材库（视频/音频/图片）">
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
            :class="{ active: cloudTab === 'images' }"
            @click="setCloudTab('images')"
          >
            图片素材库
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
          @preview-audio="handlePreviewAudio"
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
          <img
            v-if="modal.kind === 'image'"
            class="media media-image"
            :src="modal.url"
            alt="preview"
          />
          <div v-if="modal.kind === 'audio'" class="audio-wrapper">
            <audio 
              ref="modalAudio"
              class="audio" 
              controls
              preload="auto"
              :src="modal.url"
              @loadedmetadata="handleAudioLoaded"
              @error="handleAudioError"
              @canplay="handleAudioLoaded"
            ></audio>
            <div class="audio-hint">
              <svg class="hint-icon" viewBox="0 0 24 24" fill="none">
                <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              </svg>
              <span>音频加载完成后将自动播放，您也可以使用下方控制条手动控制播放</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import VideoEditorView from './VideoEditorView.vue'
import * as materialApi from '../api/material'
import * as editorApi from '../api/editor'
import * as aiApi from '../api/ai'
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
  if (!toast.value) {
    toast.value = { show: false, message: '' }
  }
  toast.value.show = true
  toast.value.message = message
  setTimeout(() => {
    if (toast.value) {
      toast.value.show = false
    }
  }, duration)
}

function handlePreviewAudio(url) {
  console.log('[VideoLibrary] ========== handlePreviewAudio 被调用 ==========')
  console.log('[VideoLibrary] 参数 url:', url)
  console.log('[VideoLibrary] url 类型:', typeof url)
  console.log('[VideoLibrary] url 值:', JSON.stringify(url))
  if (!url) {
    console.error('[VideoLibrary] handlePreviewAudio: url 为空')
    return
  }
  console.log('[VideoLibrary] 准备调用 openModal')
  openModal('TTS 试听', 'audio', url)
  console.log('[VideoLibrary] openModal 调用完成')
}

// 在 setup 顶层提供预览音频方法（必须在 setup 顶层，不能在 onMounted 中）
provide('previewAudio', handlePreviewAudio)

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
  
  console.log('[openModal] 打开模态框:', { title, kind, url: fullUrl })
  modal.value = { show: true, title, kind, url: fullUrl }
  console.log('[openModal] modal.value 已更新:', modal.value)
  console.log('[openModal] modal.show 值:', modal.value.show)
  
  // 对于音频，等待模态框渲染完成后尝试自动播放
  if (kind === 'audio') {
    console.log('[openModal] 开始处理音频模态框，等待渲染...')
    // 使用 nextTick 确保模态框已经渲染，audio 元素已经存在
    nextTick(() => {
      console.log('[openModal] nextTick 回调执行，检查 audio 元素...')
      // 再等待一下确保 audio 元素完全渲染
      setTimeout(() => {
        if (modalAudio.value) {
          const audio = modalAudio.value
          console.log('[openModal] 音频元素已找到，设置源:', fullUrl)
          
          // 清除之前的事件监听器
          audio.onerror = null
          audio.onloadeddata = null
          audio.oncanplay = null
          audio.onloadedmetadata = null
          
          // 明确设置音频源（即使模板中已经绑定了 :src，这里也设置一次确保生效）
          audio.src = fullUrl
          
          // 设置音量（确保不是静音）
          audio.volume = 1.0
          audio.muted = false
          
          // 添加错误处理
          audio.onerror = (e) => {
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
          
          // 当音频可以播放时，尝试自动播放
          audio.oncanplay = () => {
            console.log('[openModal] 音频可以播放')
            audio.volume = 1.0
            audio.muted = false
            // 尝试自动播放（在用户交互上下文中）
            audio.play().then(() => {
              console.log('[openModal] 音频自动播放成功')
            }).catch((err) => {
              // 自动播放被阻止是正常的浏览器行为，不显示错误
              console.log('[openModal] 自动播放被阻止，用户可以手动点击播放按钮:', err)
            })
          }
          
          // 当元数据加载完成时也尝试播放
          audio.onloadedmetadata = () => {
            console.log('[openModal] 音频元数据加载完成')
            audio.volume = 1.0
            audio.muted = false
            if (audio.readyState >= 2) {
              audio.play().then(() => {
                console.log('[openModal] 音频元数据加载后播放成功')
              }).catch(() => {
                // 自动播放被阻止是正常的
                console.log('[openModal] 音频元数据加载后播放被阻止')
              })
            }
          }
          
          // 当数据加载完成时也尝试播放
          audio.onloadeddata = () => {
            console.log('[openModal] 音频数据加载完成')
            audio.volume = 1.0
            audio.muted = false
            if (audio.readyState >= 2) {
              audio.play().then(() => {
                console.log('[openModal] 音频数据加载后播放成功')
              }).catch(() => {
                // 自动播放被阻止是正常的
                console.log('[openModal] 音频数据加载后播放被阻止')
              })
            }
          }
          
          // 强制加载音频
          console.log('[openModal] 开始加载音频')
          audio.load()
        } else {
          console.warn('[openModal] 音频元素未找到！modalAudio.value:', modalAudio.value)
        }
      }, 150)
    })
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
        showToast('视频加载失败，请检查文件是否存在', 'error')
      }
      video.onloadeddata = () => {
        // 视频加载成功
      }
      video.oncanplay = () => {
        // 视频可以播放
      }
      
      video.load()
    }
    // 注意：音频处理已经在上面提前返回了，这里不再处理
  })
}

async function closeModal() {
  // 如果是临时TTS文件（路径包含 /tts/），关闭时删除
  const currentUrl = modal.value.url
  if (modal.value.kind === 'audio' && currentUrl && currentUrl.includes('/tts/')) {
    try {
      await aiApi.deleteTempTts(currentUrl)
      // 静默删除，不显示成功消息（避免干扰用户体验）
    } catch (error) {
      // 删除失败也不影响关闭模态框，只记录错误
      console.warn('删除临时TTS文件失败:', error)
    }
  }
  
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
    modalAudio.value.oncanplay = null
    modalAudio.value.onloadedmetadata = null
  }
  modal.value = { show: false, title: '', kind: '', url: '' }
}

function handleAudioLoaded() {
  // 音频元数据加载完成，尝试自动播放
  if (modalAudio.value) {
    modalAudio.value.volume = 1.0
    modalAudio.value.muted = false
    // 尝试自动播放（在用户交互上下文中）
    modalAudio.value.play().catch(() => {
      // 自动播放被阻止是正常的浏览器行为，用户可以手动点击播放
    })
  }
}

function handleAudioError(e) {
  showToast('音频加载失败，请检查网络连接或音频文件', 'error')
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
    }
  } catch (error) {
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
  } else if (tab === 'images') {
    items = materials.value.filter(m => {
      const type = (m.type || '').toLowerCase()
      return type === 'image'
    })
  } else if (tab === 'bgm') {
    items = materials.value.filter(m => {
      const type = (m.type || '').toLowerCase()
      return type === 'audio'
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
    } else if (tab === 'images') {
      emptyMessage = '暂无图片素材<br><small style="color:#8a94a3;margin-top:8px;display:block;">请点击"上传素材"按钮上传图片文件（.jpg, .jpeg, .png, .gif, .webp）</small>'
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
  const type = (m.type || '').toLowerCase()
  const isVideo = type === 'video'
  const isAudio = type === 'audio'
  const isImage = type === 'image'
  const badge = isVideo ? 'video' : isImage ? 'image' : 'audio'
  const badgeLabel = isVideo ? '视频' : isImage ? '图片' : '音频'
  const filename = (m.path || '').split('/').pop() || '-'
  const mediaUrl = toUploadsUrl(m.path)
  const showAdd = isVideo || isImage
  
  // 如果是视频，使用 video 元素显示缩略图；如果是图片，显示 img；如果是音频，显示占位图标
  let coverHtml = ''
  if (isVideo && mediaUrl) {
    coverHtml = `
      <video 
        class="card-video-thumbnail" 
        preload="metadata" 
        muted
        data-video-url="${escapeHtml(mediaUrl)}"
      >
        <source src="${escapeHtml(mediaUrl)}" type="video/mp4">
      </video>
      <div class="card-cover-overlay">
        <span class="badge ${badge}">${badgeLabel}</span>
      </div>
    `
  } else if (isImage && mediaUrl) {
    coverHtml = `
      <img
        class="card-image-thumbnail"
        src="${escapeHtml(mediaUrl)}"
        alt="${escapeHtml(m.name || filename)}"
        loading="lazy"
      />
      <div class="card-cover-overlay">
        <span class="badge ${badge}">${badgeLabel}</span>
      </div>
    `
  } else {
    coverHtml = `
      <div class="card-cover-placeholder">
        <svg class="placeholder-icon" viewBox="0 0 24 24" fill="none">
          <path d="M11 5L6 9H2v6h4l5 4V5zM19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="badge ${badge}">${badgeLabel}</span>
      </div>
    `
  }
  
  return `
    <div class="card-cover">
      ${coverHtml}
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
        ${showAdd ? `<button class="btn btn-mini primary" data-action="add">添加到剪辑轨道</button>` : ''}
        ${isAudio ? `<button class="btn btn-mini primary" data-action="set-voice">设为配音</button>` : ''}
        ${isAudio ? `<button class="btn btn-mini primary" data-action="set-bgm">设为BGM</button>` : ''}
        <button class="btn btn-mini danger" data-action="delete">删除</button>
      </div>
    </div>
  `
}

function renderOutputCard(o) {
  const videoUrl = o.preview_url || o.video_url || ''
  // 处理URL：如果是相对路径，转换为完整URL
  const fullVideoUrl = videoUrl ? (videoUrl.startsWith('http') ? videoUrl : toUploadsUrl(videoUrl)) : ''
  
  // 使用 video 元素显示视频画面帧
  let coverHtml = ''
  if (fullVideoUrl) {
    coverHtml = `
      <video 
        class="card-video-thumbnail" 
        preload="metadata" 
        muted
        data-video-url="${escapeHtml(fullVideoUrl)}"
      >
        <source src="${escapeHtml(fullVideoUrl)}" type="video/mp4">
      </video>
      <div class="card-cover-overlay">
        <span class="badge output">成品</span>
      </div>
    `
  } else {
    coverHtml = `
      <div class="card-cover-placeholder">
        <svg class="placeholder-icon" viewBox="0 0 24 24" fill="none">
          <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="badge output">成品</span>
      </div>
    `
  }
  
  return `
    <div class="card-cover">
      ${coverHtml}
    </div>
    <div class="card-body">
      <div class="card-title">${escapeHtml(o.video_name || o.filename || '-')}</div>
      <div class="card-meta">
        <div>大小：${formatSize(o.size || 0)}</div>
        <div>更新时间：${escapeHtml(o.update_time || '-')}</div>
        <div>时长：<span data-meta="duration">-</span></div>
        <div>分辨率：<span data-meta="resolution">-</span></div>
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
  const setVoiceBtn = card.querySelector('[data-action="set-voice"]')
  const setBgmBtn = card.querySelector('[data-action="set-bgm"]')
  const deleteBtn = card.querySelector('[data-action="delete"]')
  const videoThumbnail = card.querySelector('.card-video-thumbnail')

  if (downloadBtn) downloadBtn.href = url
  
  if (previewBtn) {
    previewBtn.onclick = () => {
      const t = (m.type || '').toLowerCase()
      const kind = t === 'audio' ? 'audio' : t === 'image' ? 'image' : 'video'
      openModal(m.name || '预览', kind, url)
    }
  }
  
  // 处理视频缩略图
  if (videoThumbnail && m.type === 'video') {
    // 设置视频当前时间为第一秒，以显示画面帧
    videoThumbnail.currentTime = 0.1
    // 加载视频元数据以获取时长和分辨率
    videoThumbnail.addEventListener('loadedmetadata', () => {
      const duration = videoThumbnail.duration
      const videoWidth = videoThumbnail.videoWidth
      const videoHeight = videoThumbnail.videoHeight
      
      // 更新时长显示
      const durationSpan = card.querySelector('[data-meta="duration"]')
      if (durationSpan && !isNaN(duration)) {
        const minutes = Math.floor(duration / 60)
        const seconds = Math.floor(duration % 60)
        durationSpan.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`
      }
      
      // 更新分辨率显示
      const resolutionSpan = card.querySelector('[data-meta="resolution"]')
      if (resolutionSpan && videoWidth && videoHeight) {
        resolutionSpan.textContent = `${videoWidth}x${videoHeight}`
      }
    }, { once: true })
    
    // 处理视频加载错误
    videoThumbnail.addEventListener('error', () => {
      console.warn('视频缩略图加载失败:', url)
      // 如果加载失败，可以显示占位符
      const cover = card.querySelector('.card-cover')
      if (cover) {
        cover.innerHTML = `
          <div class="card-cover-placeholder">
            <svg class="placeholder-icon" viewBox="0 0 24 24" fill="none">
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="badge video">视频</span>
          </div>
        `
      }
    }, { once: true })
  }

  if (addBtn) {
    addBtn.onclick = () => {
      if (m.type === 'video') {
        addVideoClip(m.id)
        showToast('已添加到剪辑轨道')
      } else if (m.type === 'image') {
        addImageClip(m.id)
        showToast('已添加到剪辑轨道')
      }
    }
  }

  if (setVoiceBtn) {
    setVoiceBtn.onclick = () => {
      setVoice(m.id)
      showToast('已设置为配音')
    }
  }

  if (setBgmBtn) {
    setBgmBtn.onclick = () => {
      setBgm(m.id)
      showToast('已选择 BGM')
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
  if (m.type === 'image') loadImageMeta(m, card)
}

function bindOutputCard(card, o) {
  const previewBtn = card.querySelector('[data-action="preview"]')
  const downloadBtn = card.querySelector('[data-action="download"]')
  const deleteBtn = card.querySelector('[data-action="delete"]')
  const editBtn = card.querySelector('[data-action="edit"]')
  const shareBtn = card.querySelector('[data-action="share"]')
  const videoThumbnail = card.querySelector('.card-video-thumbnail')
  
  // 处理视频URL
  const videoUrl = o.preview_url || o.video_url || ''
  const fullVideoUrl = videoUrl ? (videoUrl.startsWith('http') ? videoUrl : toUploadsUrl(videoUrl)) : ''

  if (previewBtn) {
    previewBtn.onclick = () => {
      if (!fullVideoUrl) {
        showToast('缺少预览链接', 'error')
        return
      }
      openModal(o.video_name || o.filename || '预览', 'video', fullVideoUrl)
    }
  }

  if (downloadBtn) {
    downloadBtn.href = o.download_url || fullVideoUrl || '#'
  }
  
  // 处理视频缩略图
  if (videoThumbnail && fullVideoUrl) {
    // 设置视频当前时间为第一秒，以显示画面帧
    videoThumbnail.currentTime = 0.1
    // 加载视频元数据以获取时长和分辨率
    videoThumbnail.addEventListener('loadedmetadata', () => {
      const duration = videoThumbnail.duration
      const videoWidth = videoThumbnail.videoWidth
      const videoHeight = videoThumbnail.videoHeight
      
      // 更新时长显示
      const durationSpan = card.querySelector('[data-meta="duration"]')
      if (durationSpan && !isNaN(duration)) {
        const minutes = Math.floor(duration / 60)
        const seconds = Math.floor(duration % 60)
        durationSpan.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`
      }
      
      // 更新分辨率显示
      const resolutionSpan = card.querySelector('[data-meta="resolution"]')
      if (resolutionSpan && videoWidth && videoHeight) {
        resolutionSpan.textContent = `${videoWidth}x${videoHeight}`
      }
    }, { once: true })
    
    // 处理视频加载错误
    videoThumbnail.addEventListener('error', () => {
      console.warn('成品视频缩略图加载失败:', fullVideoUrl)
      // 如果加载失败，显示占位符
      const cover = card.querySelector('.card-cover')
      if (cover) {
        cover.innerHTML = `
          <div class="card-cover-placeholder">
            <svg class="placeholder-icon" viewBox="0 0 24 24" fill="none">
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="badge output">成品</span>
          </div>
        `
      }
    }, { once: true })
  }

  if (deleteBtn) {
    deleteBtn.onclick = async () => {
      try {
        await ElMessageBox.confirm(`确定删除成品视频吗？\n${o.filename}`, '提示', {
          type: 'warning'
        })
        
        const response = await materialApi.deleteOutput(o.filename, o.cos_key)
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
      const rawUrl = o.preview_url || o.video_url || ''
      if (!rawUrl) {
        showToast('缺少预览链接', 'error')
        return
      }

      let url = rawUrl
      if (!rawUrl.startsWith('http')) {
        const normalized = rawUrl.startsWith('/') ? rawUrl : toUploadsUrl(rawUrl)
        url = window.location.origin + normalized
      }
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

function loadImageMeta(m, card) {
  try {
    const url = toUploadsUrl(m.path)
    const img = new Image()
    img.onload = () => {
      const durationEl = card.querySelector('[data-meta="duration"]')
      const resolutionEl = card.querySelector('[data-meta="resolution"]')
      if (durationEl) durationEl.innerText = '-'
      if (resolutionEl) resolutionEl.innerText = `${img.naturalWidth}x${img.naturalHeight}`
    }
    img.src = url
  } catch (e) {}
}

// 时间线操作
function addVideoClip(materialId) {
  if (!timeline.value.clips) timeline.value.clips = []
  const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
  timeline.value.clips.push({ id, type: 'video', materialId })
  saveTimeline()
}

function addImageClip(materialId, duration = 2.0) {
  if (!timeline.value.clips) timeline.value.clips = []
  const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
  timeline.value.clips.push({ id, type: 'image', materialId, duration })
  saveTimeline()
}

function setBgm(materialId) {
  timeline.value.bgm = { materialId }
  saveTimeline()
}

function setVoice(materialId) {
  timeline.value.voice = { materialId }
  saveTimeline()
}

function saveTimeline() {
  try {
    localStorage.setItem('ve.timeline', JSON.stringify(timeline.value))
  } catch (e) {}
}

function updateTimeline(newTimeline) {
  console.log('[VideoLibrary] updateTimeline 被调用，newTimeline:', newTimeline)
  console.log('[VideoLibrary] newTimeline.voice:', newTimeline?.voice)
  timeline.value = newTimeline
  saveTimeline()
  console.log('[VideoLibrary] timeline.value 已更新:', timeline.value)
  console.log('[VideoLibrary] timeline.value.voice:', timeline.value?.voice)
}

// 上传和清空
async function handleUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return

  try {
    console.log('[VideoLibrary] handleUpload:', { name: file.name, size: file.size, type: file.type })
    const fileName = file.name
    const fileExt = fileName.split('.').pop()?.toLowerCase()
    const isAudio = ['.mp3', '.wav', '.flac'].includes('.' + fileExt)
    const isVideo = ['.mp4', '.avi', '.mov'].includes('.' + fileExt)
    const isImage = ['.jpg', '.jpeg', '.png', '.gif', '.webp'].includes('.' + fileExt)
    
    showToast('正在上传…')
    const response = await materialApi.uploadMaterial(file)
    
    if (response.code === 200) {
      const uploadedType = response.data?.type
      showToast('上传成功，已刷新素材库')
      
      // 如果是音频文件，自动切换到 BGM 库
      if (uploadedType === 'audio') {
        setCloudTab('bgm')
      } else if (uploadedType === 'image') {
        setCloudTab('images')
      } else if (uploadedType === 'video') {
        setCloudTab('videos')
      }
      
      await bootstrapData()
      
      // 确保渲染
      await nextTick()
      renderCloud()
    } else {
      showToast(`上传失败：${response.message || '未知错误'}`, 'error', 3500)
    }
  } catch (error) {
    showToast(`上传失败：${error.message}`, 'error', 3500)
  } finally {
    e.target.value = ''
  }
}

function triggerUpload() {
  const input = uploadInput.value
  if (!input) return
  input.click()
}

async function handleClearMaterials() {
  try {
    await ElMessageBox.confirm(
      '确定清空素材库吗？此操作将删除视频/音频/图片素材文件与数据库记录。',
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
  position: relative;
  overflow: hidden;
}

.card-video-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #000;
}

.card-image-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: #000;
}

.card-cover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 8px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, transparent 30%);
  pointer-events: none;
}

.card-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #8a94a3;
  font-weight: 800;
  font-size: 13px;
  position: relative;
}

.placeholder-icon {
  width: 48px;
  height: 48px;
  opacity: 0.5;
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

.badge.image {
  background: rgba(155, 89, 182, 0.12);
  color: #7d3c98;
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

.media-image {
  object-fit: contain;
}

.audio-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.audio {
  width: 100%;
  min-height: 80px;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  box-sizing: border-box;
  outline: none;
}

/* 确保音频控制条清晰可见 */
.audio::-webkit-media-controls-panel {
  background-color: #fff;
  border-radius: 6px;
  padding: 8px;
}

.audio::-webkit-media-controls-play-button {
  background-color: #1677ff;
  border-radius: 50%;
  width: 40px;
  height: 40px;
}

.audio::-webkit-media-controls-current-time-display,
.audio::-webkit-media-controls-time-remaining-display {
  color: #2c3e50;
  font-size: 14px;
  font-weight: 500;
}

.audio::-webkit-media-controls-timeline {
  background-color: #e0e0e0;
  border-radius: 2px;
  height: 6px;
  margin: 0 12px;
}

.audio::-webkit-media-controls-timeline::-webkit-slider-thumb {
  background-color: #1677ff;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.audio::-webkit-media-controls-volume-slider {
  background-color: #e0e0e0;
  border-radius: 2px;
  height: 4px;
}

.audio::-webkit-media-controls-volume-slider::-webkit-slider-thumb {
  background-color: #1677ff;
  border-radius: 50%;
  width: 12px;
  height: 12px;
}

.audio-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f0f7ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  font-size: 13px;
  color: #1677ff;
}

.hint-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
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
