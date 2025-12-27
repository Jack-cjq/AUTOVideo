<template>
  <div class="login-helper-container">
    <el-card>
      <template #header>
        <h2>🎬 抖音账号登录助手</h2>
      </template>

      <div v-if="!accountId" class="error-message">
        <el-alert type="error" :closable="false">
          <template #title>错误：缺少账号ID参数</template>
        </el-alert>
      </div>

      <div v-else>
        <!-- 步骤 1: 打开抖音登录页面 -->
        <div class="step" :class="{ hidden: currentStep < 1 }">
          <h3>步骤 1: 打开抖音登录页面</h3>
          <p>点击下面的按钮，将在新窗口中打开抖音创作者中心登录页面。</p>
          <el-button type="primary" @click="openLoginPage" :disabled="loginWindowOpen">
            {{ loginWindowOpen ? '已打开登录页面' : '打开抖音登录页面' }}
          </el-button>
        </div>

        <!-- 步骤 2: 完成登录 -->
        <div class="step" :class="{ hidden: currentStep < 2 }">
          <h3>步骤 2: 完成登录</h3>
          <p>在新打开的窗口中完成抖音登录（手机号登录或扫码登录）。</p>
          <p class="tip">登录完成后，请继续下一步。</p>
        </div>

        <!-- 步骤 3: 提取 Cookies -->
        <div class="step" :class="{ hidden: currentStep < 3 }">
          <h3>步骤 3: 提取 Cookies</h3>
          <p>登录完成后，请按照以下步骤提取 cookies：</p>
          
          <el-tabs v-model="extractMethod" style="margin: 15px 0;">
            <el-tab-pane label="方法1: 从 Network 标签页获取（推荐）" name="network">
              <el-alert type="success" :closable="false" style="margin: 10px 0;">
                <template #title>
                  <strong>✅ 推荐方法：可以获取所有 cookies（包括 HttpOnly）</strong>
                </template>
              </el-alert>
              <ol style="margin-left: 20px; margin-top: 10px; line-height: 2;">
                <li>在新打开的抖音登录窗口中，按 <strong>F12</strong> 打开开发者工具</li>
                <li>切换到 <strong>Network（网络）</strong> 标签页</li>
                <li>刷新页面或执行任意操作（如点击某个按钮）</li>
                <li>在 Network 标签页中找到任意一个请求（如 <code>creator.douyin.com</code> 的请求）</li>
                <li>点击该请求，查看右侧的 <strong>Headers</strong> 标签</li>
                <li>在 <strong>Request Headers</strong> 部分，找到 <strong>Cookie:</strong> 这一行</li>
                <li>复制完整的 Cookie 值（通常很长，包含很多 cookies）</li>
                <li>切换到 <strong>Console（控制台）</strong> 标签页</li>
                <li>先执行下面的提取代码（获取 localStorage 等）</li>
                <li>然后在控制台输入：<code>parseCookieHeader("粘贴的Cookie值")</code></li>
                <li>最后输入：<code>copyCookiesData()</code> 或查看输出的 JSON</li>
                <li>复制完整的 JSON 数据，粘贴到下面的文本框中提交</li>
              </ol>
            </el-tab-pane>
            
            <el-tab-pane label="方法2: 从 Console 获取（不完整）" name="console">
              <el-alert type="warning" :closable="false" style="margin: 10px 0;">
                <template #title>
                  <strong>⚠️ 注意：此方法只能获取非 HttpOnly 的 cookies，可能缺少关键的登录 cookies</strong>
                </template>
              </el-alert>
              <ol style="margin-left: 20px; margin-top: 10px; line-height: 2;">
                <li>在新打开的抖音登录窗口中，按 <strong>F12</strong> 打开开发者工具</li>
                <li>切换到 <strong>Console（控制台）</strong> 标签页</li>
                <li>复制下面的代码并粘贴到控制台中，然后按回车执行</li>
                <li>代码会自动提取 cookies 并显示在控制台中</li>
                <li>复制控制台输出的 JSON 数据，然后粘贴到下面的文本框中提交</li>
              </ol>
            </el-tab-pane>
          </el-tabs>
          
          <div class="code-block">
            <el-button 
              class="copy-btn" 
              size="small" 
              @click="copyExtractCode"
            >
              {{ copyCodeSuccess ? '已复制' : '复制代码' }}
            </el-button>
            <pre id="extractCode">{{ extractCode }}</pre>
          </div>
          
          <el-alert type="warning" :closable="false" style="margin-top: 10px;">
            <template #title>
              <strong>注意：</strong>由于浏览器安全限制，此代码只能提取部分cookies（非HttpOnly的cookies）。
              如果登录后仍然提示需要登录，可能需要使用浏览器扩展来提取完整的cookies。
            </template>
          </el-alert>
        </div>

        <!-- 步骤 4: 提交 Cookies -->
        <div class="step" :class="{ hidden: currentStep < 3 }">
          <h3>步骤 4: 提交 Cookies</h3>
          <p>将从控制台复制的 cookies 数据粘贴到下面的文本框中：</p>
          <el-input
            v-model="cookiesInput"
            type="textarea"
            :rows="10"
            placeholder="粘贴从控制台复制的 cookies JSON 数据..."
            style="margin: 10px 0;"
          />
          <el-button type="primary" @click="submitCookies" :loading="submitting">
            {{ submitting ? '提交中...' : '提交 Cookies' }}
          </el-button>
          <div v-if="submitStatus" style="margin-top: 10px;">
            <el-alert 
              :type="submitStatus.type" 
              :closable="false"
              :title="submitStatus.message"
            />
          </div>
        </div>

        <!-- 步骤 5: 登录完成 -->
        <div class="step" :class="{ hidden: currentStep < 5 }">
          <el-result icon="success" title="登录完成" sub-title="Cookies 已成功保存到服务器！">
            <template #extra>
              <el-button type="primary" @click="closeWindow">关闭窗口</el-button>
            </template>
          </el-result>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const route = useRoute()
