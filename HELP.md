# Gf1_AccountEval 使用帮助

这个帮助分为两部分：

1. **正常使用流程（PC）**
2. **安卓端流程（模拟器 / 手机）**

> 本工具只读取账号数据并做本地评分。  
> 不上传账号、不写入游戏内存、不修改账号。  
> 抓包只读取流量；是否继续操作账号（例如靶机注入）由 targetForge 等独立工具负责。

---

## 一、正常使用流程（PC）

### 1. 安装

1. 下载仓库 ZIP 并解压
2. 双击 `build.bat`
3. 等待 Python 环境、依赖、测试准备完成
4. 双击 `run.bat` 启动桌面版

如果已经装好，以后只需要 `run.bat`。

### 2. 提取账号

启动后点右上角 **「提取账号」**，有两种方式：

#### 方式 A：实时提取

适用条件：

- PC 国服客户端已经启动并登录
- 游戏和本工具在同一台 Windows 机器

步骤：

1. 点 **「提取账号」**
2. 选择 **实时提取**
3. 工具通过 Frida / XLua 只读读取 `CS.GameData`
4. 等待出现账号总览
5. 提取完成后会自动保存 `snapshots/account_*.json`

#### 方式 B：导入快照

适用条件：

- 已经有之前导出的 `account_snapshot.json`
- 或者从 Android 端抓到的快照

步骤：

1. 点 **「提取账号」**
2. 选择 **导入快照**
3. 选择 `snapshots/account_*.json`
4. 等待载入完成

### 3. 查看评分

左侧导航：

- **总览**：四维评分、下一步建议
- **人形**：仓库人形、三改/常用好手
- **妖精**：空降与战略妖精储备
- **融合势力**：铁血捕获单位
- **装备**：目标个数 vs 当前个数
- **图鉴**：全部单位与拥有状态
- **设置**：数据来源、评分口径

当前账号可在窗口右上角点 **「导出账号」**，把载入的原始快照 JSON 另存为文件；之后可用「导入快照」恢复。

人形 / 妖精 / 融合势力支持：

- 三改与原型合并为同一单位，点开明细可看到原型 / 三改的逐条记录
- 多选强度筛选
- 排序：综合推荐度 / 萌新推荐度 / 游戏编号 / 星级
- 卡片右上角星标收藏；「只看收藏」筛选；设置页可导出收藏 JSON
- 逐条复制详情

装备页点 **「调整对应规则」** 可以修改三个分区（配件 / 子弹 / 人形）的目标数量和 match JSON，也支持导入 / 导出规则 JSON；保存到本地 `equipment_rules.local.json`，不会改仓库默认数据，并会立即重新计算。  
`高穿` 当前定义为 **500 穿甲值**，对应第三方穿甲弹；可用 `armor_piercing_min: 500` 匹配。

装备页下方新增 **机动装甲（坦克 / 战术人型机甲）组件**，可按老吴仙人 / 归海临渊 / 秋水Ameth 三套方案筛选，组件分为必需 / 部分方案 / 完全fw。

设置页 **「评分数据（可导入 / 导出）」** 可以导出人形 / 妖精 / 融合势力全部档位与萌新推荐。  
修改 JSON 后直接导入即可更新评分，不需要重新打包；`recommend` 支持 `gold / green / blue / white / gray`，分别显示金色、绿色、蓝色、白色、灰色渐变卡面。  
启动时只自动读取本地 `app/data/tierlists/*.local.json`；导出的 `ratings_export.json` 不会自动加载，需要在设置页手动导入。

### 4. 导出 / 备份

提取或导入后，快照默认在：

```text
snapshots/account_*.json
```

这个 JSON 就是后续 Android 抓包的导入文件。
备份时直接复制它即可，不要复制整个游戏目录。

---

## 二、安卓端流程

安卓端有两种用法：

1. **Android 模拟器 + PC 抓包**（推荐，不需 root）
2. **Android 手机 + PC 局域网抓包**（不需 root）

> 安卓端**不读取进程**。  
> 读取游戏进程需要 root + Frida/注入，风险高，也不需要；代理抓包拿到的是同一份 `Index/index` 账号数据。

### 一键抓包（推荐）

桌面端点 **「提取账号」→「一键抓包」**：

