# GF Account Forge PWA

这是给 Android / 手机 / 平板使用的**轻量查看器**，与 PC 端 Qt 应用共享同一份榜单、图鉴和头像数据。

## 定位

- **PC 端（`app/` + `run.ps1`）**：负责账号提取（Windows XLua / Android ADB 拉取快照）。
- **PWA（本目录）**：负责离线查看、四维评分、多强度筛选、逐条复制详情。
- PWA 不读取游戏进程，不需要 root；账号数据必须以 `account_snapshot.json` 导入。

## 启动

```powershell
cd E:\python\gf_forge\account_evaluate
.\run_web.ps1
```

默认地址：`http://127.0.0.1:8770/`。手机/模拟器同局域网时可用：

```powershell
python web\serve.py --host 0.0.0.0 --port 8770
```

然后访问 `http://<电脑局域网 IP>:8770/` 预览。注意：**局域网 HTTP 不是安全上下文，不能完整安装 PWA**；只能预览页面。

## 在 Android 模拟器/真机上安装

推荐用 `adb reverse` 把手机上的 localhost 映射到电脑，这样在手机上打开 `http://localhost:8770/` 就是安全上下文，可以安装 PWA：

```powershell
adb reverse tcp:8770 tcp:8770
```

然后在 Android Chrome 打开 `http://localhost:8770/`，菜单里选「安装应用 / 添加到主屏幕」。

也可以把 `web/` 部署到任意 HTTPS 静态站点，`manifest.webmanifest` 和 `sw.js` 已经配好离线缓存。

## 数据

```text
web/data/codex/*.json
web/data/tierlists/*.json
web/data/equipment_*.json
web/data/sample_account.json
web/assets/avatars/*.webp
```

这些文件由 `tools/build_web.py` 从 `app/data` 和 `assets/avatars` 复制生成；修改 PC 端数据后重新运行：

```powershell
python tools\build_web.py
```

PWA 的评分逻辑在 `app.js` 里，和 Qt 端保持同一口径：人形 40% / 妖精 20% / 融合势力 20% / 装备 20%；妖精详情按品质分组显示逐条复制，不再把「最高品质 × 总数」当成全满星。

## PWA 缓存

- 首次安装缓存 HTML/CSS/JS、榜单 JSON、示例快照和图标。
- 头像按需缓存；第二次打开可离线使用已看过的单位。
- 升级版本时修改 `sw.js` 里的 `CACHE` 常量即可让旧缓存失效。

## 限制

- PWA 不能直接读取 Android 游戏进程或 `/sdcard/Android/data` 私有目录；账号快照需要 PC 端或其他导出工具生成。
- Android 端的进程/内存读取需要 root + Frida 或 MITM，可能触发反外挂/安全软件，本项目默认不做。
- 如需原生 APK，可将同一套静态页面用 WebView/TWA 套壳，或后续用 Kotlin + Compose 重写；当前先以 PWA 验证交互和评分口径。
