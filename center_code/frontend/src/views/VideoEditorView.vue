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
      <!-- 视频素材选择 -->
      <div class="edit-section">
        <div class="section-header">
          <div class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none">
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>视频素材</span>
          </div>
          <div class="section-hint">从云素材库选择或本地上传</div>
        </div>
        <div class="panel edit-panel">
          <div class="edit-row">
            <div class="edit-field full-width">
              <div class="field-label">
                已选视频素材
                <span class="label-badge" v-if="(props.timeline?.clips || []).length > 0">
                  {{ (props.timeline?.clips || []).length }} 个
                </span>
              </div>
              <div class="chip-list" ref="selectedVideos"></div>
              <div class="field-hint">
                <svg class="hint-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                </svg>
                <span>
                  <strong>说明：</strong>这里显示您选择的视频素材，将按顺序拼接成最终视频。
                  可通过 ↑↓ 调整顺序，× 删除素材。
                  去"云素材库 → 视频素材库"点击"添加到剪辑轨道"来选择素材。
                </span>
              </div>
            </div>
          </div>
          <div class="edit-row" style="margin-top:16px;">
            <div class="edit-field">
              <div class="field-label">本地上传</div>
              <label class="upload-btn">
                <input 
                  type="file" 
                  accept=".mp4,.avi,.mov"
                  @change="handleAiVideoUpload"
                  style="display:none"
                />
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>选择视频文件</span>
              </label>
            </div>
            <div class="edit-field">
              <div class="field-label">AI生成（占位）</div>
              <button class="btn btn-secondary" @click="handleAiGen">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <span>AI生成</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 音频配置 -->
      <div class="edit-section">
        <div class="section-header">
          <div class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none">
              <path d="M11 5L6 9H2v6h4l5 4V5zM19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>音频配置</span>
          </div>
        </div>
        <div class="panel edit-panel">
          <div class="edit-row">
            <div class="edit-field">
              <div class="field-label">配音</div>
              <div class="chip-list" ref="selectedVoice"></div>
              <div class="field-hint">
                <svg class="hint-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                </svg>
                在"配音"模块生成并加入素材库会自动设为配音轨
              </div>
            </div>
            <div class="edit-field">
              <div class="field-label">BGM</div>
              <div class="chip-list" ref="selectedBgm"></div>
              <div class="field-hint">
                <svg class="hint-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                </svg>
                去"云素材库 → BGM库"点击"添加到剪辑轨道"
              </div>
            </div>
          </div>
          <div class="edit-row" style="margin-top:16px;padding-top:16px;border-top:1px solid #f0f0f0;">
            <div class="edit-field">
              <div class="field-label">BGM 音量</div>
              <div class="range-wrapper">
                <input 
                  v-model.number="editForm.bgmVolume" 
                  class="range-input" 
                  type="range" 
                  min="0" 
                  max="100"
                />
                <span class="range-value">{{ editForm.bgmVolume }}%</span>
              </div>
            </div>
            <div class="edit-field">
              <div class="field-label">BGM 循环</div>
              <select v-model="editForm.bgmLoop" class="select">
                <option value="auto">按视频长度截断</option>
                <option value="loop">循环（后端未实现）</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- 输出设置 -->
      <div class="edit-section">
        <div class="section-header">
          <div class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none">
              <path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <rect x="2" y="6" width="20" height="12" rx="2" stroke="currentColor" stroke-width="2"/>
            </svg>
            <span>输出设置</span>
          </div>
        </div>
        <div class="panel edit-panel">
          <div class="edit-row">
            <div class="edit-field">
              <div class="field-label">分辨率</div>
              <select v-model="editForm.resolution" class="select">
                <option value="auto">自动</option>
                <option value="1080p">1080p</option>
                <option value="720p">720p</option>
              </select>
            </div>
            <div class="edit-field">
              <div class="field-label">视频比例</div>
              <select v-model="editForm.ratio" class="select">
                <option value="auto">自动</option>
                <option value="16:9">16:9</option>
                <option value="9:16">9:16</option>
                <option value="1:1">1:1</option>
              </select>
            </div>
            <div class="edit-field">
              <div class="field-label">播放速度</div>
              <select v-model.number="editForm.speed" class="select">
                <option :value="1">1.0x</option>
                <option :value="0.75">0.75x</option>
                <option :value="1.25">1.25x</option>
                <option :value="1.5">1.5x</option>
                <option :value="2">2.0x</option>
              </select>
            </div>
          </div>
          <div class="edit-row" style="margin-top:16px;padding-top:16px;border-top:1px solid #f0f0f0;">
            <div class="edit-field full-width">
              <div class="field-label">字幕设置</div>
              <div class="subtitle-options">
                <label class="checkbox-label">
                  <input 
                    v-model="editForm.subtitleEnabled" 
                    type="checkbox"
                    class="checkbox-input"
                  />
                  <span class="checkbox-text">生成并烧录字幕（需要已选择配音音频）</span>
                </label>
                <div class="subtitle-actions">
                  <button class="btn btn-secondary" @click="handleSubPreview" type="button">
                    <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span>生成字幕预览</span>
                  </button>
                  <a 
                    v-if="subtitleUrl" 
                    class="btn btn-secondary" 
                    :href="subtitleUrl" 
                    target="_blank"
                  >
                    <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span>下载SRT</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 生成按钮和进度 -->
      <div class="edit-section">
        <div class="panel edit-panel generate-panel">
          <div class="generate-content">
            <button 
              class="btn btn-generate" 
              :class="{ loading: generateLoading }"
              @click="handleGenerate"
              :disabled="generateLoading"
            >
              <svg v-if="!generateLoading" class="btn-icon" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span class="spinner" v-if="generateLoading"></span>
              <span>{{ generateLoading ? '正在生成中...' : '一键生成AI剪辑视频' }}</span>
            </button>
            
            <div class="progress-wrapper" v-if="progress.show">
              <div class="progress-info">
                <span class="progress-text">{{ progress.text || '处理中...' }}</span>
                <span class="progress-percent">{{ Math.round(progress.value) }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: `${Math.min(100, Math.max(0, progress.value))}%` }"></div>
              </div>
            </div>
          </div>
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
    box.innerHTML = '<div class="empty-state"><svg class="empty-icon" viewBox="0 0 24 24" fill="none"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><div class="empty-text">尚未选择视频素材</div><div class="empty-hint">去"云素材库 → 视频素材库"点击"添加到剪辑轨道"来选择素材</div></div>'
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