const accountId = ref(null)
const currentStep = ref(1)
const loginWindowOpen = ref(false)
const cookiesInput = ref('')
const submitting = ref(false)
const submitStatus = ref(null)
const copyCodeSuccess = ref(false)

// 提取代码
const extractCode = `// 在抖音网站 (creator.douyin.com) 的控制台中运行此代码
// 确保您已经完成登录，并且当前在 creator.douyin.com 域名下
// 此代码会尝试获取所有 cookies（包括 HttpOnly 的 cookies）

(function() {
    try {
        const cookies = [];
        
        // 方法1: 尝试使用 Chrome DevTools Protocol (如果可用)
        // 注意：这需要浏览器支持，某些浏览器可能不支持
        let useDevToolsProtocol = false;
        
        if (typeof chrome !== 'undefined' && chrome.cookies) {
            // 浏览器扩展环境
            console.log('[+] 检测到浏览器扩展环境，使用 chrome.cookies API 获取所有 cookies...');
            useDevToolsProtocol = true;
        } else {
            // 方法2: 使用 Network 标签页的方法（推荐）
            console.log('[+] 方法1: 从 Network 标签页获取 cookies（推荐）');
            console.log('[+] 请按照以下步骤操作：');
            console.log('[+] 1. 打开开发者工具的 Network（网络）标签页');
            console.log('[+] 2. 刷新页面或执行任意操作');
            console.log('[+] 3. 找到任意一个请求（如 creator.douyin.com 的请求）');
            console.log('[+] 4. 点击该请求，查看 Request Headers');
            console.log('[+] 5. 找到 Cookie: 这一行，复制完整的 Cookie 值');
            console.log('[+] 6. 在控制台输入: parseCookieHeader("粘贴的Cookie值")');
            console.log('');
            console.log('[+] 方法2: 使用 document.cookie（只能获取非 HttpOnly 的 cookies）');
        }
        
        // 获取非 HttpOnly 的 cookies（通过 document.cookie）
        const cookieString = document.cookie;
        if (cookieString) {
            cookieString.split(';').forEach(cookie => {
                const [name, ...valueParts] = cookie.trim().split('=');
                const value = valueParts.join('=');
                if (name && value) {
                    cookies.push({
                        name: name.trim(),
                        value: value.trim(),
                        domain: '.douyin.com',
                        path: '/',
                        httpOnly: false,
                        secure: true,
                        sameSite: 'Lax'
                    });
                }
            });
        }
        
        // 提供一个函数来解析从 Network 标签页复制的 Cookie 头
        window.parseCookieHeader = function(cookieHeader) {
            if (!cookieHeader || typeof cookieHeader !== 'string') {
                console.error('❌ 请提供有效的 Cookie 头字符串');
                return null;
            }
            
            const cookiePairs = cookieHeader.split(';').map(pair => pair.trim());
            const parsedCookies = [];
            
            cookiePairs.forEach(pair => {
                const [name, ...valueParts] = pair.split('=');
                const value = valueParts.join('=');
                if (name && value) {
                    // 尝试从现有 cookies 中查找该 cookie 的完整信息
                    let cookieInfo = {
                        name: name.trim(),
                        value: value.trim(),
                        domain: '.douyin.com',
                        path: '/',
                        httpOnly: true, // 从 Network 获取的通常是 HttpOnly
                        secure: true,
                        sameSite: 'Lax'
                    };
                    
                    // 检查是否已存在（从 document.cookie 获取的）
                    const existing = cookies.find(c => c.name === cookieInfo.name);
                    if (existing) {
                        // 合并信息，保留 httpOnly 状态
                        cookieInfo = { ...existing, httpOnly: true, value: cookieInfo.value };
                        const index = cookies.findIndex(c => c.name === cookieInfo.name);
                        cookies[index] = cookieInfo;
                    } else {
                        parsedCookies.push(cookieInfo);
                    }
                }
            });
            
            // 添加新解析的 cookies
            cookies.push(...parsedCookies);
            
            console.log(\`[+] 已解析 \${parsedCookies.length} 个 cookies\`);
            console.log('[+] 现在调用 generateStorageState() 生成完整的 storage_state');
            
            return parsedCookies;
        };
        
        // 生成完整的 storage_state
        window.generateStorageState = function() {
            return generateStorageState();
        };
        
        function generateStorageState() {
            // 获取localStorage
            const localStorageData = {};
            try {
                for (let i = 0; i < window.localStorage.length; i++) {
                    const key = window.localStorage.key(i);
                    localStorageData[key] = window.localStorage.getItem(key);
                }
            } catch (e) {
                console.warn('无法读取localStorage:', e);
            }
            
            // 获取sessionStorage
            const sessionStorageData = {};
            try {
                for (let i = 0; i < window.sessionStorage.length; i++) {
                    const key = window.sessionStorage.key(i);
                    sessionStorageData[key] = window.sessionStorage.getItem(key);
                }
            } catch (e) {
                console.warn('无法读取sessionStorage:', e);
            }
            
            // 构建storage_state格式（Playwright格式）
            // localStorage 需要转换为数组格式
            const localStorageArray = Object.keys(localStorageData).length > 0 ? 
                Object.entries(localStorageData).map(([name, value]) => ({ name, value })) : [];
            
            const storageState = {
                cookies: cookies,
                origins: [{
                    origin: 'https://creator.douyin.com',
                    localStorage: localStorageArray
                }]
            };
            
            return storageState;
        }
        
        // 生成初始的 storage_state（仅包含非 HttpOnly cookies）
        let storageState = generateStorageState();
        
        console.log(\`[+] 已获取 \${cookies.length} 个 cookies（仅非 HttpOnly）\`);
        console.log('[!] 警告：可能缺少关键的 HttpOnly cookies（如 sessionid、passport_auth 等）');
        console.log('[!] 建议使用方法1从 Network 标签页获取完整的 cookies');
        console.log('');
        
        // 改进的自动复制功能（需要在用户交互上下文中调用）
        const copyToClipboard = async (text) => {
            // 方法1: 使用现代 Clipboard API（需要用户交互上下文）
            if (navigator.clipboard && navigator.clipboard.writeText) {
                try {
                    await navigator.clipboard.writeText(text);
                    return true;
                } catch (err) {
                    console.warn('Clipboard API 复制失败，尝试备用方法:', err);
                }
            }
            
            // 方法2: 使用传统的 execCommand 方法（兼容性更好）
            try {
                // 创建临时 textarea 元素
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.left = '-999999px';
                textarea.style.top = '-999999px';
                document.body.appendChild(textarea);
                
                // 选中文本
                textarea.select();
                textarea.setSelectionRange(0, text.length); // 对于移动设备
                
                // 执行复制
                const successful = document.execCommand('copy');
                document.body.removeChild(textarea);
                
                if (successful) {
                    return true;
                } else {
                    throw new Error('execCommand 复制失败');
                }
            } catch (err) {
                console.warn('execCommand 复制失败:', err);
                return false;
            }
        };
        
        // 输出JSON字符串
        const jsonStr = JSON.stringify(storageState, null, 2);
        
        // 在控制台中以更友好的方式输出
        console.log('%c=== 请复制下面的内容 ===', 'color: #409eff; font-size: 14px; font-weight: bold;');
        console.log(jsonStr);
        console.log('%c=== 复制完成 ===', 'color: #67c23a; font-size: 14px; font-weight: bold;');
        
        // 提供一个全局函数方便手动复制
        window.copyCookiesData = function() {
            return copyToClipboard(jsonStr).then(success => {
                if (success) {
                    console.log('%c✅ 已复制到剪贴板！', 'color: #67c23a; font-size: 14px; font-weight: bold;');
                    return true;
                } else {
                    console.log('%c⚠️ 复制失败，请手动选中上面的JSON数据并按 Ctrl+C 复制', 'color: #e6a23c; font-size: 14px;');
                    return false;
                }
            });
        };
        console.log('%c💡 提示：如果自动复制失败，可以在控制台输入 copyCookiesData() 手动复制', 'color: #909399; font-size: 12px;');
        
        // 尝试自动复制
        copyToClipboard(jsonStr).then(success => {
            if (success) {
                console.log('%c✅ 已自动复制到剪贴板！', 'color: #67c23a; font-size: 14px; font-weight: bold;');
                alert('✅ Cookies已提取并复制到剪贴板！\\n\\n请回到登录助手页面粘贴并提交。');
            } else {
                console.log('%c⚠️ 自动复制失败，请手动复制上面的内容', 'color: #e6a23c; font-size: 14px;');
                console.log('%c提示：您可以选中上面的JSON数据，然后按 Ctrl+C (Windows) 或 Cmd+C (Mac) 复制', 'color: #909399; font-size: 12px;');
                alert('⚠️ 自动复制失败，请手动复制控制台中的内容。\\n\\n提示：选中控制台中的JSON数据，按 Ctrl+C 复制。\\n\\n或者输入 copyCookiesData() 尝试手动复制。');
            }
        }).catch(err => {
            console.error('复制过程出错:', err);
            console.log('%c⚠️ 自动复制失败，请手动复制上面的内容', 'color: #e6a23c; font-size: 14px;');
            console.log('%c提示：您可以选中上面的JSON数据，然后按 Ctrl+C (Windows) 或 Cmd+C (Mac) 复制', 'color: #909399; font-size: 12px;');
            alert('⚠️ 自动复制失败，请手动复制控制台中的内容。');
        });
        
        return jsonStr;
    } catch (error) {
        console.error('提取cookies时出错:', error);
        alert('❌ 提取失败: ' + error.message);
    }
})();`