1. 自动检测 ADB / 模拟器
2. 选择区服：**台服 / 日服 / 美服 / 国服复活版**
3. 自动选择本地端口，并配置 `adb reverse`、代理和桥接
4. 点 **「开始抓包」**
5. 游戏启动后：台服 / 日服 / 美服重启即可；国服复活版 **退出登录 / 切换账号 → 重新输入账密**
6. 等待出现 `[KEY]` 和 `[SNAP]`，自动载入账号

只有 **国服复活版** 会额外处理 `18765/18766` 本地桥接；其他区服走普通代理路径。

如果桌面端按钮不可用，仍可使用下面的命令行方式。

### 命令行方式（备用）

Android 抓包工具：

```text
tools/android_proxy_capture.py
```

桌面端内置实时提取 / 快照导入；命令行方式适合排查问题或自定义端口。  
抓包完成后，生成的快照可以在桌面端导入。

---

### 2.1 安装 Android 抓包依赖

在项目根目录执行：

```powershell
build.bat
```

会安装：

- `mitmproxy`
- `cryptography`
- `gflzirc`

如果已经安装过，可以跳过。

---

### 2.2 Android 模拟器 + PC 抓包

> 桌面端「一键抓包」已经自动完成下面的代理、`adb reverse`、端口和桥接配置；本节保留手动流程，便于排查问题或自定义环境。

#### 适用

- MuMu / LDPlayer / BlueStacks / Nox 等安卓模拟器
- 国服、台服、日服或 CN 复活版
- 不需要 Android root

#### 第一步：启动抓包工具

在项目根目录打开 PowerShell：

```powershell
.\.venv\Scripts\python.exe tools\android_proxy_capture.py --port 18080 --host 0.0.0.0 --push-ca
```

工具会打印：

```text
PC 局域网 IP:18080
CA 证书路径
```

> `--push-ca` 会把 CA 推到模拟器的 `Download` 目录。  
> 只抓 HTTP 的 `Index/index` 时，CA 不是必须的；  
> 如果游戏有 HTTPS 登录包，或者出现 TLS 握手失败，再安装 CA。

#### 第二步：让模拟器走 PC 代理

##### 方式 A：Wi-Fi 代理（简单）

在模拟器里：

```text
设置 → Wi-Fi → 当前网络 → 修改网络 → 代理 → 手动
主机名：PC 的局域网 IP
端口：18080
```

不要填 `127.0.0.1`，模拟器里的 `127.0.0.1` 是模拟器自己。

##### 方式 B：adb reverse（更稳，适合 MuMu）

先确认 adb 能找到设备：

```powershell
adb devices
```

然后：

```powershell
adb reverse tcp:18080 tcp:18080
adb forward tcp:18765 tcp:18765
adb forward tcp:18766 tcp:18766
adb shell settings put global http_proxy 127.0.0.1:18080
```

说明：

- `adb reverse`：模拟器访问自己的 `127.0.0.1:18080` 时转发到 PC 的抓包工具
- `adb forward 18765/18766`：保留游戏自己的本地桥接端口
- 全局代理让游戏 HTTP 请求进入抓包工具

> 不同模拟器的 adb 路径不同。MuMu 常见路径：  
> `D:\Program Files\Netease\MuMu\nx_device\12.0\shell\adb.exe`

#### 第三步：安装 CA（可选，但推荐）

如果工具打印的 CA 已经推到 `Download`：

1. 打开模拟器 **设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书**
2. 选择 `Download` 里的 `ca.crt`
3. 给它起个名字，例如 `GF Capture`

Android 7+ 默认不信任用户 CA。  
如果游戏只抓 HTTP，可以跳过；如果 HTTPS 包握手失败，需要：

- 模拟器开启 root，把 CA 安装到系统证书目录
- 或使用 targetForge 的 CA 安装流程

#### 第四步：登录（区服不同）

- **台服 / 日服 / 美服**：抓包工具保持运行，重启游戏即可，和 PC 国服流程一样
- **国服复活版**：在游戏里 **退出登录 / 切换账号 → 重新输入账密**

国服复活版只有全新登录，日志里才会出现：

```text
POST Index/getUidPC
[S2C] getUidPC
[KEY] uid/sign 已获取
```

之后才会出现：

```text
POST Index/index
[S2C] Index/index
[SNAP] 已写入 snapshots/account_android_*.json
```