/* 剪辑生成优化样式 */
.edit-section {
  max-width: 980px;
  margin: 20px auto 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 800;
  color: #2c3e50;
}

.section-icon {
  width: 20px;
  height: 20px;
  color: #1677ff;
}

.section-hint {
  font-size: 12px;
  color: #8a94a3;
}

.edit-panel {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.edit-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.edit-field.full-width {
  grid-column: 1 / -1;
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.label-badge {
  padding: 2px 8px;
  background: rgba(22, 119, 255, 0.1);
  color: #1677ff;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 800;
}

.field-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #8a94a3;
  margin-top: 4px;
  line-height: 1.4;
}

.hint-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: #1677ff;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 32px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px dashed #e0e0e0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
  min-height: 120px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: #d0d0d0;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
  color: #8a94a3;
  font-weight: 600;
  margin-bottom: 6px;
}

.empty-hint {
  font-size: 12px;
  color: #b0b0b0;
  line-height: 1.5;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  background: #fff;
  border-radius: 8px;
  font-size: 12px;
  color: #2c3e50;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
}

.chip:hover {
  border-color: #1677ff;
  box-shadow: 0 2px 6px rgba(22, 119, 255, 0.15);
}

.chip b {
  font-weight: 800;
  color: #1677ff;
  padding: 2px 6px;
  background: rgba(22, 119, 255, 0.1);
  border-radius: 4px;
}

.chip-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

.chip-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #8a94a3;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
  width: 24px;
  height: 24px;
}

.chip-btn svg {
  width: 14px;
  height: 14px;
}

.chip-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #1677ff;
}

.chip-btn-danger:hover {
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
}

.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px dashed #d0d0d0;
  background: #fafafa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  color: #2c3e50;
}

.upload-btn:hover {
  border-color: #1677ff;
  background: rgba(22, 119, 255, 0.05);
  color: #1677ff;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-secondary {
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #2c3e50;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary:hover {
  background: #f6f8fa;
  border-color: #1677ff;
  color: #1677ff;
}

.range-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.range-input {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: #e0e0e0;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #1677ff;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.range-input::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #1677ff;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.range-value {
  font-size: 13px;
  font-weight: 600;
  color: #1677ff;
  min-width: 45px;
  text-align: right;
}

.subtitle-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex: 1;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #1677ff;
}

.checkbox-text {
  font-size: 13px;
  color: #2c3e50;
}

.subtitle-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.generate-panel {
  background: linear-gradient(135deg, rgba(22, 119, 255, 0.05), rgba(255, 122, 0, 0.05));
  border-color: rgba(22, 119, 255, 0.2);
}

.generate-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.btn-generate {
  background: linear-gradient(135deg, #ff7a00, #ff9500);
  border: none;
  color: #fff;
  font-weight: 800;
  padding: 14px 32px;
  font-size: 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 12px rgba(255, 122, 0, 0.3);
  min-width: 200px;
  justify-content: center;
}

.btn-generate:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(255, 122, 0, 0.4);
}

.btn-generate:active:not(:disabled) {
  transform: translateY(0);
}

.btn-generate:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.progress-wrapper {
  width: 100%;
  max-width: 600px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.progress-text {
  color: #2c3e50;
  font-weight: 600;
}

.progress-percent {
  color: #1677ff;
  font-weight: 800;
}

.progress-bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1677ff, #ff7a00);
  border-radius: 999px;
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
</style>

