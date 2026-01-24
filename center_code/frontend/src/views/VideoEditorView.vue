<template>
  <div class="video-editor-view">
    <!-- 步骤导航 -->
    <div class="steps-nav" style="max-width:980px;margin:0 auto 20px;">
      <div 
        class="step-item" 
        :class="{ active: aiTab === 'copy', completed: copyForm.output }"
        @click="setAiTab('copy')"
      >
        <div class="step-number">1</div>
        <div class="step-content">
          <div class="step-title">文案生成</div>
          <div class="step-desc">AI生成视频文案</div>
        </div>
        <div v-if="copyForm.output" class="step-check">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </div>
      <div class="step-connector"></div>
      <div 
        class="step-item" 
        :class="{ active: aiTab === 'tts', completed: props.timeline?.voice }"
        @click="setAiTab('tts')"
      >
        <div class="step-number">2</div>
        <div class="step-content">
          <div class="step-title">配音生成</div>
          <div class="step-desc">将文案转为语音</div>
        </div>
        <div v-if="props.timeline?.voice" class="step-check">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </div>
      <div class="step-connector"></div>
      <div 
        class="step-item" 
        :class="{ active: aiTab === 'edit', completed: previewUrl }"
        @click="setAiTab('edit')"
      >
        <div class="step-number">3</div>
        <div class="step-content">
          <div class="step-title">剪辑生成</div>
          <div class="step-desc">合成最终视频</div>
        </div>
        <div v-if="previewUrl" class="step-check">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </div>
      <div class="step-connector"></div>
      <div 
        class="step-item" 
        :class="{ active: aiTab === 'history' }"
        @click="setAiTab('history')"
      >
        <div class="step-number step-icon">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M3 3h18v18H3z" stroke="currentColor" stroke-width="2"/>
            <path d="M9 9h6v6H9z" stroke="currentColor" stroke-width="2"/>
          </svg>
        </div>
        <div class="step-content">
          <div class="step-title">历史任务</div>
          <div class="step-desc">查看剪辑记录</div>
        </div>
      </div>
    </div>

    <!-- 文案步骤 -->
    <div class="aiStep" v-if="aiTab === 'copy'">
      <div class="step-container">
        <div class="step-header">
          <h2 class="step-title">第一步：生成视频文案</h2>
          <p class="step-subtitle">使用AI生成吸引人的视频文案，支持自定义主题和风格</p>
        </div>
        
        <div class="panel step-panel">
          <div class="form-grid">
            <div class="form-field">
              <label class="form-label">
                <span class="label-text">主题</span>
                <span class="label-required">*</span>
              </label>
              <input 
                v-model="copyForm.theme" 
                class="form-input" 
                placeholder="例如：冬日城市漫游 / 美食探店 / 旅行Vlog"
              />
              <div class="field-tip">描述视频的主要内容或场景</div>
            </div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-text">关键词</span>
                <span class="label-optional">（可选）</span>
              </label>
              <input 
                v-model="copyForm.keywords" 
                class="form-input" 
                placeholder="例如：温暖、治愈、街景、镜头感…"
              />
              <div class="field-tip">添加关键词以影响文案风格</div>
            </div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-text">生成数量</span>
              </label>
              <input 
                v-model.number="copyForm.count" 
                class="form-input" 
                type="number"
                min="1"
                max="10"
              />
              <div class="field-tip">生成多个版本供选择（1-10个）</div>
            </div>
          </div>
          <div class="form-field full-width">
            <label class="form-label">
              <span class="label-text">参考文案</span>
              <span class="label-optional">（可选）</span>
            </label>
            <textarea 
              v-model="copyForm.reference" 
              class="form-textarea" 
              placeholder="粘贴一段参考文案，AI会参考其风格和结构生成新文案"
              rows="4"
            ></textarea>
            <div class="field-tip">提供参考文案可以帮助AI更好地理解您想要的风格</div>
          </div>
          
          <div class="form-actions">
            <button 
              class="btn btn-primary btn-large" 
              :class="{ loading: copyLoading }"
              @click="handleCopyGenerate"
              :disabled="!copyForm.theme || copyLoading"
            >
              <span class="spinner"></span>
              <svg v-if="!copyLoading" class="btn-icon" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>{{ copyLoading ? '生成中...' : '生成文案' }}</span>
            </button>
            <button class="btn btn-secondary" @click="handleCopyClear" :disabled="copyLoading">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>清空</span>
            </button>
            <button class="btn btn-secondary" @click="handleCopyCopy" :disabled="!copyForm.output || copyLoading">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                <path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2M8 2v4M16 2v4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>复制</span>
            </button>
          </div>
          
          <div v-if="copyOptions.length > 0" class="form-field full-width" style="margin-top:20px;padding-top:20px;border-top:1px solid #f0f0f0;">
            <label class="form-label">
              <span class="label-text">选择文案版本</span>
            </label>
            <div class="copy-options">
              <div 
                v-for="(opt, idx) in copyOptions" 
                :key="idx"
                class="copy-option-card"
                :class="{ active: selectedCopyIndex === idx }"
                @click="selectedCopyIndex = idx; applyCopyOption()"
              >
                <div class="option-header">
                  <span class="option-title">{{ opt.title }}</span>
                  <div class="option-badge" v-if="selectedCopyIndex === idx">已选择</div>
                </div>
                <div class="option-preview">{{ opt.text.substring(0, 100) }}{{ opt.text.length > 100 ? '...' : '' }}</div>
              </div>
            </div>
          </div>
          
          <div class="form-field full-width" style="margin-top:20px;">
            <label class="form-label">
              <span class="label-text">文案预览/编辑</span>
            </label>
            <textarea 
              v-model="copyForm.output" 
              class="form-textarea" 
              placeholder="生成的文案将显示在这里，您可以进一步编辑和完善..."
              rows="8"
            ></textarea>
            <div class="field-tip" v-if="copyForm.output">
              文案字数：{{ copyForm.output.length }} 字
              <span v-if="copyForm.output.length > 500" class="tip-warning">（建议控制在500字以内）</span>
            </div>
            <div class="field-tip" v-else>
              文案将用于生成配音，建议控制在500字以内
            </div>
          </div>
          
          <!-- 下一步按钮 -->
          <div class="step-footer" v-if="copyForm.output">
            <div class="footer-tip">
              <svg class="tip-icon" viewBox="0 0 24 24" fill="none">
                <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              </svg>
              <span>文案已准备就绪，点击下方按钮前往配音生成</span>
            </div>
            <button class="btn btn-primary btn-large" @click="setAiTab('tts')">
              <span>下一步：生成配音</span>
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 配音步骤 -->
    <div class="aiStep" v-if="aiTab === 'tts'">
      <div class="step-container">
        <div class="step-header">
          <h2 class="step-title">第二步：生成配音</h2>
          <p class="step-subtitle">将文案转换为语音，选择合适的音色和参数</p>
        </div>
        
        <div class="panel step-panel">
          <div v-if="!copyForm.output" class="empty-state-warning">
            <svg class="warning-icon" viewBox="0 0 24 24" fill="none">
              <path d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <div class="warning-content">
              <div class="warning-title">请先完成文案生成</div>
              <div class="warning-desc">需要先在第一步骤中生成或输入文案，才能进行配音生成</div>
              <button class="btn btn-primary" @click="setAiTab('copy')">
                <span>前往文案生成</span>
              </button>
            </div>
          </div>
          
          <template v-else>
            <div class="form-grid">
              <div class="form-field full-width">
                <label class="form-label">
                  <span class="label-text">文案内容</span>
                </label>
                <div class="copy-preview-box">
                  <div class="copy-text">{{ copyForm.output || '暂无文案' }}</div>
                  <div class="copy-stats">
                    <span>字数：{{ copyForm.output.length }}</span>
                    <button class="btn-link" @click="setAiTab('copy')">编辑文案</button>
                  </div>
                </div>
              </div>
              
              <div class="form-field">
                <label class="form-label">
                  <span class="label-text">音色选择</span>
                </label>
                <select v-model="ttsForm.voice" class="form-select">
                  <option 
                    v-for="voice in ttsVoices" 
                    :key="voice.id" 
                    :value="voice.id"
                  >
                    {{ voice.name }}
                  </option>
                </select>
                <div class="field-tip">选择适合视频风格的音色</div>
              </div>
              
              <div class="form-field">
                <label class="form-label">
                  <span class="label-text">自定义音色</span>
                  <span class="label-optional">（可选）</span>
                </label>
                <label class="upload-btn-secondary">
                  <input 
                    type="file" 
                    accept="audio/*"
                    @change="handleVoiceUpload"
                    style="display:none"
                  />
                  <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span>上传音频</span>
                </label>
                <div class="field-tip">上传自定义音色文件（演示功能）</div>
              </div>
            </div>
            
            <div class="form-actions" style="margin-top:24px;padding-top:24px;border-top:1px solid #f0f0f0;">
              <button 
                class="btn btn-primary btn-large" 
                :class="{ loading: ttsLoading }"
                @click="handleVoiceSave"
                :disabled="!copyForm.output || ttsLoading"
              >
                <span class="spinner"></span>
                <svg v-if="!ttsLoading" class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>{{ ttsLoading ? '生成中...' : '生成配音并加入素材库' }}</span>
              </button>
              <button 
                class="btn btn-secondary" 
                @click="handleVoicePreview"
                :disabled="!copyForm.output || ttsLoading"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <rect x="2" y="6" width="20" height="12" rx="2" stroke="currentColor" stroke-width="2"/>
                </svg>
                <span>试听预览</span>
              </button>
            </div>
            
            <div class="step-footer" v-if="props.timeline?.voice">
              <div class="footer-tip success">
                <svg class="tip-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>配音已生成并设置为配音轨，请前往"剪辑生成"步骤合成视频</span>
              </div>
              <button class="btn btn-primary" @click="setAiTab('edit')">
                <span>下一步：剪辑生成</span>
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 剪辑生成步骤 -->
    <div class="aiStep" v-if="aiTab === 'edit'">
      <div class="step-container">
        <div class="step-header">
          <h2 class="step-title">第三步：剪辑生成</h2>
          <p class="step-subtitle">选择视频素材、配置音频和参数，一键生成AI剪辑视频</p>
        </div>
        
      <!-- 视频素材选择 -->
      <div class="edit-section">
        <div class="section-header">
          <div class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none">
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>视频素材</span>
            <span class="label-badge" v-if="(props.timeline?.clips || []).length > 0">
              {{ (props.timeline?.clips || []).length }} 个
            </span>
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
              <div class="field-label">从素材库选择</div>
              <button class="btn btn-primary" @click="openMaterialSelector">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M9 22V12h6v10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>从素材库选择视频</span>
              </button>
            </div>
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
              <div style="margin-top: 8px;">
                <button class="btn btn-secondary" @click="openVoiceSelector" style="font-size: 12px; padding: 6px 12px;">
                  <svg class="btn-icon" viewBox="0 0 24 24" fill="none" style="width: 14px; height: 14px;">
                    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M9 22V12h6v10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span>从素材库选择</span>
                </button>
              </div>
              <div class="field-hint">
                <svg class="hint-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                </svg>
                可在"配音"模块生成，或从素材库选择音频作为配音
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
                <!-- 字幕预览显示 -->
                <div v-if="subtitleUrl" class="subtitle-preview">
                  <div class="subtitle-preview-header">
                    <svg class="subtitle-icon" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span class="subtitle-preview-title">字幕预览</span>
                    <span class="subtitle-status-badge">已生成</span>
                  </div>
                  <div v-if="recognizedText" class="subtitle-text-preview">
                    <div class="subtitle-text-label">识别内容：</div>
                    <div class="subtitle-text-content">{{ recognizedText }}</div>
                  </div>
                  <div class="subtitle-file-info">
                    <span class="subtitle-file-label">字幕文件：</span>
                    <span class="subtitle-file-name">{{ subtitleUrl.split('/').pop() }}</span>
                  </div>
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

      <!-- 视频预览 -->
      <div class="edit-section">
        <div class="panel edit-panel">
          <div class="section-header">
            <div class="section-title">
              <svg class="section-icon" viewBox="0 0 24 24" fill="none">
                <path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <rect x="2" y="6" width="20" height="12" rx="2" stroke="currentColor" stroke-width="2"/>
              </svg>
              <span>视频预览</span>
            </div>
          </div>
          <div class="preview-container">
            <video 
              ref="previewVideo"
              class="preview-video" 
              controls
              v-if="previewUrl"
            >
              <source :src="previewUrl" type="video/mp4" />
              您的浏览器不支持HTML5视频播放，请更换浏览器后重试
            </video>
            <div v-else class="preview-placeholder">
              <svg class="placeholder-icon" viewBox="0 0 24 24" fill="none">
                <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <div class="placeholder-text">暂无预览视频</div>
              <div class="placeholder-desc">生成视频后将显示在这里</div>
            </div>
            <div class="preview-actions" v-if="previewUrl || exportUrl">
              <a 
                v-if="exportUrl" 
                class="btn btn-primary" 
                :href="exportUrl" 
                target="_blank"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>下载视频</span>
              </a>
              <button 
                v-if="previewUrl" 
                class="btn btn-secondary" 
                @click="handleFullscreen"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>全屏播放</span>
              </button>
              <button class="btn btn-secondary" @click="$emit('open-outputs')">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M3 3h18v18H3z" stroke="currentColor" stroke-width="2"/>
                  <path d="M9 9h6v6H9z" stroke="currentColor" stroke-width="2"/>
                </svg>
                <span>查看成品库</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- 历史任务步骤 -->
    <div class="aiStep" v-if="aiTab === 'history'">
      <div class="panel" style="max-width:980px;margin:0 auto;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <div class="label">历史任务列表</div>
          <button class="btn" @click="loadHistoryTasks" :disabled="historyLoading">
            <span v-if="historyLoading">加载中...</span>
            <span v-else>刷新</span>
          </button>
        </div>
        
        <div v-if="historyLoading" style="text-align:center;padding:40px;">
          <div class="spinner"></div>
          <div style="margin-top:10px;color:#8a94a3;">加载中...</div>
        </div>
        
        <div v-else-if="historyTasks.length === 0" style="text-align:center;padding:40px;color:#8a94a3;">
          暂无历史任务
        </div>
        
        <div v-else style="display:grid;gap:12px;">
          <div 
            v-for="task in historyTasks" 
            :key="task.id"
            class="history-task-item"
            :class="{ 'task-success': task.status === 'success', 'task-fail': task.status === 'fail', 'task-running': task.status === 'running' }"
            style="padding:16px;border:1px solid #e0e0e0;border-radius:8px;background:#fff;"
          >
            <div style="display:flex;justify-content:space-between;align-items:start;">
              <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                  <span style="font-weight:500;">任务 #{{ task.id }}</span>
                  <span 
                    class="task-status"
                    :class="{
                      'status-success': task.status === 'success',
                      'status-fail': task.status === 'fail',
                      'status-running': task.status === 'running',
                      'status-pending': task.status === 'pending'
                    }"
                    style="padding:2px 8px;border-radius:4px;font-size:12px;"
                  >
                    {{ getTaskStatusText(task.status) }}
                  </span>
                  <span v-if="task.progress !== undefined && task.progress !== null" style="color:#8a94a3;font-size:12px;">
                    进度: {{ task.progress }}%
                  </span>
                </div>
                <div style="color:#8a94a3;font-size:12px;margin-bottom:4px;">
                  <span>视频: {{ task.video_ids || '-' }}</span>
                  <span style="margin-left:12px;">配音: {{ task.voice_id || '-' }}</span>
                  <span style="margin-left:12px;">BGM: {{ task.bgm_id || '-' }}</span>
                  <span style="margin-left:12px;">速度: {{ task.speed || 1.0 }}x</span>
                </div>
                <div style="color:#8a94a3;font-size:12px;">
                  创建时间: {{ formatTime(task.create_time || task.update_time) }}
                </div>
                <div v-if="task.error_message" style="color:#f56c6c;font-size:12px;margin-top:4px;">
                  错误: {{ task.error_message }}
                </div>
              </div>
              <div style="display:flex;gap:8px;margin-left:16px;">
                <button 
                  v-if="task.preview_url" 
                  class="btn" 
                  @click="previewTask(task)"
                  style="font-size:12px;padding:4px 12px;"
                >
                  预览
                </button>
                <button 
                  v-if="task.output_filename" 
                  class="btn" 
                  @click="downloadTask(task)"
                  style="font-size:12px;padding:4px 12px;"
                >
                  下载
                </button>
                <button 
                  class="btn danger" 
                  @click="deleteTask(task)"
                  style="font-size:12px;padding:4px 12px;"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 素材选择器模态框 -->
    <div class="mask" :class="{ show: materialSelector.show }" @click="handleMaterialSelectorMaskClick">
      <div class="modal material-selector-modal" @click.stop>
        <div class="modal-header">
          <div class="modal-title">
            {{ materialSelector.type === 'media' ? '选择视频/图片素材' : materialSelector.type === 'audio' ? '选择音频素材' : materialSelector.type === 'video' ? '选择视频素材' : '选择素材' }}
          </div>
          <button class="modal-close" @click="closeMaterialSelector">×</button>
        </div>
        <div class="modal-body">
          <div class="material-selector-search">
            <input 
              v-model="materialSelector.search" 
              class="input" 
              placeholder="搜索素材名称..."
              @input="filterMaterials"
            />
          </div>
          <div class="material-selector-list">
            <div 
              v-for="material in filteredMaterials" 
              :key="material.id"
              class="material-item"
              :class="{ selected: Number(materialSelector.selectedId) === Number(material.id), disabled: !isMaterialReady(material) }"
              @click="trySelectMaterial(material)"
            >
              <div class="material-info">
                <div class="material-name">{{ getMaterialDisplayName(material) }}</div>
                <div class="material-meta">
                  <span v-if="material.duration">时长: {{ formatDuration(material.duration) }}</span>
                  <span v-if="material.size" style="margin-left: 12px;">大小: {{ formatSize(material.size) }}</span>
                  <span v-if="material.created_at || material.create_time" style="margin-left: 12px; color: #8a94a3;">
                    {{ formatMaterialTime(material.created_at || material.create_time) }}
                  </span>
                  <span v-if="!isMaterialReady(material)" class="material-status" :class="statusClass(material)">
                    {{ statusText(material) }}
                  </span>
                </div>
                <div v-if="materialSelector.type === 'audio'" class="material-preview" @click.stop="previewMaterial(material)">
                  <svg class="preview-icon" viewBox="0 0 24 24" fill="none">
                    <path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <rect x="2" y="6" width="20" height="12" rx="2" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>试听</span>
                </div>
              </div>
              <svg v-if="Number(materialSelector.selectedId) === Number(material.id)" class="check-icon" viewBox="0 0 24 24" fill="none">
                <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div v-if="filteredMaterials.length === 0" class="empty-materials">
              <div class="empty-text">
                {{ materialSelector.type === 'media' ? '暂无视频/图片素材' : materialSelector.type === 'audio' ? '暂无音频素材' : materialSelector.type === 'video' ? '暂无视频素材' : '暂无素材' }}
              </div>
              <div class="empty-hint">
                <span v-if="props.materials && props.materials.length > 0">
                  当前素材库中有 {{ props.materials.length }} 个素材，但没有{{ materialSelector.type === 'media' ? '视频/图片' : materialSelector.type === 'video' ? '视频' : '音频' }}类型的素材
                </span>
                <span v-else>
                  请先上传{{ materialSelector.type === 'media' ? '视频/图片' : materialSelector.type === 'video' ? '视频' : '音频' }}素材到素材库
                </span>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeMaterialSelector">取消</button>
            <button 
              class="btn btn-primary" 
              @click="confirmMaterialSelection"
              :disabled="!materialSelector.selectedId"
            >
              确认选择
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 音频预览模态框 -->
    <div class="mask" :class="{ show: audioModal.show }" @click="handleMaskClick">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <div class="modal-title">{{ audioModal.title }}</div>
          <button class="modal-close" @click="closeAudioModal">×</button>
        </div>
        <div class="modal-body">
          <div v-if="audioModal.kind === 'audio'" class="audio-wrapper">
            <audio 
              ref="modalAudio"
              class="audio" 
              controls
              preload="auto"
              :src="audioModal.url"
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
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, inject } from 'vue'
import { ElMessage } from 'element-plus'
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