onMounted(() => {
  // 从 URL 参数获取 account_id
  accountId.value = route.query.account_id ? parseInt(route.query.account_id) : null
  
  if (!accountId.value) {
    ElMessage.error('缺少账号ID参数')
  } else {
    // 从步骤1开始显示
    currentStep.value = 1
  }
  
  // 监听来自登录窗口的消息
  window.addEventListener('message', handleMessage)
})

const handleMessage = (event) => {
  // 可以在这里处理来自登录窗口的消息
  if (event.data && event.data.type === 'login_success') {
    // 登录成功的消息
  }
}

const openLoginPage = () => {
  // 打开新窗口
  const loginWindow = window.open(
    'https://creator.douyin.com/', 
    '_blank', 
    'width=1200,height=800'
  )

  if (loginWindow) {
    loginWindowOpen.value = true
    currentStep.value = 2
    
    // 3秒后自动进入下一步
    setTimeout(() => {
      if (currentStep.value === 2) {
        currentStep.value = 3
      }
    }, 3000)
  } else {
    ElMessage.error('无法打开新窗口，请检查浏览器弹窗设置')
  }
}

const copyExtractCode = async () => {
  try {
    await navigator.clipboard.writeText(extractCode)
    copyCodeSuccess.value = true
    ElMessage.success('代码已复制到剪贴板！')
    setTimeout(() => {
      copyCodeSuccess.value = false
    }, 2000)
  } catch (error) {
    ElMessage.error('复制失败，请手动选择并复制代码')
  }
}

