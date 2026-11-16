# Gf1_AccountEval 使用说明

这是一个本地优先的《少女前线 1》账号查看与四维强度评估工具。  
**不修改游戏、不绕过登录、不上传账号数据。**

> **国服复活版 / PC 继承客户端：支持，但必须全新登录。**  
> 抓包生效后，在游戏里退出登录 / 切换账号，再重新输入账密；日志出现 `Index/getUidPC` 和 `[KEY] uid/sign` 才算成功。只重启客户端会复用缓存登录态，通常抓不到 sign，也就解不开 `Index/index`。

## 你需要什么

- Windows 10/11 x64
- Python **3.10+**，推荐 3.12（安装时勾选 “Add Python to PATH”）
- 不需要游戏也能先看内置示例账号
- 如果要实时提取：已安装并登录的 PC 国服客户端
- 如果要手机端：Android 手机/模拟器 + `adb`（可选）

> 普通用户**不需要** `dataMiner`、`Portrait_showcase`、UnityPy 或游戏解包工具。  
> 仓库已经带好图鉴、榜单数据和头像；实时读取账号走 Frida/XLua，也不会调用这些工具。

## 1. 安装

### 方式 A：下载 ZIP

1. 打开 https://github.com/TenshiInHeaven/Gf1_AccountEval
2. 点 **Code → Download ZIP**
3. 解压到任意目录，例如 `D:\Gf1_AccountEval`
4. 双击 `build.bat`

第一次会自动创建 `.venv` 并安装依赖，需要几分钟。  
如果没有检测到 Python 3.10+，`build.bat` 会询问是否通过 winget 自动安装 Python 3.12；没有 winget 时会打开 Python 下载页。

### 方式 B：git clone

```powershell
git clone https://github.com/TenshiInHeaven/Gf1_AccountEval.git
cd Gf1_AccountEval
build.bat
```

> `build.bat` 会安装运行依赖、跑测试，并生成 PWA 的 `web/data` 与头像副本。  
> 只有你要运行头像/Spine 提取脚本时，才需要用 `build.bat --with-extract` 安装 UnityPy；它**不会自动重新提取素材**，提取命令仍需按 README 的「重建数据 / 头像」手动执行。

## 2. 打开桌面版

双击：

```text
run.bat
```

或者：

```powershell
.\run.ps1
```

第一次启动会载入**示例账号**。  
这时不需要游戏，可以先熟悉界面。

## 3. 读取你的账号

### 方式 A：从运行中的 PC 游戏实时读取

1. 启动《少女前线》PC 客户端并登录
2. 进入主界面（能看到战斗、编成、仓库等）
3. 保持游戏窗口在前台
4. 在工具右上角点 **「提取账号」**
5. 选择 **方式 A · 从运行中的游戏提取**
6. 点 **「开始提取」**

成功后会看到 UID、昵称、等级和仓库数量，并自动保存一份快照到 `snapshots/`。

如果提示没有数据：

- 确认游戏已经进入主界面，不是启动器/登录界面
- 确认游戏窗口在前台
- 当前客户端版本如果更新，XLua 偏移可能失效；请改用下面的快照导入

### 方式 B：导入快照

1. 点 **「提取账号」**
2. 选择 **方式 B · 导入快照 JSON**
3. 选择 `account_*.json`

之前从本工具导出的、或从 Android 端导出的快照都可以。

### 方式 C：Android 模拟器 HTTPS 抓包（无需 root）

这是与 targetForge 同类的 MITM 代理路线：不读进程，抓登录后的 `Index/index` 全量账号响应。

```powershell
build.bat --with-android
python tools\android_proxy_capture.py --port 18080 --push-ca
```

1. 按工具提示，把模拟器 Wi-Fi 代理设为 **PC 局域网 IP:18080**
2. 在模拟器安装 CA（设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书）
3. 完全退出并重启游戏，重新登录到主界面
4. 看到 `[SNAP]` 后，工具生成 `snapshots/account_android_*.json`
5. 在桌面版「提取账号 → 导入快照」选择该文件

如果已经保存了原始响应，可以离线转换：

```powershell
python tools\android_proxy_capture.py --from-index snapshots\index_xxx.json
```

> 如果客户端启用了证书固定，或者当前区服的登录协议发生变化，抓包可能解不开；这时仍可使用下面的快照导入。

> **CN 复活版 / PC 继承客户端：支持，但必须全新登录。**  
> 抓包期间要在游戏里退出登录 / 切换账号并重新输入账密，让日志出现 `Index/getUidPC` → `[KEY] uid/sign`；只重启客户端不会产生新的登录包，sign 为空，`Index/index` 无法解密。

### 方式 D：Android 模拟器显式快照 fallback

如果你的模拟器已经开启 ADB：

1. 打开工具 → **提取账号**
2. 在 Android ADB 区域检测设备
3. 启动游戏，或手动把 `gf_account_snapshot.json` 放到 `/sdcard/Download/`
4. 点 **拉取快照**

## 4. 看结果

- **总览**：账号等级、四维总分、雷达图、短板建议
- **人形 / 妖精 / 融合势力 / 装备**：分维度列表
- **强度筛选**：可以同时选择多个档位，例如 `SS + S`
- **点击卡片**：查看每一份复制/每个单位的等级、技能、装备、编队等详情
- **图鉴**：查看全部单位，区分已拥有/未拥有
- **设置**：账号来源、快照路径、项目说明

融合势力头像是从游戏 Spine 资源提取的战场 Q 版小全身，少数没有独立 Q 版模型的 SWAP/特殊单位会回退到官方小图。

## 5. 手机 / PWA 版

在电脑上双击：

```text
run_web.bat
```

浏览器会打开 `http://127.0.0.1:8770/`。

### 安装到 Android

推荐用 `adb reverse`，让手机访问电脑的 localhost：

```powershell
adb reverse tcp:8770 tcp:8770
```

然后在手机 Chrome 打开：

```text
http://localhost:8770/
```

浏览器菜单里选择 **「安装应用 / 添加到主屏幕」**。  
PWA 支持离线缓存；账号数据通过导入 `account_snapshot.json` 获取，PWA 本身不读取游戏进程。

## 6. 常见问题

### 提示找不到 Python

安装 Python 3.12 x64，并勾选 **Add Python to PATH**，然后重新运行 `build.bat`。

### PowerShell 不允许运行脚本

直接双击 `run.bat` / `run_web.bat` 即可，它们会绕过执行策略调用 `.ps1`。

### 实时提取没有响应

- 游戏必须在主界面，且保持前台
- 如果还是失败，使用「导入快照」
- 游戏客户端更新后，实时 hook 可能需要适配；快照导入不受影响

### 快照里的 UID 和账号信息会被上传吗？

不会。快照只保存在本机 `snapshots/`，`.gitignore` 已排除该目录；本工具没有上传逻辑。

## 7. 版权

- 代码、脚本、文档、数据表：**MIT**
- `assets/`、`web/assets/`、`web/icons/`、`docs/screenshots/` 和根目录榜单图片：**不属于 MIT**，版权归 Sunborn / 散爆及各自权利人，仅用于个人非商业展示

详见 [LICENSE](LICENSE) 和 [ASSETS_LICENSE.md](ASSETS_LICENSE.md)。