// 尝试从父组件注入预览音频方法（作为备用方案）
const previewAudioFromParent = inject('previewAudio', null)

// 状态
const aiTab = ref('copy')
const copyLoading = ref(false)
const ttsLoading = ref(false)
const generateLoading = ref(false)
let pollTimeoutId = null

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

const defaultImageDuration = ref(2.0)

// 预览和进度
const previewUrl = ref('')
const exportUrl = ref('')
const subtitleUrl = ref('')
const recognizedText = ref('')  // 从音频识别的文字
const progress = ref({ show: false, value: 0, text: '' })

// 历史任务
const historyTasks = ref([])
const historyLoading = ref(false)

// DOM 引用
const selectedVideos = ref(null)
const selectedVoice = ref(null)
const selectedBgm = ref(null)
const previewVideo = ref(null)

// 本地状态：保存最近设置的配音（用于处理 props 更新延迟的问题）
const localVoiceState = ref(null)

// 音频预览模态框
const audioModal = ref({ show: false, title: '', kind: '', url: '' })
const modalAudio = ref(null)
const isClosingModal = ref(false) // 标志：是否正在关闭模态框

// 素材选择器
const materialSelector = ref({ show: false, search: '', selectedId: null, type: 'media', action: null }) // type: 'media' | 'audio', action: 'voice' | 'bgm' | null
const filteredMaterials = ref([])

