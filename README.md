# DeepSeek Proxy for Claude Code

一键切换 Claude Code 后端为 DeepSeek API 的桌面开关程序。

## 软件优势

- **零配置启动**：双击 `main.pyw` 即用，无需命令行操作
- **双模式灵活切换**：Direct 直连（零延迟，完整功能）+ Proxy 代理（LiteLLM 协议翻译，兼容性好）
- **自动环境管理**：程序负责注册表 + setx 双重写入，退出自动清理，不留残留
- **UI 不卡顿**：所有耗时操作（进程管理、环境变量写入）均放入后台线程，tkinter 主线程保持响应
- **安全退出保护**：窗口关闭 + `atexit` 双重保险，确保端口和变量清理
- **模型级粒度控制**：支持 V4 Flash / V4 Pro / Flash+Think(R1) 三档选择，Direct 模式下 Thin 模式自动设置 EFFORT_LEVEL=max

## 已知使用缺陷

1. **Claude Code 不动态重读环境变量**：CC 启动时读取环境变量，运行期间不变。开关代理后 CC 不会自动切换后端，需重启 CC
2. **Proxy 模式 LiteLLM 启动慢**：首次启动需 10-15 秒绑定 4000 端口，UI 会显示 "Starting..." 等待
3. **Proxy 模式内存占用高**：LiteLLM 1.87 在 Windows 上启动峰值内存 500MB+
4. **切换模式时 CC 会断连**：Proxy 模式关闭或切换到 Direct 都会导致已运行的 CC 断连，需等待 30 秒+ 自动重试或 Ctrl+C 重进
5. **Direct 模式 V4 Flash 默认开启 thinking**：小请求可能 thinking tokens 吃满导致无文本输出，建议小任务用 Pro 或关闭 thinking
6. **仅支持 Windows**：依赖 `winreg` 注册表操作和 `taskkill` 进程管理
7. **关闭代理时 VS Code 插件跳转登录页**：环境变量清除后 VS Code 中的 CC 插件自动回退 Anthropic 原生 API，触发登录

## 快速开始

1. 双击 `main.pyw`
2. 选择**连接模式**：Direct（直连）或 Proxy（代理）
3. 选择**模型**：V4 Flash / V4 Pro / Flash+Think(R1)
4. 点击 **Turn ON**

## 两种模式

| | Direct（推荐） | Proxy（LiteLLM） |
|---|---|---|
| 原理 | 直连 DeepSeek Anthropic 端点 | 本地 LiteLLM 翻译协议 |
| 速度 | 快，无中间层 | 多一跳转发 |
| 功能 | 完整（tool use、thinking） | 部分受限 |
| 依赖 | 无 | 需 Python + LiteLLM |
| 稳定性 | 好 | 偶发端口残留 |

## 架构

### 整体架构

```
┌─────────────────────────────────────────────┐
│              main.pyw (GUI)                  │
│  ┌───────────┐  ┌─────────┐  ┌───────────┐  │
│  │ 模式选择   │  │ 模型选择 │  │ ON/OFF    │  │
│  │ Direct    │  │ V4 Flash │  │  开关     │  │
│  │ Proxy     │  │ V4 Pro   │  │           │  │
│  └───────────┘  └─────────┘  └───────────┘  │
│                                              │
│  环境变量管理 → 注册表 HKCU\Environment       │
│  端口管理     → netstat 检测 / taskkill 清理 │
│  LiteLLM      → subprocess.Popen            │
└─────────────────────────────────────────────┘
```

### 两种模式数据流

**Direct 模式**：直连 DeepSeek 的 Anthropic 兼容端点，无中间层，完整支持 tool-use/thinking/web-search。

```
Claude Code  ────→ api.deepseek.com/anthropic
                  （原生 Anthropic 协议）
```

**Proxy 模式**：LiteLLM 作为本地协议翻译层，将 Claude Code 的 Anthropic 请求转为 OpenAI 协议发给 DeepSeek。

