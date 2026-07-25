# AI智能客服 - App 打包指南

## 前置要求

- Node.js 18+ 和 npm
- **Android**: Android Studio ( Hedgehog+ )
- **iOS**: Mac + Xcode 15+ + Apple Developer 账号

## 一、初始化项目

```bash
# 安装依赖
npm install

# 如果之前没有添加过平台
npx cap add android
npx cap add ios
```

## 二、两种运行模式

### 模式 A：线上模式（推荐，最简单）
当前 `capacitor.config.ts` 已配置 `server.url`，App 直接加载线上页面。
优点：无需重新打包即可更新内容。

### 模式 B：离线打包模式
编辑 `capacitor.config.ts`，注释掉 `server.url`，Capacitor 会打包前端静态文件到 App 内。

## 三、打包 Android APK

```bash
# 同步 Web 资源到原生项目
npx cap sync android

# 方法1：用 Android Studio 打开
npx cap open android
# → Build → Generate Signed Bundle / APK → 选择 APK → 签名 → Build

# 方法2：命令行打包
cd android
./gradlew assembleRelease
# APK 在 android/app/build/outputs/apk/release/
```

### 上架 Google Play
```bash
cd android
./gradlew bundleRelease
# AAB 在 android/app/build/outputs/bundle/release/
# 上传到 Google Play Console
```

## 四、打包 iOS App

```bash
# 同步 Web 资源
npx cap sync ios

# 用 Xcode 打开
npx cap open ios
# → 选择 Team（Apple Developer 账号）
# → Product → Archive → Distribute App
```

### 上架 App Store
1. 在 Xcode 中 Archive → Distribute App → App Store Connect
2. 在 [App Store Connect](https://appstoreconnect.apple.com) 创建 App 记录
3. 上传截图、描述、隐私政策
4. 提交审核（通常 1-3 天）

## 五、应用图标和启动页

图标已准备好在 `frontend/icons/` 目录：

### Android
将以下图标复制到对应位置：
- `icon-192.png` → `android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png`
- 或使用 Android Studio 的 Image Asset 工具批量生成各尺寸

### iOS
在 Xcode 中打开 `ios/App/App/Assets.xcassets/AppIcon.appiconset`，拖入各尺寸图标。

## 六、费用参考

| 项目 | 费用 |
|------|------|
| Apple Developer 账号 | $99/年 |
| Google Play 开发者 | $25（一次性） |

## 七、注意事项

1. **隐私政策**：上架应用商店必须提供隐私政策页面链接
2. **HTTPS**：后端必须使用 HTTPS（已有）
3. **离线支持**：已配置 Service Worker，弱网环境也能显示界面
4. **更新策略**：线上模式下，更新服务器代码即可，无需重新发版