#### 国服复活版为什么必须大退

台服 / 日服 / 美服重启客户端即可；但国服复活版如果只是：

```text
关闭游戏
→ 重新打开
```

游戏可能直接复用缓存登录态，自动回到主界面，**不会重新走 `getUidPC`**。  
这时抓包工具只能看到 `Index/index` 密文，没有当前 `sign`，无法解密。

所以国服复活版请认准：

```text
抓包运行中 + 退出登录/切换账号 + 重新输入账密
```

不是“重启客户端”。

#### 第五步：停止并恢复

看到 `[SNAP]` 后，在抓包窗口按 `Ctrl+C` 停止，然后恢复模拟器：

```powershell
adb shell settings put global http_proxy :0
adb reverse --remove tcp:18080
adb forward --remove tcp:18765
adb forward --remove tcp:18766
```

如果安装了 CA，按需在模拟器里删除测试证书。

#### 第六步：导入快照

抓包成功后生成：

```text
snapshots/account_android_*.json
```

回到桌面端：

```text
提取账号 → 导入快照 → 选择该 JSON
```

---

### 2.3 Android 手机 + PC 抓包

不需要 root，前提是手机和 PC 在同一局域网。

1. PC 上启动抓包工具：

```powershell
.\.venv\Scripts\python.exe tools\android_proxy_capture.py --port 18080 --host 0.0.0.0 --push-ca
```

2. 手机 Wi-Fi 代理指向：

```text
PC 局域网 IP:18080
```

3. 手机安装 CA（如果抓 HTTPS）：

```text
设置 → 安全 → 加密与凭据 → 安装 CA 证书
```

4. 国服复活版：在游戏里 **退出登录 / 切换账号 → 重新输入账密**；其他区服：重启游戏即可

5. 看到 `[KEY]` 和 `[SNAP]` 后停止工具，把手机代理改回“无”

6. 把 `snapshots/account_android_*.json` 传到桌面端导入

> 部分手机系统会限制用户 CA 被游戏信任。  
> 如果 HTTPS 包抓不到，不要强行 root；优先用模拟器 + PC 抓包。

---

## 三、常见问题

### Q1：抓包只看到 `Index/index`，没有 `[KEY]`

原因：游戏复用了缓存登录态，没有重新走登录。

处理：

```text
抓包运行中 → 游戏内退出登录/切换账号 → 重新输入账密
```

不要只重启客户端。

### Q2：出现 `[WARN] # 包解密失败`

说明当前没有 sign，或者 sign 已过期。

检查：

- 是否在抓包运行期间完成全新登录
- 日志里有没有 `Index/getUidPC`
- 有没有 `[KEY] uid/sign`

### Q3：模拟器里打不开网页 / 连不上代理

- 确认手机/模拟器和 PC 在同一网络
- 确认 Windows 防火墙允许 18080 / 8770
- 模拟器里不要用 `127.0.0.1` 访问 PC，除非用了 `adb reverse`

### Q4：TLS 握手失败

- 没有安装 CA，或 CA 没被系统信任
- Android 7+ 用户 CA 不一定被游戏信任
- 只抓 HTTP 的 `Index/index` 可以先不装 CA；需要 HTTPS 时用系统 CA

### Q5：CN 复活版可以抓吗

可以，但必须**全新登录**：

```text
抓包生效 → 退出登录/切换账号 → 重新输入账密
```

只重启客户端会复用缓存，抓不到 sign。

### Q6：需要 root 吗

不需要。

- PC + 模拟器抓包：不需要 Android root
- PC + 手机抓包：不需要 root

只有两种情况需要 root：

- 把 CA 装进系统证书目录
- 读取游戏进程内存（本工具不建议）

---

## 四、数据与隐私

- 抓包数据只在本机处理
- 快照默认保存在 `snapshots/`
- `snapshots/` 和 `raw/` 已加入 `.gitignore`，不会被提交
- 不要把包含 UID、签名、账号数据的快照发到公开仓库
- 抓包结束后建议清空代理和测试 CA

---

## 五、相关文件

- [README.md](README.md)：项目总览
- [USAGE.md](USAGE.md)：安装与使用说明
- [tools/android_proxy_capture.py](tools/android_proxy_capture.py)：Android 抓包工具
