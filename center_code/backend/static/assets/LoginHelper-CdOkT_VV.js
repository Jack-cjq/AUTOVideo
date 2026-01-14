import{_ as j,r as u,o as E,I as M,E as d,a as y,b as f,d as l,f as n,g as p,l as t,e,H as k,t as v,k as L,n as _}from"./index-DyjCXijH.js";const R={class:"login-helper-container"},W={key:0,class:"error-message"},A={key:1},q={class:"code-block"},$={key:0,style:{"margin-top":"10px"}},O=`// 在抖音网站 (creator.douyin.com) 的控制台中运行此代码
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
})();`,B={__name:"LoginHelper",setup(F){const b=M(),g=u(null),r=u(1),C=u(!1),w=u(""),m=u(!1),i=u(null),x=u(!1);E(()=>{g.value=b.query.account_id?parseInt(b.query.account_id):null,g.value?r.value=1:d.error("缺少账号ID参数"),window.addEventListener("message",N)});const N=a=>{a.data&&a.data.type},H=()=>{window.open("https://creator.douyin.com/","_blank","width=1200,height=800")?(C.value=!0,r.value=2,setTimeout(()=>{r.value===2&&(r.value=3)},3e3)):d.error("无法打开新窗口，请检查浏览器弹窗设置")},I=async()=>{try{await navigator.clipboard.writeText(O),x.value=!0,d.success("代码已复制到剪贴板！"),setTimeout(()=>{x.value=!1},2e3)}catch{d.error("复制失败，请手动选择并复制代码")}},D=async()=>{const a=w.value.trim();if(!a){i.value={type:"error",message:"请先粘贴 cookies 数据"};return}let o;try{o=JSON.parse(a)}catch{i.value={type:"error",message:"Cookies 数据格式错误，请检查JSON格式"};return}m.value=!0,i.value={type:"info",message:"正在提交..."};try{const s=await _.accounts.updateCookies(g.value,a);if(s.code===200){i.value={type:"success",message:"✅ Cookies 提交成功！"},r.value=5;try{(await _.accounts.updateStatus(g.value,"logged_in")).code===200&&console.log("账号登录状态已更新")}catch(c){console.warn("更新登录状态失败（不影响cookies保存）:",c)}window.opener&&window.opener.postMessage({type:"login_success",account_id:g.value},"*"),d.success("Cookies 提交成功！")}else i.value={type:"error",message:`提交失败: ${s.message||"未知错误"}`},d.error(s.message||"提交失败")}catch(s){i.value={type:"error",message:`提交失败: ${s.message||"网络错误"}`},d.error(s.message||"提交失败"),console.error("提交cookies失败:",s)}finally{m.value=!1}},P=()=>{window.close()};return(a,o)=>{const s=p("el-alert"),c=p("el-button"),h=p("el-tab-pane"),J=p("el-tabs"),z=p("el-input"),T=p("el-result"),V=p("el-card");return f(),y("div",R,[l(V,null,{header:n(()=>[...o[2]||(o[2]=[e("h2",null,"🎬 抖音账号登录助手",-1)])]),default:n(()=>[g.value?(f(),y("div",A,[e("div",{class:k(["step",{hidden:r.value<1}])},[o[4]||(o[4]=e("h3",null,"步骤 1: 打开抖音登录页面",-1)),o[5]||(o[5]=e("p",null,"点击下面的按钮，将在新窗口中打开抖音创作者中心登录页面。",-1)),l(c,{type:"primary",onClick:H,disabled:C.value},{default:n(()=>[t(v(C.value?"已打开登录页面":"打开抖音登录页面"),1)]),_:1},8,["disabled"])],2),e("div",{class:k(["step",{hidden:r.value<2}])},[...o[6]||(o[6]=[e("h3",null,"步骤 2: 完成登录",-1),e("p",null,"在新打开的窗口中完成抖音登录（手机号登录或扫码登录）。",-1),e("p",{class:"tip"},"登录完成后，请继续下一步。",-1)])],2),e("div",{class:k(["step",{hidden:r.value<3}])},[o[12]||(o[12]=e("h3",null,"步骤 3: 提取 Cookies",-1)),o[13]||(o[13]=e("p",null,"登录完成后，请按照以下步骤提取 cookies：",-1)),l(J,{modelValue:a.extractMethod,"onUpdate:modelValue":o[0]||(o[0]=S=>a.extractMethod=S),style:{margin:"15px 0"}},{default:n(()=>[l(h,{label:"方法1: 从 Network 标签页获取（推荐）",name:"network"},{default:n(()=>[l(s,{type:"success",closable:!1,style:{margin:"10px 0"}},{title:n(()=>[...o[7]||(o[7]=[e("strong",null,"✅ 推荐方法：可以获取所有 cookies（包括 HttpOnly）",-1)])]),_:1}),o[8]||(o[8]=e("ol",{style:{"margin-left":"20px","margin-top":"10px","line-height":"2"}},[e("li",null,[t("在新打开的抖音登录窗口中，按 "),e("strong",null,"F12"),t(" 打开开发者工具")]),e("li",null,[t("切换到 "),e("strong",null,"Network（网络）"),t(" 标签页")]),e("li",null,"刷新页面或执行任意操作（如点击某个按钮）"),e("li",null,[t("在 Network 标签页中找到任意一个请求（如 "),e("code",null,"creator.douyin.com"),t(" 的请求）")]),e("li",null,[t("点击该请求，查看右侧的 "),e("strong",null,"Headers"),t(" 标签")]),e("li",null,[t("在 "),e("strong",null,"Request Headers"),t(" 部分，找到 "),e("strong",null,"Cookie:"),t(" 这一行")]),e("li",null,"复制完整的 Cookie 值（通常很长，包含很多 cookies）"),e("li",null,[t("切换到 "),e("strong",null,"Console（控制台）"),t(" 标签页")]),e("li",null,"先执行下面的提取代码（获取 localStorage 等）"),e("li",null,[t("然后在控制台输入："),e("code",null,'parseCookieHeader("粘贴的Cookie值")')]),e("li",null,[t("最后输入："),e("code",null,"copyCookiesData()"),t(" 或查看输出的 JSON")]),e("li",null,"复制完整的 JSON 数据，粘贴到下面的文本框中提交")],-1))]),_:1}),l(h,{label:"方法2: 从 Console 获取（不完整）",name:"console"},{default:n(()=>[l(s,{type:"warning",closable:!1,style:{margin:"10px 0"}},{title:n(()=>[...o[9]||(o[9]=[e("strong",null,"⚠️ 注意：此方法只能获取非 HttpOnly 的 cookies，可能缺少关键的登录 cookies",-1)])]),_:1}),o[10]||(o[10]=e("ol",{style:{"margin-left":"20px","margin-top":"10px","line-height":"2"}},[e("li",null,[t("在新打开的抖音登录窗口中，按 "),e("strong",null,"F12"),t(" 打开开发者工具")]),e("li",null,[t("切换到 "),e("strong",null,"Console（控制台）"),t(" 标签页")]),e("li",null,"复制下面的代码并粘贴到控制台中，然后按回车执行"),e("li",null,"代码会自动提取 cookies 并显示在控制台中"),e("li",null,"复制控制台输出的 JSON 数据，然后粘贴到下面的文本框中提交")],-1))]),_:1})]),_:1},8,["modelValue"]),e("div",q,[l(c,{class:"copy-btn",size:"small",onClick:I},{default:n(()=>[t(v(x.value?"已复制":"复制代码"),1)]),_:1}),e("pre",{id:"extractCode"},v(O))]),l(s,{type:"warning",closable:!1,style:{"margin-top":"10px"}},{title:n(()=>[...o[11]||(o[11]=[e("strong",null,"注意：",-1),t("由于浏览器安全限制，此代码只能提取部分cookies（非HttpOnly的cookies）。 如果登录后仍然提示需要登录，可能需要使用浏览器扩展来提取完整的cookies。 ",-1)])]),_:1})],2),e("div",{class:k(["step",{hidden:r.value<3}])},[o[14]||(o[14]=e("h3",null,"步骤 4: 提交 Cookies",-1)),o[15]||(o[15]=e("p",null,"将从控制台复制的 cookies 数据粘贴到下面的文本框中：",-1)),l(z,{modelValue:w.value,"onUpdate:modelValue":o[1]||(o[1]=S=>w.value=S),type:"textarea",rows:10,placeholder:"粘贴从控制台复制的 cookies JSON 数据...",style:{margin:"10px 0"}},null,8,["modelValue"]),l(c,{type:"primary",onClick:D,loading:m.value},{default:n(()=>[t(v(m.value?"提交中...":"提交 Cookies"),1)]),_:1},8,["loading"]),i.value?(f(),y("div",$,[l(s,{type:i.value.type,closable:!1,title:i.value.message},null,8,["type","title"])])):L("",!0)],2),e("div",{class:k(["step",{hidden:r.value<5}])},[l(T,{icon:"success",title:"登录完成","sub-title":"Cookies 已成功保存到服务器！"},{extra:n(()=>[l(c,{type:"primary",onClick:P},{default:n(()=>[...o[16]||(o[16]=[t("关闭窗口",-1)])]),_:1})]),_:1})],2)])):(f(),y("div",W,[l(s,{type:"error",closable:!1},{title:n(()=>[...o[3]||(o[3]=[t("错误：缺少账号ID参数",-1)])]),_:1})]))]),_:1})])}}},G=j(B,[["__scopeId","data-v-849089d0"]]);export{G as default};