const submitCookies = async () => {
  const cookiesData = cookiesInput.value.trim()

  if (!cookiesData) {
    submitStatus.value = {
      type: 'error',
      message: '请先粘贴 cookies 数据'
    }
    return
  }

  // 验证JSON格式
  let cookiesJson
  try {
    cookiesJson = JSON.parse(cookiesData)
  } catch (e) {
    submitStatus.value = {
      type: 'error',
      message: 'Cookies 数据格式错误，请检查JSON格式'
    }
    return
  }

  submitting.value = true
  submitStatus.value = {
    type: 'info',
    message: '正在提交...'
  }

  try {
    // 提交到服务器
    const response = await api.accounts.updateCookies(accountId.value, cookiesData)
    
    if (response.code === 200) {
      submitStatus.value = {
        type: 'success',
        message: '✅ Cookies 提交成功！'
      }
      currentStep.value = 5
      
      // 更新账号登录状态（可选，如果失败不影响主流程）
      try {
        const statusResponse = await api.accounts.updateStatus(accountId.value, 'logged_in')
        if (statusResponse.code === 200) {
          console.log('账号登录状态已更新')
        }
      } catch (e) {
        console.warn('更新登录状态失败（不影响cookies保存）:', e)
      }
      
      // 通知父窗口（如果存在）
      if (window.opener) {
        window.opener.postMessage({
          type: 'login_success',
          account_id: accountId.value
        }, '*')
      }
      
      ElMessage.success('Cookies 提交成功！')
    } else {
      submitStatus.value = {
        type: 'error',
        message: `提交失败: ${response.message || '未知错误'}`
      }
      ElMessage.error(response.message || '提交失败')
    }
  } catch (error) {
    submitStatus.value = {
      type: 'error',
      message: `提交失败: ${error.message || '网络错误'}`
    }
    ElMessage.error(error.message || '提交失败')
    console.error('提交cookies失败:', error)
  } finally {
    submitting.value = false
  }
}

const closeWindow = () => {
  window.close()
}
</script>

<style scoped>
.login-helper-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.step {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
  border-left: 4px solid #409eff;
}

.step.hidden {
  display: none;
}

.step h3 {
  color: #409eff;
  margin-bottom: 15px;
  font-size: 18px;
}

.step p {
  color: #666;
  line-height: 1.6;
  margin-bottom: 10px;
}

.step .tip {
  color: #999;
  font-size: 12px;
}

.code-block {
  position: relative;
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  overflow-x: auto;
  margin: 15px 0;
}

.code-block pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.copy-btn {
  position: absolute;
  top: 10px;
  right: 10px;
}

.error-message {
  margin: 20px 0;
}
</style>