// 本地素材列表（当没有从父组件接收时使用）
const localMaterials = ref([])

// 计算属性：优先使用 props.materials，如果为空则使用本地加载的素材
const effectiveMaterials = computed(() => {
  if (props.materials && props.materials.length > 0) {
    return props.materials
  }
  return localMaterials.value
})

// 工具函数
function materialNameById(materialId) {
  const m = effectiveMaterials.value.find(x => x.id === materialId)
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
const ttsPreviewLoading = ref(false)

async function handleVoicePreview() {
  const text = getTtsText(500)
  if (!text) {
    ElMessage.warning('请先生成/填写文案（用于试听）')
    return
  }

  ttsPreviewLoading.value = true
  try {
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
        // 优先使用父组件的方法（如果存在）
        if (previewAudioFromParent) {
          try {
            previewAudioFromParent(url)
            ElMessage.success('音频生成成功，正在播放...')
            return
          } catch (error) {
            // 如果父组件方法失败，继续使用自己的模态框
          }
        }
        
        // 尝试发送事件给父组件（如果父组件监听了事件，可能会处理）
        // 但为了确保总是有模态框显示，我们也使用自己的模态框
        try {
          emit('preview-audio', url)
        } catch (error) {
          // 忽略事件发送错误
        }
        
        // 使用自己的模态框（作为备用方案，确保总是有模态框显示）
        openAudioModal('TTS 试听', 'audio', url)
        ElMessage.success('音频生成成功，正在播放...')
      } else {
        ElMessage.error('缺少 preview_url')
      }
    } else {
      ElMessage.error(`TTS失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    ElMessage.error(`TTS失败：${error.message}`)
  } finally {
    ttsPreviewLoading.value = false
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
      persist: true,
      theme: copyForm.value.theme || '',  // 传递主题
      keywords: copyForm.value.keywords || ''  // 传递关键字
    })

    if (response.code === 200) {
      const materialId = response.data?.material_id
      if (materialId) {
        // 更新时间线
        const newTimeline = { ...props.timeline }
        if (!newTimeline.voice) newTimeline.voice = {}
        newTimeline.voice.materialId = Number(materialId)
        emit('update-timeline', newTimeline)
        
        // 刷新素材列表（由父组件处理）
        emit('refresh-materials')
        
        // 立即更新本地素材列表（如果使用本地加载）
        if (localMaterials.value.length > 0 || !props.materials || props.materials.length === 0) {
          loadMaterials().then(() => {
            // 素材加载后，重新渲染配音显示
            nextTick(() => {
              renderSelectedVoice()
            })
          })
        } else {
          // 如果使用 props.materials，直接渲染
          nextTick(() => {
            renderSelectedVoice()
          })
        }
        
        ElMessage.success('已生成并加入素材库，已设为配音')
      } else {
        ElMessage.error('入库失败（未返回 material_id）')
      }
    } else {
      ElMessage.error(`生成失败：${response.message || '未知错误'}`)
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
    ElMessage.info('正在上传并添加到剪辑轨道…')
    const response = await materialApi.uploadMaterial(file)
    if (response.code === 200) {
      const materialId = response.data?.material_id
      const uploadedType = (response.data?.type || '').toLowerCase()
      const status = ((response.data?.status || 'ready') + '').toLowerCase()

      if (status === 'processing' && materialId) {
        emit('refresh-materials')
        pollMaterialStatus(materialId)
        ElMessage.info('已接收，转码中（完成后可用）')
        return
      }
      if (materialId) {
        // 添加到时间线
        const newTimeline = { ...props.timeline }
        if (!newTimeline.clips) newTimeline.clips = []
        const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
        if (uploadedType === 'image') {
          newTimeline.clips.push({ id, type: 'image', materialId: Number(materialId), duration: Number(defaultImageDuration.value || 2.0) })
        } else {
          newTimeline.clips.push({ id, type: 'video', materialId: Number(materialId) })
        }
        emit('update-timeline', newTimeline)
        
        // 刷新素材列表
        emit('refresh-materials')
        
        // 立即渲染视频列表
        nextTick(() => {
          renderSelectedVideos()
        })
        
        ElMessage.success('上传成功，已加入剪辑轨道')
      }
    } else {
      ElMessage.error(`上传失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    ElMessage.error(`上传失败：${error.message}`)
  } finally {
    e.target.value = ''
  }
}

let _pollingMaterialIds = new Set()
function pollMaterialStatus(materialId) {
  const mid = Number(materialId)
  if (!mid || _pollingMaterialIds.has(mid)) return
  _pollingMaterialIds.add(mid)

  const startedAt = Date.now()
  const timeoutMs = 5 * 60 * 1000
  const intervalMs = 2000

  const tick = async () => {
    try {
      await loadMaterials()
      emit('refresh-materials')

      const m = effectiveMaterials.value.find(x => Number(x.id) === mid)
      const s = ((m?.status || 'ready') + '').toLowerCase()
      if (s === 'processing') {
        if (Date.now() - startedAt < timeoutMs) {
          setTimeout(tick, intervalMs)
          return
        }
        ElMessage.warning('转码超时，请稍后手动刷新素材库')
      } else if (s === 'ready') {
        ElMessage.success('转码完成，可使用该素材')
      } else if (s === 'failed') {
        ElMessage.error('转码失败（可在素材库下载原始文件排查）')
      }
    } catch (e) {
      // ignore polling errors
    } finally {
      _pollingMaterialIds.delete(mid)
    }
  }

  setTimeout(tick, intervalMs)
}

function handleAiGen() {
  alert('AI生成（占位）：后续可接入生成式视频/检索素材。')
}

// 素材选择器相关函数
async function openMaterialSelector() {
  materialSelector.value = { show: true, search: '', selectedId: null, type: 'media' }
  
  // 如果素材列表为空，尝试加载
  if (effectiveMaterials.value.length === 0) {
    await loadMaterials()
  }
  
  filterMaterials()
  
}

// 打开配音选择器
async function openVoiceSelector() {
  materialSelector.value = { show: true, search: '', selectedId: null, type: 'audio', action: 'voice' }
  
  // 如果素材列表为空，尝试加载
  if (effectiveMaterials.value.length === 0) {
    await loadMaterials()
  }
  
  filterMaterials()
}

// 打开BGM选择器
async function openBgmSelector() {
  materialSelector.value = { show: true, search: '', selectedId: null, type: 'audio', action: 'bgm' }
  
  // 如果素材列表为空，尝试加载
  if (effectiveMaterials.value.length === 0) {
    await loadMaterials()
  }
  
  filterMaterials()
}

// 加载素材列表（当没有从父组件接收时使用）
async function loadMaterials() {
  try {
    const response = await materialApi.getMaterials({ type: null })
    if (response.code === 200) {
      const materials = Array.isArray(response.data) ? response.data : (response.data?.materials || [])
      localMaterials.value = materials
    } else {
      ElMessage.error(`加载素材失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    ElMessage.error(`加载素材失败：${error.message || '未知错误'}`)
  }
}

function closeMaterialSelector() {
  materialSelector.value = { show: false, search: '', selectedId: null, type: 'media', action: null }
}

function handleMaterialSelectorMaskClick(e) {
  if (e.target.classList.contains('mask')) {
    closeMaterialSelector()
  }
}

function filterMaterials() {
  const search = materialSelector.value.search.toLowerCase().trim()
  const selectorType = materialSelector.value.type || 'media'
  
  // 使用有效的素材列表（优先使用 props.materials，如果为空则使用本地加载的）
  const allMaterials = effectiveMaterials.value
  
  // 根据选择器类型过滤素材
  let filteredByType = []
  if (selectorType === 'media') {
    filteredByType = allMaterials.filter(m => {
      const type = (m.type || '').toLowerCase()
      return (
        type === 'video' || type === 'mp4' || type === 'avi' || type === 'mov' ||
        type === 'image' || type === 'jpg' || type === 'jpeg' || type === 'png' || type === 'gif' || type === 'webp'
      )
    })
  } else if (selectorType === 'video') {
    // 过滤视频素材，兼容不同的类型值
    filteredByType = allMaterials.filter(m => {
      const type = (m.type || '').toLowerCase()
      return type === 'video' || type === 'mp4' || type === 'avi' || type === 'mov'
    })
  } else if (selectorType === 'audio') {
    // 过滤音频素材，兼容不同的类型值
    filteredByType = allMaterials.filter(m => {
      const type = (m.type || '').toLowerCase()
      return type === 'audio' || type === 'mp3' || type === 'wav' || type === 'flac'
    })
  }
  
  
  if (search) {
    filteredMaterials.value = filteredByType.filter(m => {
      const name = (m.name || '').toLowerCase()
      return name.includes(search)
    })
  } else {
    filteredMaterials.value = filteredByType
  }
  
}

function materialStatus(material) {
  return ((material?.status || 'ready') + '').toLowerCase()
}

function isMaterialReady(material) {
  return materialStatus(material) === 'ready' && !!material?.path
}

function statusText(material) {
  const s = materialStatus(material)
  if (s === 'processing') return '转码中'
  if (s === 'failed') return '失败'
  return s || 'unknown'
}

function statusClass(material) {
  const s = materialStatus(material)
  return s ? `status-${s}` : ''
}

function trySelectMaterial(material) {
  if (!isMaterialReady(material)) {
    ElMessage.info('素材未就绪，暂不可选择')
    return
  }
  materialSelector.value.selectedId = Number(material?.id)
}

function confirmMaterialSelection() {
  if (!materialSelector.value.selectedId) return
  
  const materialId = materialSelector.value.selectedId
  const selectorType = materialSelector.value.type || 'media'
  const selectedMat = effectiveMaterials.value.find(x => Number(x.id) === Number(materialId))
  if (!isMaterialReady(selectedMat)) {
    ElMessage.info('素材未就绪，暂不可使用')
    return
  }
  const newTimeline = { ...props.timeline }
  
  if (selectorType === 'media') {
    // 添加到视频剪辑轨道
    if (!newTimeline.clips) newTimeline.clips = []
    const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
    const mid = Number(materialId)
    const mat = effectiveMaterials.value.find(x => Number(x.id) === mid)
    const type = (mat?.type || 'video').toLowerCase()
    const isImage = ['image', 'jpg', 'jpeg', 'png', 'gif', 'webp'].includes(type)
    if (isImage) {
      newTimeline.clips.push({ id, type: 'image', materialId: mid, duration: Number(defaultImageDuration.value || 2.0) })
    } else {
      newTimeline.clips.push({ id, type: 'video', materialId: mid })
    }
    emit('update-timeline', newTimeline)
    ElMessage.success('已添加到剪辑轨道')
    
    // 立即渲染视频列表
    nextTick(() => {
      renderSelectedVideos(newTimeline)
    })
  } else if (selectorType === 'audio') {
    // 判断是配音还是BGM（根据当前打开的选择器上下文）
    // 这里我们需要一个额外的标志来区分，暂时都设为配音
    // 可以通过检查 materialSelector 的额外属性来区分
    // 为了简化，我们添加一个 action 属性
    const action = materialSelector.value.action || 'voice' // 'voice' | 'bgm'
    
    if (action === 'voice') {
      // 设置为配音
      newTimeline.voice = { materialId: Number(materialId) }
      
      // 保存到本地状态（用于处理 props 更新延迟）
      localVoiceState.value = { materialId: Number(materialId) }
      
      emit('update-timeline', newTimeline)
      ElMessage.success('已设置为配音')
      
      // 先关闭模态框，确保 DOM 元素可用
      closeMaterialSelector()
      
      // 使用新的 timeline 直接渲染，不等待 props 更新
      
      // 等待模态框关闭和 DOM 更新
      nextTick(() => {
        try {
          renderSelectedVoiceWithTimeline(newTimeline)
        } catch (error) {
        }
        
        // 延迟一下再检查 props 是否更新，如果更新了才重新渲染
        // 这样可以避免覆盖正确的渲染结果
        setTimeout(() => {
          // 只有当 props.timeline.voice 确实更新了才重新渲染
          if (props.timeline?.voice?.materialId === newTimeline.voice.materialId) {
            nextTick(() => {
              renderSelectedVoice()
            })
          } else {
            // 如果 props 还没更新，再次使用 newTimeline 渲染
            renderSelectedVoiceWithTimeline(newTimeline)
          }
        }, 300)
      })
    } else if (action === 'bgm') {
      // 设置为BGM
      newTimeline.bgm = { materialId: Number(materialId) }
      emit('update-timeline', newTimeline)
      ElMessage.success('已设置为BGM')
      
      // 先关闭模态框，确保 DOM 元素可用
      closeMaterialSelector()
      
      // 使用新的 timeline 直接渲染，不等待 props 更新
      nextTick(() => {
        renderSelectedBgmWithTimeline(newTimeline)
        
        // 延迟一下再使用 nextTick 确保渲染（等待 props 更新后）
        setTimeout(() => {
          nextTick(() => {
            renderSelectedBgm()
          })
        }, 200)
      })
    }
  }
  
  // 如果不是在函数内部关闭的，则关闭模态框
  if (materialSelector.value.show) {
    closeMaterialSelector()
  }
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// 获取素材的友好显示名称
function getMaterialDisplayName(material) {
  if (!material) return `素材 #${material?.id || '?'}`
  
  let name = material.name || ''
  
  // 如果名称是UUID格式或者看起来像随机字符串，尝试从路径中提取信息
  if (!name || name.length > 50 || /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(name)) {
    // 尝试从路径中提取文件名
    if (material.path) {
      const pathParts = material.path.split('/')
      const fileName = pathParts[pathParts.length - 1]
      if (fileName && fileName !== name) {
        // 移除UUID前缀（如果有）
        const cleanName = fileName.replace(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\./i, '')
        if (cleanName !== fileName) {
          name = cleanName.replace(/\.[^.]+$/, '') // 移除扩展名
        } else {
          name = fileName.replace(/\.[^.]+$/, '') // 移除扩展名
        }
      }
    }
  }
  
  // 如果还是没有名称，使用ID
  if (!name || name.length === 0) {
    name = `素材 #${material.id}`
  }
  
  // 限制显示长度
  if (name.length > 40) {
    name = name.substring(0, 37) + '...'
  }
  
  return name
}

// 格式化素材时间
function formatMaterialTime(timeStr) {
  if (!timeStr) return ''
  try {
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now - date
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) {
      const hours = Math.floor(diff / (1000 * 60 * 60))
      if (hours === 0) {
        const minutes = Math.floor(diff / (1000 * 60))
        return minutes <= 0 ? '刚刚' : `${minutes}分钟前`
      }
      return `${hours}小时前`
    } else if (days === 1) {
      return '昨天'
    } else if (days < 7) {
      return `${days}天前`
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    }
  } catch {
    return timeStr
  }
}

// 预览素材（音频试听）
function previewMaterial(material) {
  if (!material || !material.path) return
  if (!isMaterialReady(material)) {
    ElMessage.info('素材未就绪，暂不可试听')
    return
  }
  
  // 构建音频URL
  let audioUrl = material.path
  if (!audioUrl.startsWith('/') && !audioUrl.startsWith('http')) {
    audioUrl = '/uploads/' + audioUrl.replace(/^uploads\//, '')
  }
  
  // 打开音频预览模态框
  openAudioModal(material.name || '音频预览', 'audio', audioUrl)
}

async function handleSubPreview() {
  // 检查配音是否存在
  let voice = props.timeline?.voice
  let voiceId = voice?.materialId
  
  // 如果 props.timeline.voice 为空，尝试从本地状态获取（可能是更新延迟）
  if (!voiceId && localVoiceState.value) {
    voice = localVoiceState.value
    voiceId = localVoiceState.value.materialId
  }
  
  if (!voiceId) {
    ElMessage.warning('请先生成配音并设为配音轨（用于取时长）')
    return
  }

  // 获取文案：优先使用当前文案，如果为空则自动从音频识别
  let text = getTtsText(500)
  if (!text) {
    // 如果文案为空，自动从音频识别（不需要用户手动输入）
    ElMessage.info('正在从配音音频中识别文字...')
  }

  try {
    // 如果文案为空，启用自动识别
    const autoRecognize = !text || text.trim().length === 0
    
    const response = await aiApi.generateSubtitle({
      text: text || '',  // 即使为空也传递，后端会处理
      audio_material_id: voiceId,
      auto_recognize: autoRecognize  // 如果文案为空，自动从音频识别
    })

    if (response.code === 200) {
      const url = response.data?.preview_url
      const recognizedTextFromApi = response.data?.recognized_text
      
      // 如果是从音频识别的文字，保存到文案中
      if (recognizedTextFromApi) {
        copyForm.value.output = recognizedTextFromApi
        recognizedText.value = recognizedTextFromApi  // 保存到ref中用于显示预览
        ElMessage.success(`已从配音识别出 ${recognizedTextFromApi.length} 字，并生成字幕`)
      }
      
      if (url) {
        subtitleUrl.value = url
        // 自动勾选字幕启用复选框
        editForm.value.subtitleEnabled = true
        if (!recognizedTextFromApi) {
          ElMessage.success('字幕已生成，已自动启用字幕')
        }
      } else {
        ElMessage.warning('缺少字幕预览链接')
      }
    } else {
      ElMessage.error(`字幕生成失败：${response.message || '未知错误'}`)
    }
  } catch (error) {
    ElMessage.error(`字幕生成失败：${error.message || '未知错误'}`)
  }
}

async function handleGenerate() {
  const rawClips = props.timeline?.clips || []
  if (rawClips.length === 0) {
    alert('请至少选择一个视频素材')
    return
  }

  generateLoading.value = true
  progress.value = { show: true, value: 0, text: '正在创建任务…' }

  try {
    const clipsPayload = rawClips.map(c => {
      const type = (c.type || 'video')
      const materialId = Number(c.materialId)
      if (type === 'image') {
        const d = Number(c.duration)
        if (!Number.isFinite(d) || d < 0.5 || d > 30) {
          throw new Error('图片时长需在 0.5–30 秒之间')
        }
        return { type: 'image', materialId, duration: d }
      }
      return { type: 'video', materialId }
    })

    const legacyVideoIds = clipsPayload.filter(c => c.type === 'video').map(c => c.materialId)
    
    // 获取配音ID：优先从 props.timeline 获取，如果为空则从本地状态获取（处理 props 更新延迟）
    let voiceId = props.timeline?.voice?.materialId || null
    if (!voiceId && localVoiceState.value) {
      voiceId = localVoiceState.value.materialId
    }
    
    const bgmId = props.timeline?.bgm?.materialId || null
    const speed = editForm.value.speed || 1.0
    
    // 字幕路径：如果已生成字幕预览，自动包含（即使未勾选复选框）
    // 如果用户明确勾选了复选框，则使用复选框状态；否则，如果有字幕预览，自动包含
    // 修复：只有当 subtitleUrl 有值且不为空字符串时才使用
    const subtitlePath = subtitleUrl.value && subtitleUrl.value.trim() ? subtitleUrl.value : null
    if (editForm.value.subtitleEnabled && !subtitlePath) {
      ElMessage.warning('字幕已启用但未生成字幕文件，请先生成字幕预览')
    }
    
    // BGM音量：前端是0-100的百分比，后端需要0-1的小数
    const bgmVolume = (editForm.value.bgmVolume || 60) / 100.0
    // 配音音量：默认100%（1.0）
    const voiceVolume = 1.0

    const response = await editorApi.editVideoAsync({
      clips: clipsPayload,
      video_ids: legacyVideoIds,
      voice_id: voiceId,
      bgm_id: bgmId,
      speed,
      subtitle_path: subtitlePath,
      bgm_volume: bgmVolume,
      voice_volume: voiceVolume
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

  if (pollTimeoutId) {
    clearTimeout(pollTimeoutId)
    pollTimeoutId = null
  }

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
          pollTimeoutId = setTimeout(poll, 1000)
        }
      } else {
        attempts++
        pollTimeoutId = setTimeout(poll, 1000)
      }
    } catch (error) {
      attempts++
      pollTimeoutId = setTimeout(poll, 1000)
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
function renderSelectedVideos(timelineToUse = null) {
  if (!selectedVideos.value) return
  const box = selectedVideos.value
  box.innerHTML = ''

  // 使用传入的 timeline 或 props.timeline
  const timeline = timelineToUse || props.timeline
  const clips = (timeline?.clips || []).map(c => {
    const type = c.type || 'video'
    if (type === 'image') {
      return { ...c, type: 'image', duration: Number(c.duration ?? defaultImageDuration.value ?? 2.0) }
    }
    return { ...c, type: 'video' }
  })
  if (!clips.length) {
    box.innerHTML = '<div class="empty-state"><svg class="empty-icon" viewBox="0 0 24 24" fill="none"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><div class="empty-text">尚未选择视频素材</div><div class="empty-hint">去"云素材库 → 视频素材库"点击"添加到剪辑轨道"来选择素材</div></div>'
    return
  }

  const bulk = document.createElement('div')
  bulk.style.display = 'flex'
  bulk.style.gap = '8px'
  bulk.style.alignItems = 'center'
  bulk.style.marginBottom = '8px'
  bulk.innerHTML = `
    <span style="color:#666">图片时长(秒)</span>
    <input data-bulk="dur" type="number" min="0.5" max="30" step="0.1" value="${Number(defaultImageDuration.value || 2.0)}" style="width:90px" />
    <button data-bulk="apply" class="btn">批量设置</button>
  `
  bulk.querySelector('[data-bulk="dur"]').onchange = (e) => {
    const v = Number(e.target.value)
    if (Number.isFinite(v)) defaultImageDuration.value = v
  }
  bulk.querySelector('[data-bulk="apply"]').onclick = () => {
    const v = Number(defaultImageDuration.value || 2.0)
    if (!Number.isFinite(v) || v < 0.5 || v > 30) {
      ElMessage.warning('图片时长需在 0.5–30 秒之间')
      return
    }
    const newTimeline = { ...(timelineToUse || props.timeline) }
    newTimeline.clips = (newTimeline.clips || []).map(c => {
      if ((c.type || 'video') === 'image') return { ...c, type: 'image', duration: v }
      return c
    })
    emit('update-timeline', newTimeline)
    nextTick(() => {
      renderSelectedVideos(newTimeline)
    })
  }
  box.appendChild(bulk)

  clips.forEach((clip, idx) => {
    const name = materialNameById(clip.materialId)
    const chip = document.createElement('div')
    chip.className = 'chip'
    const kind = clip.type === 'image' ? '图片' : '视频'
    chip.innerHTML = `
      <b>${idx + 1}</b>
      <span>${escapeHtml(name)} <em style="color:#999;font-style:normal">(${kind})</em></span>
      <button class="x" title="上移" data-action="up">↑</button>
      <button class="x" title="下移" data-action="down">↓</button>
      <button class="x" title="移除" data-action="remove">×</button>
    `
    
    if (clip.type === 'image') {
      const input = document.createElement('input')
      input.type = 'number'
      input.min = '0.5'
      input.max = '30'
      input.step = '0.1'
      input.value = String(Number(clip.duration ?? defaultImageDuration.value ?? 2.0))
      input.style.width = '80px'
      input.style.marginLeft = '8px'
      input.title = '图片时长(秒)'
      input.onchange = () => {
        const v = Number(input.value)
        if (!Number.isFinite(v) || v < 0.5 || v > 30) {
          ElMessage.warning('图片时长需在 0.5–30 秒之间')
          input.value = String(Number(clip.duration ?? defaultImageDuration.value ?? 2.0))
          return
        }
        const newTimeline = { ...(timelineToUse || props.timeline) }
        newTimeline.clips = (newTimeline.clips || []).map(x => {
          if (x.id === clip.id) return { ...x, type: 'image', duration: v }
          return x
        })
        emit('update-timeline', newTimeline)
        nextTick(() => {
          renderSelectedVideos(newTimeline)
        })
      }
      chip.appendChild(input)
    }

    chip.querySelector('[data-action="up"]').onclick = () => {
      if (idx <= 0) return
      const newTimeline = { ...(timelineToUse || props.timeline) }
      const arr = newTimeline.clips
      ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
      emit('update-timeline', newTimeline)
      // 立即使用新的 timeline 更新 UI
      nextTick(() => {
        renderSelectedVideos(newTimeline)
      })
    }
    
    chip.querySelector('[data-action="down"]').onclick = () => {
      const newTimeline = { ...(timelineToUse || props.timeline) }
      const arr = newTimeline.clips
      if (idx >= arr.length - 1) return
      ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
      emit('update-timeline', newTimeline)
      // 立即使用新的 timeline 更新 UI
      nextTick(() => {
        renderSelectedVideos(newTimeline)
      })
    }
    
    chip.querySelector('[data-action="remove"]').onclick = () => {
      const newTimeline = { ...(timelineToUse || props.timeline) }
      newTimeline.clips = newTimeline.clips.filter(c => c.id !== clip.id)
      emit('update-timeline', newTimeline)
      // 立即使用新的 timeline 更新 UI
      nextTick(() => {
        renderSelectedVideos(newTimeline)
      })
    }
    
    box.appendChild(chip)
  })
}

// 使用指定的 timeline 渲染BGM（用于立即更新，不等待 props）
function renderSelectedBgmWithTimeline(timeline) {
  if (!selectedBgm.value) return
  const box = selectedBgm.value
  box.innerHTML = ''

  const bgm = timeline?.bgm
  if (!bgm || !bgm.materialId) {
    box.innerHTML = '<div class="label">未选择 BGM（可不选）。</div>'
    return
  }

  const name = materialNameById(bgm.materialId)
  const chip = document.createElement('div')
  chip.className = 'chip'
  chip.innerHTML = `<b>BGM</b><span>${escapeHtml(name)}</span><button class="x" title="移除">×</button>`
  chip.querySelector('.x').onclick = () => {
    const newTimeline = { ...timeline }
    newTimeline.bgm = null
    emit('update-timeline', newTimeline)
  }
  box.appendChild(chip)
}

function renderSelectedBgm() {
  if (!selectedBgm.value) return
  const box = selectedBgm.value
  box.innerHTML = ''

  const bgm = props.timeline?.bgm
  if (!bgm || !bgm.materialId) {
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

// 使用指定的 timeline 渲染配音（用于立即更新，不等待 props）
function renderSelectedVoiceWithTimeline(timeline) {
  
  if (!selectedVoice.value) {
    // 如果 ref 还没有初始化，等待 nextTick
    nextTick(() => {
      if (selectedVoice.value) {
        renderSelectedVoiceWithTimeline(timeline)
      } else {
      }
    })
    return
  }
  
  const box = selectedVoice.value
  box.innerHTML = ''

  const voice = timeline?.voice
  
  if (!voice || !voice.materialId) {
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

function renderSelectedVoice() {
  if (!selectedVoice.value) {
    return
  }
  const box = selectedVoice.value
  box.innerHTML = ''

  const voice = props.timeline?.voice
  
  if (!voice || !voice.materialId) {
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
    } else if (tab === 'history') {
      loadHistoryTasks()
    }
  })
}

// 历史任务相关函数
async function loadHistoryTasks() {
  historyLoading.value = true
  try {
    const response = await editorApi.getTasks({ limit: 100 })
    if (response.code === 200) {
      historyTasks.value = response.data || []
    }
  } catch (error) {
  } finally {
    historyLoading.value = false
  }
}

function getTaskStatusText(status) {
  const statusMap = {
    'pending': '等待中',
    'running': '进行中',
    'success': '成功',
    'fail': '失败'
  }
  return statusMap[status] || status
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return timeStr
  }
}

function previewTask(task) {
  if (task.preview_url) {
    window.open(task.preview_url, '_blank')
  }
}

function downloadTask(task) {
  if (task.preview_url) {
    const link = document.createElement('a')
    link.href = task.preview_url
    link.download = task.output_filename || 'video.mp4'
    link.click()
  }
}

async function deleteTask(task) {
  if (!confirm(`确定要删除任务 #${task.id} 吗？`)) {
    return
  }
  
  try {
    const response = await editorApi.deleteTask(task.id, true)
    if (response.code === 200) {
      await loadHistoryTasks()
      alert('删除成功')
    } else {
      alert(response.message || '删除失败')
    }
  } catch (error) {
    alert('删除失败: ' + (error.message || '未知错误'))
  }
}

// 音频预览模态框相关方法
function openAudioModal(title, kind, url) {
  if (!url) {
    ElMessage.error('预览地址无效')
    return
  }
  
  // 重置关闭标志
  isClosingModal.value = false
  
  // 确保 URL 是完整的（如果是相对路径，添加基础路径）
  let fullUrl = url
  if (url.startsWith('/')) {
    // 相对路径，直接使用（会被代理处理）
    fullUrl = url
  } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
    // 可能是相对路径但没有前导斜杠
    fullUrl = '/' + url
  }
  
  audioModal.value = { show: true, title, kind, url: fullUrl }
  
  // 对于音频，等待模态框渲染完成后尝试自动播放
  if (kind === 'audio') {
    nextTick(() => {
      setTimeout(() => {
        if (modalAudio.value) {
          const audio = modalAudio.value
          
          // 清除之前的事件监听器（但保留模板中的 @error 事件）
          // 注意：模板中已经有 @error="handleAudioError"，所以这里不需要设置 onerror
          audio.onloadeddata = null
          audio.oncanplay = null
          audio.onloadedmetadata = null
          
          // 明确设置音频源
          audio.src = fullUrl
          
          // 设置音量（确保不是静音）
          audio.volume = 1.0
          audio.muted = false
          
          // 当音频可以播放时，尝试自动播放
          audio.oncanplay = () => {
            // 如果正在关闭，不处理
            if (isClosingModal.value) return
            
            audio.volume = 1.0
            audio.muted = false
            // 尝试自动播放（在用户交互上下文中）
            audio.play().then(() => {
            }).catch((err) => {
            })
          }
          
          // 当数据加载完成时也尝试播放
          audio.onloadeddata = () => {
            // 如果正在关闭，不处理
            if (isClosingModal.value) return
            
            audio.volume = 1.0
            audio.muted = false
            if (audio.readyState >= 2) {
              audio.play().then(() => {
              }).catch(() => {
              })
            }
          }
          
          // 强制加载音频
          audio.load()
        } else {
        }
      }, 150)
    })
  }
}

async function closeAudioModal() {
  // 设置关闭标志，防止在关闭过程中触发错误事件
  isClosingModal.value = true
  
  // 如果是临时TTS文件（路径包含 /tts/），关闭时删除
  const currentUrl = audioModal.value.url
  if (audioModal.value.kind === 'audio' && currentUrl) {
    // 检查是否是临时TTS文件（路径包含 /tts/ 或 /uploads/tts/）
    // 后端要求 URL 必须以 /uploads/tts/ 开头
    let deleteUrl = currentUrl
    
    // 如果 URL 包含 /tts/ 但不是以 /uploads/tts/ 开头，尝试转换
    if (currentUrl.includes('/tts/') && !currentUrl.startsWith('/uploads/tts/')) {
      // 提取文件名部分
      const parts = currentUrl.split('/tts/')
      if (parts.length > 1) {
        const filename = parts[1].split('?')[0] // 移除查询参数
        deleteUrl = `/uploads/tts/${filename}`
      }
    }
    
    // 检查是否是临时TTS文件（必须以 /uploads/tts/ 开头，文件名以 tts_ 开头）
    const isTempTts = deleteUrl.startsWith('/uploads/tts/') && 
                      deleteUrl.includes('tts_') && 
                      deleteUrl.endsWith('.mp3')
    
    if (isTempTts) {
      try {
        const response = await aiApi.deleteTempTts(deleteUrl)
        if (response.code === 200) {
        } else {
        }
        // 静默删除，不显示成功消息（避免干扰用户体验）
      } catch (error) {
        // 删除失败也不影响关闭模态框，只记录错误
      }
    } else {
    }
  }
  
  // 先移除所有事件监听器，然后再清理资源
  if (modalAudio.value) {
    // 暂停播放
    try {
      modalAudio.value.pause()
    } catch (e) {
      // 忽略暂停错误
    }
    
    // 移除所有事件监听器
    modalAudio.value.onerror = null
    modalAudio.value.onloadeddata = null
    modalAudio.value.oncanplay = null
    modalAudio.value.onloadedmetadata = null
    
    // 清空音频源
    modalAudio.value.src = ''
    
    // 强制停止加载
    try {
      modalAudio.value.load()
    } catch (e) {
      // 忽略加载错误
    }
  }
  
  // 重置模态框状态
  audioModal.value = { show: false, title: '', kind: '', url: '' }
  
  // 延迟重置关闭标志，确保所有事件都已处理
  setTimeout(() => {
    isClosingModal.value = false
  }, 100)
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
  // 如果正在关闭模态框，不显示错误消息
  if (isClosingModal.value) {
    return
  }
  
  // 检查是否是真正的错误（而不是因为关闭导致的）
  if (modalAudio.value && modalAudio.value.error) {
    const error = modalAudio.value.error
    let errorMsg = '音频加载失败'
    
    if (error.code === error.MEDIA_ERR_ABORTED) {
      // 加载被中止（可能是用户关闭了模态框），不显示错误
      return
    } else if (error.code === error.MEDIA_ERR_NETWORK) {
      errorMsg = '网络错误，无法加载音频'
    } else if (error.code === error.MEDIA_ERR_DECODE) {
      errorMsg = '音频解码失败'
    } else if (error.code === error.MEDIA_ERR_SRC_NOT_SUPPORTED) {
      errorMsg = '音频格式不支持或文件不存在'
    }
    
    ElMessage.error(errorMsg)
  }
}

function handleMaskClick(e) {
  if (e.target.classList.contains('mask')) {
    closeAudioModal()
  }
}

// 监听时间线变化
watch(() => props.timeline, (newTimeline, oldTimeline) => {
  
  // 检查是否是配音变化
  const voiceChanged = (newTimeline?.voice?.materialId !== oldTimeline?.voice?.materialId)
  const bgmChanged = (newTimeline?.bgm?.materialId !== oldTimeline?.bgm?.materialId)
  const clipsChanged = JSON.stringify(newTimeline?.clips) !== JSON.stringify(oldTimeline?.clips)
  
  // 同步本地状态（当 props 更新时）
  if (newTimeline?.voice) {
    localVoiceState.value = { materialId: newTimeline.voice.materialId }
  } else if (!newTimeline?.voice && oldTimeline?.voice) {
    // 如果配音被移除，也清除本地状态
    localVoiceState.value = null
  }
  
  // 无论当前在哪个标签页，都更新渲染（因为用户可能在其他标签页添加素材）
  nextTick(() => {
    if (clipsChanged) {
      renderSelectedVideos()
    }
    if (bgmChanged) {
      renderSelectedBgm()
    }
    if (voiceChanged) {
      renderSelectedVoice()
    }
  })
}, { deep: true, immediate: false })

// 监听素材列表变化，更新音频配置显示和素材选择器
watch(() => props.materials, () => {
  if (aiTab.value === 'edit') {
    nextTick(() => {
      renderSelectedBgm()
      renderSelectedVoice()
    })
  }
  
  // 如果素材选择器已打开，更新过滤列表
  if (materialSelector.value.show) {
    filterMaterials()
  }
}, { deep: true })

// 监听有效素材列表变化
watch(effectiveMaterials, () => {
  // 如果素材选择器已打开，更新过滤列表
  if (materialSelector.value.show) {
    filterMaterials()
  }
}, { deep: true })

// 初始化
onMounted(async () => {
  const savedTab = localStorage.getItem('ve.aiTab') || 'copy'
  setAiTab(savedTab)
  
  // 加载 TTS 音色列表
  aiApi.getTtsVoices().then(response => {
    if (response.code === 200) {
      const list = Array.isArray(response.data) ? response.data : []
      if (list.length > 0) {
        ttsVoices.value = list

        const current = Number(ttsForm.value.voice)
        const hasCurrent = ttsVoices.value.some(v => Number(v.id) === current)
        if (!hasCurrent) {
          ttsForm.value.voice = Number(ttsVoices.value[0]?.id ?? 0)
        }
      }
    }
  }).catch(() => {})
  
  // 如果 props.materials 为空，尝试自己加载素材
  if (!props.materials || props.materials.length === 0) {
    await loadMaterials()
  }
  
  // 初始渲染音频配置
  nextTick(() => {
    if (aiTab.value === 'edit') {
      renderSelectedVideos()
      renderSelectedBgm()
      renderSelectedVoice()
    }
  })
})

onBeforeUnmount(() => {
  if (pollTimeoutId) {
    clearTimeout(pollTimeoutId)
    pollTimeoutId = null
  }
})
</script>

<style scoped>
/* 复用父组件的样式 */
/* aiStep 的显示由 v-show 控制，不需要 CSS display 属性 */

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

.subtitle-preview {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.subtitle-preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.subtitle-icon {
  width: 18px;
  height: 18px;
  color: #1677ff;
}

.subtitle-preview-title {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
  flex: 1;
}

.subtitle-status-badge {
  padding: 4px 8px;
  background: #52c41a;
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.subtitle-text-preview {
  margin-bottom: 12px;
}

.subtitle-text-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}

.subtitle-text-content {
  font-size: 13px;
  color: #2c3e50;
  line-height: 1.6;
  padding: 10px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e9ecef;
  max-height: 120px;
  overflow-y: auto;
}

.subtitle-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.subtitle-file-label {
  font-weight: 500;
}

.subtitle-file-name {
  color: #1677ff;
  font-family: monospace;
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

/* 历史任务样式 */
.history-task-item {
  transition: all 0.2s;
}

.history-task-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.task-success {
  border-left: 4px solid #52c41a;
}

.task-fail {
  border-left: 4px solid #f56c6c;
}

.task-running {
  border-left: 4px solid #1677ff;
}

.status-success {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.status-fail {
  background: #fff2f0;
  color: #f56c6c;
  border: 1px solid #ffccc7;
}

.status-running {
  background: #e6f7ff;
  color: #1677ff;
  border: 1px solid #91d5ff;
}

.status-pending {
  background: #fafafa;
  color: #8a94a3;
  border: 1px solid #d9d9d9;
}

/* 步骤导航样式 */
.steps-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  margin-bottom: 24px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  flex: 1;
  max-width: 200px;
}

.step-item:hover {
  background: #f8f9fa;
}

.step-item.active {
  background: rgba(22, 119, 255, 0.1);
  border: 2px solid rgba(22, 119, 255, 0.3);
}

.step-item.completed {
  background: rgba(82, 196, 26, 0.1);
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e0e0e0;
  color: #8a94a3;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 14px;
  flex-shrink: 0;
  transition: all 0.2s;
}

.step-number.step-icon {
  background: transparent;
  border: 2px solid #e0e0e0;
}

.step-number.step-icon svg {
  width: 18px;
  height: 18px;
}

.step-item.active .step-number.step-icon {
  border-color: #1677ff;
  color: #1677ff;
}

.step-item.active .step-number {
  background: #1677ff;
  color: #fff;
}

.step-item.completed .step-number {
  background: #52c41a;
  color: #fff;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 2px;
}

.step-desc {
  font-size: 12px;
  color: #8a94a3;
}

.step-item.active .step-title {
  color: #1677ff;
}

.step-check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #52c41a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-check svg {
  width: 12px;
  height: 12px;
}

.step-connector {
  width: 40px;
  height: 2px;
  background: #e0e0e0;
  flex-shrink: 0;
}

/* 步骤容器样式 */
.step-container {
  max-width: 980px;
  margin: 0 auto;
}

.step-header {
  text-align: center;
  margin-bottom: 32px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(22, 119, 255, 0.05) 0%, rgba(22, 119, 255, 0.02) 100%);
  border-radius: 12px;
}

.step-title {
  font-size: 24px;
  font-weight: 800;
  color: #2c3e50;
  margin-bottom: 8px;
}

.step-subtitle {
  font-size: 14px;
  color: #8a94a3;
  margin: 0;
}

.step-panel {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 表单样式优化 */
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-field.full-width {
  grid-column: 1 / -1;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
}

.label-text {
  color: #2c3e50;
}

.label-required {
  color: #f56c6c;
}

.label-optional {
  color: #8a94a3;
  font-weight: 400;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  transition: all 0.2s;
  background: #fff;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #1677ff;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.1);
}

.form-textarea {
  min-height: 120px;
  resize: vertical;
}

.field-tip {
  font-size: 12px;
  color: #8a94a3;
  margin-top: 4px;
}

.tip-warning {
  color: #ff7a00;
}

.form-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-large {
  padding: 14px 24px;
  font-size: 15px;
  font-weight: 600;
}

.btn-primary {
  background: #1677ff;
  border-color: #1677ff;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #0f66e2;
  border-color: #0f66e2;
}

.btn-secondary {
  background: #fff;
  border-color: #e0e0e0;
  color: #2c3e50;
}

.btn-secondary:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #d0d0d0;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 文案选项卡片 */
.copy-options {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.copy-option-card {
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.copy-option-card:hover {
  border-color: #1677ff;
  background: rgba(22, 119, 255, 0.02);
}

.copy-option-card.active {
  border-color: #1677ff;
  background: rgba(22, 119, 255, 0.08);
}

.option-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.option-title {
  font-weight: 600;
  color: #2c3e50;
  font-size: 14px;
}

.option-badge {
  padding: 2px 8px;
  background: #1677ff;
  color: #fff;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.option-preview {
  font-size: 13px;
  color: #6b7785;
  line-height: 1.6;
}

/* 文案预览框 */
.copy-preview-box {
  padding: 16px;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  min-height: 100px;
}

.copy-text {
  font-size: 14px;
  line-height: 1.8;
  color: #2c3e50;
  white-space: pre-wrap;
  word-break: break-word;
}

.copy-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e0e0e0;
  font-size: 12px;
  color: #8a94a3;
}

.btn-link {
  background: none;
  border: none;
  color: #1677ff;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
  text-decoration: underline;
}

.btn-link:hover {
  color: #0f66e2;
}

/* 空状态警告 */
.empty-state-warning {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
  margin-bottom: 20px;
}

.warning-icon {
  width: 32px;
  height: 32px;
  color: #ff7a00;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 4px;
}

.warning-desc {
  font-size: 13px;
  color: #8a94a3;
  margin-bottom: 12px;
}

/* 步骤底部 */
.step-footer {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.footer-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #8a94a3;
  flex: 1;
}

.footer-tip.success {
  color: #52c41a;
}

.tip-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* 生成面板优化 */
.generate-panel {
  background: linear-gradient(135deg, rgba(22, 119, 255, 0.05) 0%, rgba(22, 119, 255, 0.02) 100%);
  border: 2px solid rgba(22, 119, 255, 0.2);
}

.generate-content {
  text-align: center;
}

.generate-header {
  margin-bottom: 24px;
}

.generate-title {
  font-size: 20px;
  font-weight: 800;
  color: #2c3e50;
  margin-bottom: 8px;
}

.generate-desc {
  font-size: 14px;
  color: #8a94a3;
  margin: 0;
}

.btn-generate {
  padding: 16px 32px;
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, #1677ff 0%, #0f66e2 100%);
  border: none;
  color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.3);
  transition: all 0.2s;
}

.btn-generate:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(22, 119, 255, 0.4);
}

.btn-generate.disabled {
  background: #d0d0d0;
  box-shadow: none;
  cursor: not-allowed;
}

.generate-warning {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
  color: #ff7a00;
  font-size: 13px;
}

.generate-warning .warning-icon {
  width: 18px;
  height: 18px;
}

/* 上传按钮优化 */
.upload-btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px dashed #d0d0d0;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  color: #2c3e50;
}

.upload-btn-secondary:hover {
  border-color: #1677ff;
  background: rgba(22, 119, 255, 0.02);
  color: #1677ff;
}

/* 预览容器优化 */
.preview-container {
  margin-top: 16px;
}

.preview-video {
  width: 100%;
  max-height: 500px;
  border-radius: 8px;
  background: #000;
  margin-bottom: 16px;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  background: #f8f9fa;
  border: 2px dashed #e0e0e0;
  border-radius: 8px;
  padding: 40px;
}

.placeholder-icon {
  width: 64px;
  height: 64px;
  color: #d0d0d0;
  margin-bottom: 16px;
}

.placeholder-text {
  font-size: 16px;
  font-weight: 600;
  color: #8a94a3;
  margin-bottom: 8px;
}

.placeholder-desc {
  font-size: 13px;
  color: #b0b0b0;
}

.preview-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

/* 音频预览模态框样式 */
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

.modal-close:hover {
  color: #2c3e50;
}

.modal-body {
  padding: 14px;
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

.audio-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f0f7ff;
  border-radius: 8px;
  font-size: 13px;
  color: #1677ff;
}

.hint-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: #1677ff;
}

/* 素材选择器样式 */
.material-selector-modal {
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.material-selector-search {
  margin-bottom: 16px;
}

.material-selector-search .input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
}

.material-selector-list {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 8px;
}

.material-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 8px;
  border: 2px solid transparent;
}

.material-item:hover {
  background: #f8f9fa;
}

.material-item.selected {
  background: #f0f7ff;
  border-color: #1677ff;
}

.material-item.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.material-item.disabled:hover {
  background: transparent;
}

.material-info {
  flex: 1;
}

.material-name {
  font-size: 14px;
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 4px;
}

.material-meta {
  font-size: 12px;
  color: #8a94a3;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.material-status {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.06);
  color: #2c3e50;
}

.material-status.status-processing {
  background: rgba(255, 122, 0, 0.12);
  color: #c35d00;
}

.material-status.status-failed {
  background: rgba(220, 53, 69, 0.12);
  color: #c82333;
}

.material-preview {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 4px 8px;
  background: #f0f7ff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  width: fit-content;
  font-size: 12px;
  color: #1677ff;
}

.material-preview:hover {
  background: #e6f4ff;
}

.preview-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.check-icon {
  width: 20px;
  height: 20px;
  color: #1677ff;
  flex-shrink: 0;
}

.empty-materials {
  text-align: center;
  padding: 40px 20px;
  color: #8a94a3;
}

.empty-text {
  font-size: 14px;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 12px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>

