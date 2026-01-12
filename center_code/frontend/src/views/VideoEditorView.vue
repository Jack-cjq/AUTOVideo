<template>
  <div class="video-editor-view">
    <div class="tabs" style="max-width:980px;margin:0 auto 14px;">
      <div 
        class="tab" 
        :class="{ active: aiTab === 'copy' }"
        @click="setAiTab('copy')"
      >
        文案
      </div>
      <div 
        class="tab" 
        :class="{ active: aiTab === 'tts' }"
        @click="setAiTab('tts')"
      >
        配音
      </div>
      <div 
        class="tab" 
        :class="{ active: aiTab === 'edit' }"
        @click="setAiTab('edit')"
      >
        剪辑生成
      </div>
    </div>

    <!-- 文案步骤 -->
    <div class="aiStep" :class="{ active: aiTab === 'copy' }" v-if="aiTab === 'copy'">
      <div class="panel" style="max-width:980px;margin:0 auto;">
        <div class="row">
          <div class="field">
            <div class="label">AI文案生成：主题</div>
            <input 
              v-model="copyForm.theme" 
              class="input" 
              placeholder="例如：冬日城市漫游 / 美食探店 / 旅行Vlog"
            />
          </div>
          <div class="field">
            <div class="label">关键词（可选）</div>
            <input 
              v-model="copyForm.keywords" 
              class="input" 
              placeholder="例如：温暖、治愈、街景、镜头感…"
            />
          </div>
          <div class="field">
            <div class="label">生成数量（1~10）</div>
            <input 
              v-model.number="copyForm.count" 
              class="input" 
              type="number"
              min="1"
              max="10"
            />
          </div>
        </div>
        <div class="field" style="margin-top:10px;">
          <div class="label">参考文案（可选）</div>
          <textarea 
            v-model="copyForm.reference" 
            class="textarea" 
            placeholder="粘贴一段参考文案（当前为本地模板生成演示）。"
          ></textarea>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">
          <button 
            class="btn primary" 
            :class="{ loading: copyLoading }"
            @click="handleCopyGenerate"
          >
            <span class="spinner"></span>
            <span>生成</span>
          </button>
          <button class="btn" @click="handleCopyClear">
            <span>清空</span>
          </button>
          <button class="btn" @click="handleCopyCopy">
            <span>复制</span>
          </button>
        </div>
        <div class="row" v-if="copyOptions.length > 0" style="margin-top:10px;">
          <div class="field">
            <div class="label">选择文案版本</div>
            <select v-model="selectedCopyIndex" class="select" @change="applyCopyOption">
              <option 
                v-for="(opt, idx) in copyOptions" 
                :key="idx" 
                :value="idx"
              >
                {{ opt.title }}
              </option>
            </select>
          </div>
        </div>
        <div class="field" style="margin-top:10px;">
          <div class="label">文案预览/编辑</div>
          <textarea 
            v-model="copyForm.output" 
            class="textarea" 
            placeholder="生成的文案会出现在这里，你也可以直接编辑。"
          ></textarea>
        </div>
      </div>
    </div>

    <!-- 配音步骤 -->
    <div class="aiStep" :class="{ active: aiTab === 'tts' }" v-if="aiTab === 'tts'">
      <div class="panel" style="max-width:980px;margin:14px auto 0;">
        <div class="row">
          <div class="field">
            <div class="label">音色选择</div>
            <select v-model="ttsForm.voice" class="select">
              <option 
                v-for="voice in ttsVoices" 
                :key="voice.id" 
                :value="voice.id"
              >
                {{ voice.name }}
              </option>
            </select>
          </div>
          <div class="field">
            <div class="label">自定义音色上传（演示）</div>
            <input 
              class="input" 
              type="file" 
              accept="audio/*"
              @change="handleVoiceUpload"
            />
          </div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">
          <button class="btn" @click="handleVoicePreview">
            <span>试听</span>
          </button>
          <button 
            class="btn primary" 
            :class="{ loading: ttsLoading }"
            @click="handleVoiceSave"
          >
            <span class="spinner"></span>
            <span>生成并加入素材库</span>
          </button>
        </div>
        <div class="label" style="margin-top:8px;">
          说明：试听仅用于预览；"生成并加入素材库"会把音频写入音频素材库并自动设为配音轨。
        </div>
      </div>
    </div>

    <!-- 剪辑生成步骤 -->
    <div class="aiStep" :class="{ active: aiTab === 'edit' }" v-if="aiTab === 'edit'">
      <div class="panel" style="max-width:980px;margin:14px auto 0;">
        <div class="row">
          <div class="field">
            <div class="label">视频素材选择（来自云素材库/本地上传）</div>
            <div class="chip-list" ref="selectedVideos"></div>
            <div class="label" style="margin-top:8px;">
              小提示：去"云素材库 → 视频素材库"点"添加到剪辑轨道"。
            </div>
          </div>
          <div class="field">
            <div class="label">本地上传视频并添加</div>
            <input 
              class="input" 
              type="file" 
              accept=".mp4,.avi,.mov"
              @change="handleAiVideoUpload"
            />
            <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;">
              <button class="btn" @click="handleAiGen">
                <span>AI生成（占位）</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="panel" style="max-width:980px;margin:14px auto 0;">
        <div class="row">
          <div class="field">
            <div class="label">配音（来自 TTS / 音频素材库）</div>
            <div class="chip-list" ref="selectedVoice"></div>
            <div class="label" style="margin-top:8px;">
              提示：在"配音"模块点"生成并加入素材库"会自动设为配音轨。
            </div>

            <div class="label" style="margin-top:12px;">BGM库选择（来自云素材库）</div>
            <div class="chip-list" ref="selectedBgm"></div>
            <div class="label" style="margin-top:8px;">
              去"云素材库 → BGM库"点"添加到剪辑轨道"。
            </div>
          </div>
          <div class="field">
            <div class="label">BGM设置（演示）</div>
            <div class="row">
              <div class="field">
                <div class="label">音量</div>
                <input 
                  v-model.number="editForm.bgmVolume" 
                  class="input" 
                  type="range" 
                  min="0" 
                  max="100"
                />
              </div>
              <div class="field">
                <div class="label">循环</div>
                <select v-model="editForm.bgmLoop" class="select">
                  <option value="auto">按视频长度截断</option>
                  <option value="loop">循环（后端未实现）</option>
                </select>
              </div>
            </div>
            <div class="label">说明：当前后端剪辑仅支持"添加/不添加 BGM"。</div>
          </div>
        </div>
      </div>

      <div class="panel" style="max-width:980px;margin:14px auto 0;">
        <div class="row">
          <div class="field">
            <div class="label">输出设置（演示）</div>
            <div class="row">
              <div class="field">
                <div class="label">分辨率</div>
                <select v-model="editForm.resolution" class="select">
                  <option value="auto">自动</option>
                  <option value="1080p">1080p</option>
                  <option value="720p">720p</option>
                </select>
              </div>
              <div class="field">
                <div class="label">视频比例</div>
                <select v-model="editForm.ratio" class="select">
                  <option value="auto">自动</option>
                  <option value="16:9">16:9</option>
                  <option value="9:16">9:16</option>
                  <option value="1:1">1:1</option>
                </select>
              </div>
            </div>
          </div>
          <div class="field">
            <div class="label">播放速度</div>
            <select v-model.number="editForm.speed" class="select">
              <option :value="1">1.0x</option>
              <option :value="0.75">0.75x</option>
              <option :value="1.25">1.25x</option>
              <option :value="1.5">1.5x</option>
              <option :value="2">2.0x</option>
            </select>
            <div class="label">说明：后端支持 0.5~2.0。</div>
          </div>
        </div>
        <div class="row" style="margin-top:10px;">
          <div class="field">
            <div class="label">字幕（跟配音同步）</div>
            <label style="display:flex;align-items:center;gap:8px;">
              <input 
                v-model="editForm.subtitleEnabled" 
                type="checkbox"
              />
              <span style="font-size:13px;color:#2c3e50;">
                生成并烧录字幕（需要已选择配音音频作为 BGM）
              </span>
            </label>
          </div>
          <div class="field" style="display:flex;align-items:flex-end;gap:10px;">
            <button class="btn" @click="handleSubPreview" type="button">
              生成字幕预览
            </button>
            <a 
              v-if="subtitleUrl" 
              class="btn" 
              :href="subtitleUrl" 
              target="_blank"
            >
              下载SRT
            </a>
          </div>
        </div>
        <div style="display:flex;justify-content:center;margin-top:14px;">
          <button 
            class="btn orange" 
            :class="{ loading: generateLoading }"
            @click="handleGenerate"
          >
            <span class="spinner"></span>
            <span>一键生成AI剪辑视频</span>
          </button>
        </div>
        <div class="progress" :class="{ show: progress.show }">
          <div class="bar" :style="{ width: `${progress.value}%` }"></div>
        </div>
        <div class="label" v-if="progress.text" style="margin-top:8px;">
          {{ progress.text }}
        </div>
      </div>

      <div class="panel" style="max-width:980px;margin:14px auto 0;">
        <div class="label" style="margin-bottom:8px;">视频预览区（生成中/已生成）</div>
        <video 
          ref="previewVideo"
          class="preview-video" 
          controls
          v-if="previewUrl"
        >
          <source :src="previewUrl" type="video/mp4" />
          您的浏览器不支持HTML5视频播放，请更换浏览器后重试
        </video>
        <div v-else class="preview-video" style="display:flex;align-items:center;justify-content:center;color:#999;">
          暂无预览视频
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">
          <a 
            v-if="exportUrl" 
            class="btn" 
            :href="exportUrl" 
            target="_blank"
          >
            导出/下载
          </a>
          <button 
            v-if="previewUrl" 
            class="btn" 
            @click="handleFullscreen"
          >
            全屏
          </button>
          <button class="btn" @click="$emit('open-outputs')">
            查看成品库
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as aiApi from '../api/ai'
import * as editorApi from '../api/editor'
import * as materialApi from '../api/material'

