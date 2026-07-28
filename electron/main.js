const { app, BrowserWindow, Menu, shell, dialog, net } = require('electron');
const path = require('path');

// 在线地址
const ONLINE_URL = 'https://craft.zhinenti.cn';
// 离线 fallback 路径
const OFFLINE_PATH = path.join(__dirname, '..', 'frontend', 'index.html');

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: '智能营销助手',
    icon: path.join(__dirname, 'icons', 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
    show: false,
    backgroundColor: '#ffffff',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
  });

  // 先尝试加载在线 URL
  mainWindow.loadURL(ONLINE_URL).catch(() => {
    // 网络不可用时加载离线页面
    loadOfflinePage();
  });

  // 窗口准备好后显示，避免白屏闪烁
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // 监听页面加载失败，自动降级到离线页面
  mainWindow.webContents.on('did-fail-load', (_event, _errorCode, _errorDescription, validatedURL) => {
    if (validatedURL === ONLINE_URL || validatedURL === ONLINE_URL + '/') {
      loadOfflinePage();
    }
  });

  // 外部链接用默认浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * 加载离线 fallback 页面
 */
function loadOfflinePage() {
  const fs = require('fs');
  if (fs.existsSync(OFFLINE_PATH)) {
    mainWindow.loadFile(OFFLINE_PATH);
  } else {
    mainWindow.loadURL(`data:text/html;charset=utf-8,
      <html><body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
        <div style="text-align:center">
          <h2>网络连接失败</h2>
          <p>请检查网络后重试，或确认离线资源已正确部署。</p>
          <button onclick="location.reload()" style="padding:8px 24px;cursor:pointer">重试</button>
        </div>
      </body></html>
    `);
  }
}

/**
 * 构建简洁菜单栏（仅保留基本编辑和视图）
 */
function buildMenu() {
  const isMac = process.platform === 'darwin';

  const template = [];

  // macOS: 应用菜单（含 About）
  if (isMac) {
    template.push({
      label: app.name,
      submenu: [
        { role: 'about', label: '关于 智能营销助手' },
        { type: 'separator' },
        { role: 'services', label: '服务' },
        { type: 'separator' },
        { role: 'hide', label: '隐藏' },
        { role: 'hideOthers', label: '隐藏其他' },
        { role: 'unhide', label: '全部显示' },
        { type: 'separator' },
        { role: 'quit', label: '退出' },
      ],
    });
  }

  // 编辑菜单
  template.push({
    label: '编辑',
    submenu: [
      { role: 'undo', label: '撤销' },
      { role: 'redo', label: '重做' },
      { type: 'separator' },
      { role: 'cut', label: '剪切' },
      { role: 'copy', label: '复制' },
      { role: 'paste', label: '粘贴' },
      { role: 'selectAll', label: '全选' },
    ],
  });

  // 视图菜单
  template.push({
    label: '视图',
    submenu: [
      { role: 'reload', label: '刷新' },
      { role: 'forceReload', label: '强制刷新' },
      { role: 'toggleDevTools', label: '开发者工具' },
      { type: 'separator' },
      { role: 'resetZoom', label: '实际大小' },
      { role: 'zoomIn', label: '放大' },
      { role: 'zoomOut', label: '缩小' },
      { type: 'separator' },
      { role: 'togglefullscreen', label: '切换全屏' },
    ],
  });

  // Windows / Linux: 窗口 + 帮助菜单
  if (!isMac) {
    template.push({
      label: '帮助',
      submenu: [
        {
          label: '关于 智能营销助手',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: '关于 智能营销助手',
              message: '智能营销助手',
              detail: '版本: ' + app.getVersion() + '\\n© 智恩科技',
            });
          },
        },
      ],
    });
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// ---- App 生命周期 ----
app.whenReady().then(() => {
  buildMenu();
  createWindow();

  app.on('activate', () => {
    // macOS: 点击 dock 图标且无窗口时重新创建
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // macOS: 关闭所有窗口后保持运行，直到用户手动退出
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
