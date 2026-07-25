import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.zhinenti.aistaff',
  appName: 'AI智能客服',
  webDir: 'frontend',
  bundledWebRuntime: false,
  server: {
    url: 'https://www.zhinenti.cn',  // 线上模式：直接加载线上页面
    // 如果要打包静态文件，注释掉 url 并取消下面注释：
    // android: { allowMixedContent: true }
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#6366f1',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
    },
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#6366f1',
    },
    Keyboard: {
      resize: 'body',
      resizeOnFullScreen: true,
    },
  },
  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: false,
  },
  ios: {
    scheme: 'AI智能客服',
  },
};

export default config;