const props = defineProps({
  materials: {
    type: Array,
    default: () => []
  },
  timeline: {
    type: Object,
    default: () => ({ clips: [], voice: null, bgm: null, global: { speed: 1.0 } })
  }
})

const emit = defineEmits(['update-timeline', 'generate', 'open-outputs', 'refresh-materials', 'preview-audio'])

// 状态
const aiTab = ref('copy')
const copyLoading = ref(false)
const ttsLoading = ref(false)
const generateLoading = ref(false)

// 文案表单
const copyForm = ref({
  theme: '',
  keywords: '',
  reference: '',
  count: 6,
  output: ''
})

const copyOptions = ref([])
const selectedCopyIndex = ref(0)

// TTS 表单
const ttsVoices = ref([
  { id: 0, name: '标准女声' },
  { id: 1, name: '标准男声' },
  { id: 3, name: '度逍遥（情感男声）' },
  { id: 4, name: '度丫丫（童声）' }
])

const ttsForm = ref({
  voice: 0
})

// 剪辑表单
const editForm = ref({
  bgmVolume: 60,
  bgmLoop: 'auto',
  resolution: 'auto',
  ratio: 'auto',
  speed: 1.0,
  subtitleEnabled: false
})

// 预览和进度
const previewUrl = ref('')
const exportUrl = ref('')
const subtitleUrl = ref('')
const progress = ref({ show: false, value: 0, text: '' })

