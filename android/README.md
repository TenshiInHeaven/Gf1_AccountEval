# GF Account Forge · Android WebView 套壳

这是把 `web/` 静态 PWA 打包成离线 APK 的最小 Android 工程：WebView 通过
`WebViewAssetLoader` 把 `app/src/main/assets/www/` 映射到
`https://appassets.androidplatform.net/assets/www/`，因此：

- 不需要服务器，断网可用；
- 属于安全上下文（https），Service Worker / localStorage 正常；
- 图片、JSON、头像全部内置，只有「连接快照」时才需要访问 PC 的 `/api/latest`。

## 构建前：生成 Web 资源

```powershell
cd E:\python\gf_forge\account_evaluate
python tools\build_web.py
python tools\build_android_assets.py
```

`build_android_assets.py` 会把 `web/` 复制到 `app/src/main/assets/www/`，并从
`assets/app_icon.png` 生成各密度 `mipmap/ic_launcher.png`。

## 构建 APK

用 Android Studio 打开本目录（`android/`），等待 Gradle 同步后：

- 模拟器 / 真机调试：`Run 'app'`
- 命令行：`gradlew assembleDebug`（首次需 Android Studio 生成 wrapper，或本机安装 Gradle 8.7+）

当前工作区没有安装 Android SDK / Gradle，所以仓库只提供**可直接导入 Android Studio 的工程**，
没有预编译 APK。

## 账号数据

- **离线**：把 PC 端导出的 `exports/web_snapshot.json` 放进手机，打开 App → 「导入快照」。
- **局域网**：PC 运行 `run_web.ps1 --host 0.0.0.0`，手机 App 点「连接」，填
  `http://<PC IP>:8770/api/latest`（需要同一 Wi-Fi；`usesCleartextTraffic` 已开启）。
- App 不会保存游戏账号密码；快照包含 UID / 昵称，请勿公开分享。

## 只读设计

安卓端只做**只读查看器**：读取已有 JSON / 内置图鉴，不抓包、不代理、不登录游戏。
启动默认进入「图鉴」（固定数据）；账号快照由 PC 端生成后，通过「导入快照」/「连接」载入。

## 与 PWA 的关系

`web/` 本身也是可安装的 PWA。用 Chrome 打开 `http://localhost:8770/`（配合
`adb reverse tcp:8770 tcp:8770`）即可「添加到主屏幕」；APK 则是同一套页面的离线壳，
适合不想常开 PC 的场景。
