// 增强的反检测脚本，专门针对抖音的检测机制
// 包括 bitbrowser 检测、自动化工具检测等

(function() {
    'use strict';
    
    // 1. 隐藏 navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    // 2. 删除 webdriver 相关属性
    delete navigator.__proto__.webdriver;
    
    // 3. 伪装 Chrome 对象
    if (!window.chrome) {
        window.chrome = {};
    }
    
    // 4. 伪装 Permissions API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    
    // 5. 伪装 Plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    
    // 6. 伪装 Languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en']
    });
    
    // 7. 隐藏自动化相关特征
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });
    
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
    });
    
    // 8. 伪装 Connection
    if (navigator.connection) {
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                rtt: 50,
                downlink: 10,
                effectiveType: '4g',
                saveData: false
            })
        });
    }
    
    // 9. 阻止 bitbrowser 检测
    // 拦截 bitbrowser:// 协议
    const originalOpen = window.open;
    window.open = function(url, target, features) {
        if (url && url.startsWith('bitbrowser://')) {
            console.warn('Blocked bitbrowser protocol:', url);
            return null;
        }
        return originalOpen.apply(this, arguments);
    };
    
    // 10. 伪装 Canvas 指纹
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {
        const context = this.getContext('2d');
        if (context) {
            const imageData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] += Math.floor(Math.random() * 10) - 5;
            }
            context.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.apply(this, arguments);
    };
    
    // 11. 伪装 WebGL 指纹
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.apply(this, arguments);
    };
    
    // 12. 伪装 AudioContext 指纹
    if (window.AudioContext || window.webkitAudioContext) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const originalCreateOscillator = AudioContext.prototype.createOscillator;
        AudioContext.prototype.createOscillator = function() {
            const oscillator = originalCreateOscillator.apply(this, arguments);
            const originalStart = oscillator.start;
            oscillator.start = function() {
                return originalStart.apply(this, arguments);
            };
            return oscillator;
        };
    }
    
    // 13. 伪装 Battery API
    if (navigator.getBattery) {
        const originalGetBattery = navigator.getBattery;
        navigator.getBattery = function() {
            return Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1
            });
        };
    }
    
    // 14. 伪装 MediaDevices
    if (navigator.mediaDevices) {
        const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
        navigator.mediaDevices.enumerateDevices = function() {
            return originalEnumerateDevices.apply(this, arguments).then(devices => {
                return devices.map(device => {
                    if (device.kind === 'videoinput' || device.kind === 'audioinput') {
                        device.deviceId = 'default';
                        device.label = '';
                    }
                    return device;
                });
            });
        };
    }
    
    // 15. 伪装 Notification
    if (window.Notification) {
        const originalNotification = window.Notification;
        window.Notification = function(title, options) {
            return new originalNotification(title, options);
        };
        window.Notification.permission = 'default';
        window.Notification.requestPermission = function() {
            return Promise.resolve('default');
        };
    }
    
    // 16. 伪装 window.outerWidth 和 window.outerHeight
    Object.defineProperty(window, 'outerWidth', {
        get: () => window.innerWidth
    });
    
    Object.defineProperty(window, 'outerHeight', {
        get: () => window.innerHeight + 85
    });
    
    // 17. 伪装 screen 对象
    Object.defineProperty(screen, 'availWidth', {
        get: () => window.innerWidth
    });
    
    Object.defineProperty(screen, 'availHeight', {
        get: () => window.innerHeight
    });
    
    // 18. 阻止自动化检测脚本
    const automationKeywords = ['webdriver', 'selenium', 'puppeteer', 'playwright', 'automation', 'headless'];
    automationKeywords.forEach(keyword => {
        Object.defineProperty(navigator, keyword, {
            get: () => undefined,
            configurable: true
        });
    });
    
    // 19. 伪装 toString 方法
    const originalToString = Function.prototype.toString;
    Function.prototype.toString = function() {
        if (this === navigator.webdriver || this === window.chrome) {
            return 'function() { [native code] }';
        }
        return originalToString.apply(this, arguments);
    };
    
    // 20. 伪装 User-Agent（如果需要）
    // 注意：这需要在浏览器启动时设置，这里只是确保一致性
    
    console.log('[Stealth] Enhanced anti-detection script loaded');
})();

