# GF Account Forge · WebUI / PWA / Android

同一套静态页面，三处可用：

1. **PC 本地 WebUI**：`run_web.ps1` → `http://127.0.0.1:8770/`
2. **Android PWA**：Chrome 打开 localhost（配合 `adb reverse`）后「安装应用」
3. **Android APK**：`android/` WebView 套壳工程，资源全部内置，离线可用

图像素材（头像、图标、榜单 JSON、归海 / 秋水组件表）全部内置；运行时只需要
**账号登录后的快照 JSON**（UID / 人形 / 妖精 / 融合势力 / 装备 / 组件）。

## 功能

- 总览：四维评分（人形 40% / 妖精 20% / 融合势力 20% / 装备 20%）、雷达图、下一步建议
- 人形 / 妖精 / 融合势力：仓库、三改合并、品质分组、逐条复制、搜索与档位筛选
- 装备：27 项目标 vs 当前个数，可按活动切换
- **组件**：当前账号全部机动装甲组件，归海 `归N` / 秋水 `秋M` 命中数
- **方案**：
  - 归海一图流：25 件 / 42 条主词条 / 183 条词条组合，按仓库标「已拥有 / 缺失」
  - 秋水各关卡：8 个活动 / 21 张表 / 189 条需求 / 29 件组件，可按活动、主战坦克 / 机甲筛选
- 图鉴：全量单位与拥有状态
- 离线：Service Worker 预缓存数据、按需缓存头像；已看过的单位断网可继续看

## 启动 WebUI

```powershell
cd E:\python\gf_forge\account_evaluate
.\run_web.ps1
```

默认 `http://127.0.0.1:8770/`。首次会运行 `tools/build_web.py` 生成 `web/data/` 与头像副本。
需要手机/平板访问时：

```powershell
.\run_web.ps1 --host 0.0.0.0
# 手机浏览器打开 http://<电脑局域网IP>:8770/
```

> 局域网 HTTP 不是安全上下文，**不能完整安装 PWA**，只能预览；安装请用下面的 localhost 方案或 APK。

## 账号快照从哪来

WebUI 不直接登录游戏，也不保存账号密码。三种方式：

1. **PC 连接**：Qt 端抓包 / Frida 生成 `snapshots/account_*.json` 后，PWA 点「连接」，
   默认请求 `/api/latest`；`serve.py` 会自动合并同目录的 `index_*.json`（组件数据）。
   - 也支持 `?snapshot=http://.../api/latest` 或任意 URL。
2. **文件导入**：点「导入快照」，选择 `account_*.json` 或合并后的 `web_snapshot.json`。
3. **导出合并快照**：
   ```powershell
   python tools\export_web_snapshot.py --out web_snapshot.json
   ```
   这个文件同时包含账号与组件，适合拷到手机离线导入。

API：

- `GET /api/health`
- `GET /api/latest`：最新账号 + 最新组件索引（UID 不一致则不混用）
- `GET /api/snapshots`：列出可用快照
- `GET /api/snapshot/<name>`

## Android PWA（推荐先试）

```powershell
adb reverse tcp:8770 tcp:8770
.\run_web.ps1
```

手机 Chrome 打开 `http://localhost:8770/` → 菜单 →「安装应用 / 添加到主屏幕」。
localhost 是安全上下文，Service Worker 与安装都正常。

## Android APK（WebView 套壳）

没有服务器、完全离线时用这个：

```powershell
python tools\build_web.py
python tools\build_android_assets.py
```

然后用 Android Studio 打开 `android/`，Run / `gradlew assembleDebug`。
详见 `android/README.md`。当前工作区没有 Android SDK / Gradle，仓库只提供工程，不附预编译 APK。

## 数据构建

```powershell
python tools\build_web.py          # app/data + assets/avatars -> web/data + web/assets
python tools\build_android_assets.py
```

`web/data/core.json` 是 Service Worker 的预缓存清单；新增数据文件后重新运行
`build_web.py` 即可。升级静态资源时改 `web/sw.js` 的 `CACHE` 常量。

## 目录

```text
web/
├─ index.html / styles.css / app.js / modules.js
├─ serve.py              # 静态服务 + /api/latest
├─ sw.js                 # 离线缓存
├─ manifest.webmanifest
├─ icons/
├─ data/                 # 由 build_web.py 生成（提交到仓库，便于静态部署）
└─ assets/avatars/       # 由 build_web.py 生成（不提交，打包时生成）
android/                 # WebView 套壳工程
```

## 限制

- PWA 不能直接读取游戏进程或 Android 私有目录；快照必须由 PC 端抓取/导出。
- 不要指望“开一个 VPN 就能抓账号”：VPN 只改道，TLS 信任 / 证书固定 / 游戏封包解密都在后面，非 root 真机基本走不通。详见 [`../docs/android_vpn_capture.md`](../docs/android_vpn_capture.md)。
- 快照包含 UID / 昵称 / 仓库，请勿公开分享。
- 组件数据依赖 `index_*.json`；只导入 `account_*.json` 时「组件 / 方案」会提示缺少组件。
- 秋水的 2 个活动文档（坠入兔洞Plus、混沌落幕Plus）当前需要登录，未收录；其余 6 个活动没有组件页。
