# 用「类 VPN」抓安卓游戏流量：能做到哪一步

结论先说：**VPN 只能把流量改道，不能自动解开 HTTPS / 游戏封包。**
在未 root 的零售安卓手机上，纯 VPN 方案基本读不到 `Index/index`；
现有 PC 代理 + 模拟器 / root 设备才是可落地路径。

## 1. 三层问题，别混在一起

```text
游戏 App
  │  ① 流量改道：VpnService / Wi-Fi 代理 / adb reverse
  ▼
本地代理（mitmproxy / 透明代理）
  │  ② TLS：需要游戏信任你的 CA；很多游戏还有证书固定
  ▼
明文 HTTP
  │  ③ 游戏封包：gf_authcode（XXTEA）+ 每次登录的 sign
  ▼
Index/index JSON → 账号快照 → PWA
```

- **① 改道**：`VpnService` 能拿到 IP 包，但要把 TCP 流接到本地 HTTP 代理，需要
  tun2socks 之类的用户态 TCP/IP 栈；不是 `VpnService` 一开就能读 HTTP。
- **② TLS**：Android 7+ 默认不信任用户安装的 CA（targetSdk ≥ 24 的 App）。
  游戏通常 targetSdk 很高，且不少客户端有证书固定。没有 root / 系统 CA / Frida 绕过，
  代理只能看到 TLS 握手，看不到 `Index/index`。
- **③ 封包**：`tools/android_proxy_capture.py` 用 `gflzirc.gf_authcode` 解 XXTEA，
  先用静态 key `yundoudou`，失败再用登录时抓到的 `sign`。所以必须抓到**本次登录**的
  请求/响应；只回放旧 `cn_creds` 的 sign 不行。

当前 PC 抓包之所以能跑，是因为：

- 模拟器可以 `adb root`，把 CA 塞进 `/system/etc/security/cacerts`（系统 CA）；
- 或者国服复活版走 `127.0.0.1:18765/18766` 的 HTTP 本地桥，不需要 TLS CA；
- 登录时 PC 代理能同时看到请求里的 `outdatacode/signcode`，从而拿到 `sign`。

## 2. 纯 VPN App 在真机上的现实

| 方案 | 免 PC | 免 root | 能读账号 | 说明 |
|---|---|---|---|---|
| PC mitmproxy + 模拟器（现状） | ❌ | ✅（模拟器 adb root） | ✅ | 最稳 |
| PC mitmproxy + 真机同 LAN | ❌ | ❌（需系统 CA） | 通常 ❌ | 用户 CA 多数游戏不信任 |
| 手机 VPN + 本地 mitmproxy | ✅ | ❌ | 仅 root/系统 CA 可行 | 需 tun2socks + mitmproxy + CA |
| 手机 VPN + 转发到 PC 代理 | ❌ | ✅ | ✅ | VPN 只是替代 Wi-Fi 代理设置，仍要 PC |
| root + Frida 读 `CS.GameData` | ✅ | ❌ | ✅ | 不走网络，最直接 |
| 国服复活版本地 HTTP 桥 | ✅ | ✅? | 需实现桥协议 | 游戏连 `127.0.0.1:18765`，桥不是现成的 |

### 为什么「VPN 转发到 PC」仍然要 PC

`VpnService` 只能把包送进 tun；要在手机上把 TCP 会话转给 PC 的 HTTP 代理，需要
tun2socks 之类的实现，且 PC 代理仍要监听 LAN、手机要信任 CA。它省掉的是“手动设 Wi-Fi 代理”，
不省 PC，也不解决证书。

### 国服复活版为什么特殊

客户端自带 `127.0.0.1:18765/18766` 的**本地桥**；`adb forward` 只是把桥暴露给 PC
（见 `build_private_server.md`）。这条链路不一定要 TLS CA，所以 `android_proxy_session.py`
里 `cn_revival` 的 `needs_ca=False`。

理论上，手机 VPN 按包名捕获游戏 UID 的出站流量，如果桥的上游是 HTTP，就可能免 CA 抓到
`Index/index`。但**桥协议、上游地址、鉴权都不在本仓库**，仓库里的 `adb forward` 只是端口转发；
要做成手机端全离线，需要先把本地桥的行为实测/复刻出来，不是“开 VPN”就能完成。

## 3. 如果一定要做「手机端全离线抓包」

推荐顺序：

1. **root 安卓手机 / 模拟器 + 系统 CA + mitmproxy**
   - 用 Termux 或 Chaquopy 把 mitmproxy 跑在手机；
   - 用 `VpnService` + tun2socks 把游戏流量导到 `127.0.0.1:8080`；
   - 把 `gflzirc` 的 `gf_authcode` 移植成 Kotlin/Python，解 `Index/index`；
   - 用现有 `app.capture.android_proxy.build_snapshot` 转快照。
2. **root + Frida**（更简单）
   - 手机跑 `frida-server`，把 `app/capture/lua_eval.py` 的只读 Lua 注入 `LuaEnv.Tick`；
   - 直接读 `CS.GameData`，完全不走网络，不受 TLS/证书影响；
   - 需要 root、游戏未检测 Frida；风险与 PC 端 Frida 相同。
3. **非 root 真机**
   - 不建议投入：TLS 信任 + 证书固定基本堵死；
   - 可行替代是「PC 抓包 + 手机 PWA 通过 LAN 拉 `/api/latest`」，体验上已经接近“打开就能看”。

## 4. 风险与边界

- 只处理**自己的账号**；不要做多账号批量、代练、交易。
- 抓包 / 改包可能违反游戏服务条款，存在封号风险；本项目只读、不修改游戏数据。
- 快照包含 UID / 昵称 / 仓库，不要公开上传。
- 不要在公共 Wi-Fi 上开透明代理；CA 私钥只留在本机。

## 5. 现阶段建议

- 日常使用：**PC 端抓包 + `run_web.ps1 --host 0.0.0.0` + 手机 PWA「连接」**。
  这已经是“手机上看账号”的最低成本方案。
- 想在手机上完全离线：优先考虑 **root + Frida**，其次 **root + 本地 mitmproxy**；
  纯 VPN 只在能装系统 CA 的设备上有意义。
- 如果要做，我可以下一步把 `VpnService + tun2socks + Chaquopy(mitmproxy/gflzirc)`
  做成一个独立的 `android-capture` 模块；但需要一台 root 设备/模拟器做联调，当前环境没有。