// DOM 引用
const selectedVideos = ref(null)
const selectedVoice = ref(null)
const selectedBgm = ref(null)
const previewVideo = ref(null)

// 工具函数
function materialNameById(materialId) {
  const m = props.materials.find(x => x.id === materialId)
  return m ? (m.name || `素材(${materialId})`) : `素材(${materialId})`
}

function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function getTtsText(maxLength = 500) {
  const text = copyForm.value.output || ''
  return text.slice(0, maxLength)
}

// 文案生成
async function handleCopyGenerate() {
  if (!copyForm.value.theme.trim()) {
    alert('请输入主题')
    return
  }

  copyLoading.value = true
  try {
    const response = await aiApi.generateCopy({
      theme: copyForm.value.theme,
      keywords: copyForm.value.keywords,
      reference: copyForm.value.reference,
      count: copyForm.value.count
    })

    if (response.code === 200) {
      const copies = response.data?.copies || []
      if (copies.length > 0) {
        copyOptions.value = copies.map((c, i) => ({
          title: c.title || `文案 ${i + 1}`,
          text: Array.isArray(c.lines) ? c.lines.join('\n') : ''
        }))
        selectedCopyIndex.value = 0
        applyCopyOption()
        alert('已生成文案（DeepSeek）')
      } else {
        alert('AI 返回空结果')
      }
    } else {
      alert(`生成失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    alert(`生成失败：${error.message}`)
  } finally {
    copyLoading.value = false
  }
}

function applyCopyOption() {
  if (copyOptions.value.length > 0 && selectedCopyIndex.value >= 0) {
    copyForm.value.output = copyOptions.value[selectedCopyIndex.value]?.text || ''
  }
}

function handleCopyClear() {
  copyForm.value = {
    theme: '',
    keywords: '',
    reference: '',
    count: 6,
    output: ''
  }
  copyOptions.value = []
  selectedCopyIndex.value = 0
  alert('已清空')
}

async function handleCopyCopy() {
  try {
    await navigator.clipboard.writeText(copyForm.value.output || '')
    alert('已复制到剪贴板')
  } catch (e) {
    alert('复制失败，请手动选择复制')
  }
}

// TTS 配音
async function handleVoicePreview() {
  const text = getTtsText(500)
  if (!text) {
    alert('请先生成/填写文案（用于试听）')
    return
  }

  try {
    alert('试听中…')
    const response = await aiApi.synthesizeTts({
      text,
      voice: ttsForm.value.voice,
      speed: 5,
      pitch: 5,
      volume: 6,
      persist: false
    })

    if (response.code === 200) {
      const url = response.data?.preview_url
      if (url) {
        // 打开预览模态框（由父组件处理）
        // 注意：由于用户已经点击了试听按钮，此时在用户交互上下文中，可以触发自动播放
        emit('preview-audio', url)
      } else {
        alert('缺少 preview_url')
      }
    } else {
      alert(`TTS失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    alert(`TTS失败：${error.message}`)
  }
}

async function handleVoiceSave() {
  const text = getTtsText(500)
  if (!text) {
    alert('请先生成/填写文案（用于配音）')
    return
  }

  ttsLoading.value = true
  try {
    const response = await aiApi.synthesizeTts({
      text,
      voice: ttsForm.value.voice,
      speed: 5,
      pitch: 5,
      volume: 6,
      persist: true
    })

    if (response.code === 200) {
      const materialId = response.data?.material_id
      if (materialId) {
        // 更新时间线
        const newTimeline = { ...props.timeline }
        newTimeline.voice = { materialId: Number(materialId) }
        emit('update-timeline', newTimeline)
        alert('已生成并加入素材库，已设为配音')
        // 刷新素材列表（由父组件处理）
        emit('refresh-materials')
      } else {
        alert('入库失败（未返回 material_id）')
      }
    } else {
      alert(`生成失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    alert(`生成失败：${error.message}`)
  } finally {
    ttsLoading.value = false
  }
}

function handleVoiceUpload(e) {
  // 占位功能
  alert('自定义音色上传功能待实现')
}

// 剪辑生成
async function handleAiVideoUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return

  try {
    alert('正在上传并添加到剪辑轨道…')
    const response = await materialApi.uploadMaterial(file)
    if (response.code === 200) {
      const materialId = response.data?.material_id
      if (materialId) {
        // 添加到时间线
        const newTimeline = { ...props.timeline }
        if (!newTimeline.clips) newTimeline.clips = []
        const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
        newTimeline.clips.push({ id, materialId: Number(materialId) })
        emit('update-timeline', newTimeline)
        alert('上传成功，已加入剪辑轨道')
        emit('refresh-materials')
      }
    } else {
      alert(`上传失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    alert(`上传失败：${error.message}`)
  } finally {
    e.target.value = ''
  }
}

function handleAiGen() {
  alert('AI生成（占位）：后续可接入生成式视频/检索素材。')
}

async function handleSubPreview() {
  const voiceId = props.timeline?.voice?.materialId
  if (!voiceId) {
    alert('请先生成配音并设为配音轨（用于取时长）')
    return
  }

  const text = getTtsText(500)
  if (!text) {
    alert('请先生成/填写文案（用于字幕）')
    return
  }

  try {
    const response = await aiApi.generateSubtitle({
      text,
      audio_material_id: voiceId
    })

    if (response.code === 200) {
      const url = response.data?.preview_url
      if (url) {
        subtitleUrl.value = url
        alert('字幕已生成，可点击下载SRT')
      } else {
        alert('缺少字幕预览链接')
      }
    } else {
      alert(`字幕生成失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    alert(`字幕生成失败：${error.message}`)
  }
}

async function handleGenerate() {
  const clips = props.timeline?.clips || []
  if (clips.length === 0) {
    alert('请至少选择一个视频素材')
    return
  }

  generateLoading.value = true
  progress.value = { show: true, value: 0, text: '正在创建任务…' }

  try {
    const videoIds = clips.map(c => c.materialId)
    const voiceId = props.timeline?.voice?.materialId || null
    const bgmId = props.timeline?.bgm?.materialId || null
    const speed = editForm.value.speed || 1.0
    const subtitlePath = editForm.value.subtitleEnabled && subtitleUrl.value ? subtitleUrl.value : null

    const response = await editorApi.editVideoAsync({
      video_ids: videoIds,
      voice_id: voiceId,
      bgm_id: bgmId,
      speed,
      subtitle_path: subtitlePath
    })

    if (response.code === 200) {
      const taskId = response.data?.task_id
      if (taskId) {
        progress.value = { show: true, value: 10, text: '任务已创建，正在处理…' }
        // 轮询任务状态
        pollTaskStatus(taskId)
      } else {
        throw new Error('未返回 task_id')
      }
    } else {
      throw new Error(response.message || '创建任务失败')
    }
  } catch (error) {
    alert(`生成失败：${error.message}`)
    progress.value = { show: false, value: 0, text: '' }
  } finally {
    generateLoading.value = false
  }
}

async function pollTaskStatus(taskId) {
  const maxAttempts = 300 // 最多轮询 5 分钟
  let attempts = 0

  const poll = async () => {
    if (attempts >= maxAttempts) {
      progress.value = { show: false, value: 0, text: '任务超时' }
      return
    }

    try {
      const response = await editorApi.getTask(taskId)
      if (response.code === 200) {
        const task = response.data
        progress.value = {
          show: true,
          value: task.progress || 0,
          text: task.status === 'running' ? '正在处理…' : task.status === 'success' ? '处理完成' : task.error_message || ''
        }

        if (task.status === 'success') {
          if (task.preview_url) {
            previewUrl.value = task.preview_url
            exportUrl.value = task.preview_url
          }
          progress.value = { show: false, value: 100, text: '完成' }
          alert('剪辑完成！')
          emit('refresh-outputs')
        } else if (task.status === 'fail') {
          progress.value = { show: false, value: 0, text: task.error_message || '处理失败' }
          alert(`剪辑失败：${task.error_message || '未知错误'}`)
        } else {
          // 继续轮询
          attempts++
          setTimeout(poll, 1000)
        }
      } else {
        attempts++
        setTimeout(poll, 1000)
      }
    } catch (error) {
      attempts++
      setTimeout(poll, 1000)
    }
  }

  poll()
}

function handleFullscreen() {
  if (previewVideo.value) {
    try {
      if (previewVideo.value.requestFullscreen) {
        previewVideo.value.requestFullscreen()
      }
    } catch (e) {}
  }
}

// 渲染选中的视频/BGM/配音
function renderSelectedVideos() {
  if (!selectedVideos.value) return
  const box = selectedVideos.value
  box.innerHTML = ''

  const clips = props.timeline?.clips || []
  if (!clips.length) {
    box.innerHTML = '<div class="label">尚未选择视频素材。去"云素材库 → 视频素材库"点击"添加到剪辑轨道"。</div>'
    return
  }

  clips.forEach((clip, idx) => {
    const name = materialNameById(clip.materialId)
    const chip = document.createElement('div')
    chip.className = 'chip'
    chip.innerHTML = `
      <b>${idx + 1}</b>
      <span>${escapeHtml(name)}</span>
      <button class="x" title="上移" data-action="up">↑</button>
      <button class="x" title="下移" data-action="down">↓</button>
      <button class="x" title="移除" data-action="remove">×</button>
    `
    
    chip.querySelector('[data-action="up"]').onclick = () => {
      if (idx <= 0) return
      const newTimeline = { ...props.timeline }
      const arr = newTimeline.clips
      ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
      emit('update-timeline', newTimeline)
    }
    
    chip.querySelector('[data-action="down"]').onclick = () => {
      const newTimeline = { ...props.timeline }
      const arr = newTimeline.clips
      if (idx >= arr.length - 1) return
      ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
      emit('update-timeline', newTimeline)
    }
    
    chip.querySelector('[data-action="remove"]').onclick = () => {
      const newTimeline = { ...props.timeline }
      newTimeline.clips = newTimeline.clips.filter(c => c.id !== clip.id)
      emit('update-timeline', newTimeline)
    }
    
    box.appendChild(chip)
  })
}

function renderSelectedBgm() {
  if (!selectedBgm.value) return
  const box = selectedBgm.value
  box.innerHTML = ''

  const bgm = props.timeline?.bgm
  if (!bgm) {
    box.innerHTML = '<div class="label">未选择 BGM（可不选）。</div>'
    return
  }

  const name = materialNameById(bgm.materialId)
  const chip = document.createElement('div')
  chip.className = 'chip'
  chip.innerHTML = `<b>BGM</b><span>${escapeHtml(name)}</span><button class="x" title="移除">×</button>`
  chip.querySelector('.x').onclick = () => {
    const newTimeline = { ...props.timeline }
    newTimeline.bgm = null
    emit('update-timeline', newTimeline)
  }
  box.appendChild(chip)
}

function renderSelectedVoice() {
  if (!selectedVoice.value) return
  const box = selectedVoice.value
  box.innerHTML = ''

  const voice = props.timeline?.voice
  if (!voice) {
    box.innerHTML = '<div class="label">未选择配音（可不选）。</div>'
    return
  }

  const name = materialNameById(voice.materialId)
  const chip = document.createElement('div')
  chip.className = 'chip'
  chip.innerHTML = `<b>配音</b><span>${escapeHtml(name)}</span><button class="x" title="移除">×</button>`
  chip.querySelector('.x').onclick = () => {
    const newTimeline = { ...props.timeline }
    newTimeline.voice = null
    emit('update-timeline', newTimeline)
  }
  box.appendChild(chip)
}

function setAiTab(tab) {
  aiTab.value = tab
  localStorage.setItem('ve.aiTab', tab)
  nextTick(() => {
    if (tab === 'edit') {
      renderSelectedVideos()
      renderSelectedBgm()
      renderSelectedVoice()
    }
  })
}

// 监听时间线变化
watch(() => props.timeline, () => {
  if (aiTab.value === 'edit') {
    nextTick(() => {
      renderSelectedVideos()
      renderSelectedBgm()
      renderSelectedVoice()
    })
  }
}, { deep: true })

// 初始化
onMounted(() => {
  const savedTab = localStorage.getItem('ve.aiTab') || 'copy'
  setAiTab(savedTab)
  
  // 加载 TTS 音色列表
  aiApi.getTtsVoices().then(response => {
    if (response.code === 200) {
      ttsVoices.value = response.data || ttsVoices.value
    }
  }).catch(() => {})
})
</script>

<style scoped>
/* 复用父组件的样式 */
.aiStep {
  display: none;
}

.aiStep.active {
  display: block;
}

.panel {
  background: #fff;
  border: 1px solid #e0e0e0;
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
  color: #6b7785;
}

.input,
.select,
.textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
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

.btn {
  border: 1px solid #e0e0e0;
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

.btn.primary {
  background: #1677ff;
  border-color: #1677ff;
  color: #fff;
}

.btn.primary:hover {
  background: #0f66e2;
  border-color: #0f66e2;
}

.btn.orange {
  background: #ff7a00;
  border-color: #ff7a00;
  color: #fff;
  font-weight: 800;
  padding: 12px 18px;
  font-size: 15px;
  border-radius: 10px;
}

.btn.orange:hover {
  background: #f17000;
  border-color: #f17000;
}

.btn.loading {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.55);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: none;
}

.btn.loading .spinner {
  display: inline-block;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid #e0e0e0;
  background: #fff;
  border-radius: 999px;
  font-size: 12px;
  color: #2c3e50;
}

.chip b {
  font-weight: 800;
}

.chip .x {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #8a94a3;
  font-size: 16px;
  line-height: 1;
  padding: 0;
}

.progress {
  height: 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  overflow: hidden;
  display: none;
  margin-top: 12px;
}

.progress.show {
  display: block;
}

.bar {
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, rgba(255, 122, 0, 0.35), rgba(255, 122, 0, 1));
  border-radius: 999px;
  transition: width 0.25s ease;
}

.preview-video {
  width: 100%;
  height: 420px;
  border-radius: 10px;
  background: #000;
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
  border: 1px solid #e0e0e0;
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
  background: rgba(22, 119, 255, 0.12);
  border-color: rgba(22, 119, 255, 0.35);
  color: #1677ff;
  font-weight: 800;
}
</style>

