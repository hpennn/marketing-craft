# 智能营销助手 桌面版构建指南

> 基于 Electron + electron-builder，支持 Windows / macOS / Linux 三端打包。

---

## 一、环境准备

| 依赖       | 版本要求         | 说明                                     |
| ---------- | --------------- | ---------------------------------------- |
| Node.js    | >= 18.x          | 推荐使用 LTS 版本                        |
| npm        | >= 9.x           | 随 Node.js 安装                          |
| Python     | >= 3.10          | 后端运行环境（仅离线模式需要）            |

### 额外平台依赖

| 平台    | 额外要求                                                    |
| ------- | ----------------------------------------------------------- |
| Windows | 无需额外安装，直接打包                                       |
| macOS   | 需安装 Xcode Command Line Tools：`xcode-select --install`   |
| Linux   | 需安装 `rpm` 和 `dpkg`（Ubuntu: `sudo apt install rpm`）     |

---

## 二、本地构建步骤

### 2.1 构建前端静态资源

```bash
# 在项目根目录执行
cd frontend/
npm install
npm run build
```

> 确保 `frontend/index.html` 存在，离线 fallback 依赖此文件。

### 2.2 安装 Electron 依赖

```bash
cd electron/
npm install
```

### 2.3 准备应用图标

在 `electron/icons/` 目录下放置以下图标文件：

```
electron/icons/
├── icon.png        # 512x512 PNG（Linux AppImage 使用）
├── icon.ico        # 256x256 ICO（Windows 安装包使用）
├── icon.icns       # macOS 图标（包含 16/32/128/256/512/1024 尺寸）
└── icon@2x.png     # 1024x1024 PNG（高分辨率备用）
```

**图标制作工具推荐：**
- 在线转换：https://icoconvert.com/
- macOS 生成 icns：`iconutil -c icns icon.iconset`
- 使用 electron-icon-maker：`npx electron-icon-maker --input=icon.png --output=./icons`

### 2.4 开发模式运行

```bash
cd electron/
npm start
```

应用将加载在线 URL（https://craft.zhinenti.cn），网络不可用时自动降级到 `frontend/index.html`。

### 2.5 打包构建

```bash
# 打包当前平台
cd electron/
npm run dist

# 仅打包 Windows 安装包（.exe）
npm run dist:win

# 仅打包 macOS DMG
npm run dist:mac

# 仅打包 Linux AppImage
npm run dist:linux

# 全平台打包（需在 macOS 上执行）
npm run dist:all
```

打包产物输出到项目根目录的 `dist-electron/` 文件夹：

```
dist-electron/
├── 智能营销助手-1.0.0-Setup.exe        # Windows NSIS 安装包
├── 智能营销助手-1.0.0-x64.dmg          # macOS Intel DMG
├── 智能营销助手-1.0.0-arm64.dmg        # macOS Apple Silicon DMG
└── 智能营销助手-1.0.0-x86_64.AppImage  # Linux AppImage
```

---

## 三、跨平台构建说明

### 3.1 在 macOS 上打包全平台

macOS 是唯一可以同时打包三端的平台（Windows 和 Linux 需要 Wine/特定工具）：

```bash
cd electron/
npm run dist:all
```

### 3.2 使用 CI/CD 自动构建（推荐）

推荐使用 GitHub Actions 自动构建，示例 workflow：

```yaml
# .github/workflows/electron-build.yml
name: Build Desktop App

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - name: Build Frontend
        run: |
          cd frontend
          npm install
          npm run build
      - name: Install Electron Deps & Build
        run: |
          cd electron
          npm install
          npm run dist
      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.os }}
          path: |
            dist-electron/*.exe
            dist-electron/*.dmg
            dist-electron/*.AppImage
```

### 3.3 各平台产物说明

| 平台    | 格式        | 说明                                      |
| ------- | ----------- | ----------------------------------------- |
| Windows | NSIS .exe   | 支持自定义安装目录、创建桌面快捷方式        |
| macOS   | DMG         | 分为 x64 和 arm64 两个版本                |
| Linux   | AppImage    | 无需安装，直接运行                         |

---

## 四、应用签名

### 4.1 Windows 签名

生产环境建议对 Windows 安装包进行代码签名，否则用户安装时会弹出 SmartScreen 警告。

**方式一：使用 EV 证书（推荐）**

1. 购买代码签名证书（推荐 Sectigo / DigiCert / GlobalSign）
2. 将 `.pfx` 证书文件放到安全位置
3. 在 `electron/package.json` 的 `build.win` 中添加签名配置：

```json
"win": {
  "certificateFile": "path/to/certificate.pfx",
  "certificatePassword": "",
  "signingHashAlgorithms": ["sha256"]
}
```

或使用环境变量（CI/CD 推荐）：

```bash
export WIN_CSC_LINK="./certificate.pfx"
export WIN_CSC_PASSWORD="your_password"
npm run dist:win
```

**方式二：使用 Azure Trusted Signing（新）**

微软推出的云签名服务，无需保管证书文件，详见 https://azure.microsoft.com/products/trusted-signing

### 4.2 macOS 签名

macOS 应用必须签名才能在非 App Store 渠道分发，否则 Gatekeeper 会阻止运行。

**前置条件：**
1. Apple Developer 账号（年费 $99）
2. 在 Apple Developer 后台创建 Developer ID Application 证书
3. 创建 Developer ID Installer 证书（用于安装包签名）

**签名配置：**

```bash
# 设置环境变量
export APPLE_ID="your@email.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="XXXXXXXXXX"

# 构建并签名
cd electron/
npm run dist:mac
```

或在 `electron/package.json` 的 `build.mac` 中添加：

```json
"mac": {
  "identity": "Developer ID Application: Your Company (XXXXXXXXXX)",
  "hardenedRuntime": true,
  "entitlements": "entitlements.mac.plist",
  "entitlementsInherit": "entitlements.mac.plist"
}
```

**公证（Notarization）：**

electron-builder v24+ 默认自动公证。需确保设置上述 APPLE_ID 环境变量。

**entitlements.mac.plist 文件：**

在 `electron/` 目录创建 `entitlements.mac.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.cs.allow-jit</key>
  <true/>
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
  <true/>
  <key>com.apple.security.network.client</key>
  <true/>
</dict>
</plist>
```

---

## 五、常见问题

### Q: 打包后应用打开白屏
检查 `frontend/index.html` 是否存在。离线 fallback 路径为 `electron/main.js` 中的 `OFFLINE_PATH`。

### Q: Windows 安装包被杀毒软件误报
需要进行代码签名。未签名的 exe 文件容易被 360、Windows Defender 等标记为可疑。

### Q: macOS 提示"应用已损坏"
应用未签名或未公证。使用 Apple Developer 证书签名并公证后可解决。

### Q: Linux AppImage 无法运行
需要赋予执行权限：`chmod +x *.AppImage`

---

## 六、版本更新

发布新版本时：

```bash
# 1. 修改 electron/package.json 中的 version
# 2. 重新构建
cd electron/
npm run dist

# 3. 将安装包上传到发布渠道
```

推荐使用 GitHub Releases 管理发布版本，配合 `electron-updater` 可实现应用内自动更新。