```
Claude Code  ────→ localhost:4000 (LiteLLM) ────→ api.deepseek.com (OpenAI 协议)
                  翻译：Anthropic → OpenAI
```

### 关键组件

- **环境变量管理**：`winreg` 直接写注册表 + `setx` 命令双重设置，保证新进程继承。程序退出时清除所有变量
- **端口检测**：`netstat -ano | findstr :4000`，不靠进程名，直接检测端口监听
- **进程清理**：`taskkill /f /t /im litellm.exe`（树杀父+子）→ `netstat` 扫描 4000 端口残留 → 按 PID 补杀
- **线程模型**：所有耗时操作放入 daemon 线程，主线程只负责 tkinter 事件循环
- **退出保护**：`WM_DELETE_WINDOW` + `atexit.register` 双重保险，`cleanup()` 幂等安全

## 模型映射

| GUI 显示 | Direct 模式 ANTHROPIC_MODEL | Proxy 模式 CC 模型名 | LiteLLM 后端 |
|---------|---------------------------|-------------------|-------------|
| V4 Flash (Fast) | deepseek-v4-flash | claude-sonnet-4-6 | deepseek/deepseek-v4-flash |
| V4 Pro (Powerful) | deepseek-v4-pro | claude-opus-4-6 | deepseek/deepseek-v4-pro |
| V4 Flash + Think (R1) | deepseek-v4-flash + EFFORT=max | - | - |

## 环境变量

程序通过注册表 `HKCU\Environment` 设置以下变量：

| 变量 | Direct 模式值 | Proxy 模式值 |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `api.deepseek.com/anthropic` | `localhost:4000` |
| `ANTHROPIC_AUTH_TOKEN` | DeepSeek API Key | LiteLLM master key |
| `ANTHROPIC_MODEL` | `deepseek-v4-xxx` | `claude-sonnet/opus-4-6` |
| `CLAUDE_CODE_EFFORT_LEVEL` | `max`（Think 模式） | 不设置 |

关闭时自动清除所有变量。

## 迭代记录

### v1.1 (2026-06-06)

**新增**
- 模型选择器（V4 Flash / V4 Pro / Flash+Think）
- Thinking mode 复选框
- Direct 直连模式（去 LiteLLM，直连 `api.deepseek.com/anthropic`）

**修复**
- 端口残留：LiteLLM 子进程未被清理，占 4000 端口。根因是 LiteLLM fork 子进程监听端口，`taskkill /im litellm.exe` 只杀父进程。修复为 `netstat` 检测端口监听 + `taskkill /t` 树杀 + `netstat` 扫描补杀孤儿
- 所有环境变量操作改为后台线程，避免界面卡顿
- 关闭窗口时 atexit 双重保险清理

**Claude Code 切换行为（测试总结）**
1. CC 启动时读环境变量，运行时不重读
2. 先开代理再开 CC → 正常使用
3. 代理 OFF 时开 CC → 走 Anthropic 原生 API（需登录）
4. 先开 CC 再开代理 → 不生效
5. Direct 模式下开关代理不影响已运行的 CC（远端始终在线）
6. Proxy 关代理 → CC 立即断连，需重开代理 + 30 秒重试
7. Proxy → Direct 切换 → CC 断连；Direct → Proxy 切换 → CC 不受影响（保持原连接）

### v1.0 (2026-06-04)

- 基于 LiteLLM 的 Proxy 模式
- ON/OFF 开关
- 全局环境变量设置
- 窗口关闭自动清理
- PowerShell profile 集成

## 依赖

- Python 3.10+
- tkinter（Python 自带）
- LiteLLM（仅 Proxy 模式需要，`pip install litellm[proxy]`）

## 文件结构

```
deepseek-proxy-gui/
├── main.pyw             # 主程序（双击运行）
├── litellm_config.yaml  # LiteLLM 代理配置文件
└── README.md            # 本文件
```
