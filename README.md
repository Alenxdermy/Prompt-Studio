# Prompt Studio

Prompt Studio 是一个把简短需求整理成结构化 AI 提示词的 Web 工具。填写任务目标和可选背景后，工作台会生成可复制的提示词，并支持选择写作风格、保留可替换变量和切换页面背景。

## 功能

- 输入任务目标、背景信息和目标对象
- 选择清晰均衡、细节充分、简洁直接或创意发散风格
- 选择是否在结果中保留 `{{变量名}}` 占位符
- 流式显示生成结果，支持复制和再次生成
- 网页内配置模型服务商、API Key、模型名称和接口地址，并可测试连通性
- 提供暖纸、薄荷、晴空、浅樱四种背景
- 未配置模型密钥时，可使用本地演示生成器
- 配置 OpenAI 兼容 API 后，可切换到真实大模型生成

## 是否需要调用大模型 API？

**当前版本不配置 API 也能启动和体验。**此时运行的是后端内置的本地演示生成器：它会把输入套入一份结构化提示词模板，不会调用大模型，因此不会产生模型 API 费用；但生成内容不会像真正的大模型那样深入理解任务并灵活创作。

如果你希望 AI 根据不同任务实际分析、匹配并撰写提示词，就需要配置一个大模型 API Key。网页的“模型设置”支持 OpenAI、DeepSeek、通义千问、硅基流动、Kimi、智谱、OpenRouter 和自定义 OpenAI 兼容接口。原生格式的 Gemini 等接口暂不支持。调用费用和免费额度由所选模型服务商决定。

## 环境要求

- Node.js 22（建议使用当前 LTS 版本）
- Python 3.10 或更高版本
- 安装依赖时需要网络连接

## 本地启动

在项目根目录打开两个 PowerShell 终端。

### 1. 启动后端

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如果 PowerShell 阻止激活虚拟环境，也可以不激活它，直接用虚拟环境中的 Python 执行安装和启动命令：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 启动前端

在第二个终端中，从项目根目录运行：

```powershell
Set-Location .\frontend
npm install
npm run dev
```

打开 Vite 输出的本地地址，通常是 <http://localhost:5173/>。如果端口已被占用，Vite 会自动选择另一个端口并在终端显示实际地址。前端开发服务器会把 `/api` 请求转发到 `http://127.0.0.1:8000`。

## 在网页中接入真实大模型（推荐）

启动前后端后，打开网页里的“模型设置”，选择服务商，填写服务商提供的 API Key 和模型名称，点击“测试连接”。预设会填入接口地址与常见模型名，具体模型名和可用性以服务商账号及文档为准。自定义接口必须使用 HTTPS，并兼容 OpenAI Chat Completions 格式。

API Key 只保存在当前页面内存，刷新或关闭页面后需要重新填写。连接测试会发送一条简短请求；生成时，任务内容会发送给对应模型服务商。后端不把用户提交的密钥写入数据库或日志。公开部署时请使用 HTTPS，并只向可信的项目后端提交密钥。

## 通过后端环境变量配置默认模型（可选）

部署者也可以在**启动后端的同一个 PowerShell 窗口**配置服务端默认模型：

```powershell
Set-Location .\backend
$env:OPENAI_API_KEY = "替换为你的 API Key"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_MODEL = "gpt-4o-mini"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

上面模型名称和地址是 OpenAI 的示例。使用其他兼容服务时，请按服务商文档替换 `OPENAI_BASE_URL`、`OPENAI_MODEL` 和 `OPENAI_API_KEY`。只有在网页未填写用户 API Key 时，后端才使用环境变量中的默认模型。

设置环境变量只对当前终端会话有效。关闭该窗口后重新启动后端时，需要再次设置。不要把真实密钥写进源码、README 或公开仓库中。

检查当前运行模式：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

返回 `mode: demo` 表示本地演示模式；返回 `mode: api` 表示检测到 API Key，生成请求将调用模型服务。

## 项目结构

```text
backend/
  app/main.py          FastAPI 健康检查、演示生成器、模型 API 与 SSE 接口
  requirements.txt     Python 依赖
frontend/
  src/App.vue          主界面
  src/stores/prompt.ts  表单状态、SSE 流读取和会话历史
  src/style.css        响应式布局与背景主题
  vite.config.ts       前端开发服务器与后端 API 代理
```

## API 接口

### `GET /api/health`

返回后端状态和运行模式，例如：

```json
{"status":"ok","mode":"demo"}
```

### `GET /api/providers`

返回网页模型设置页支持的服务商名称、默认接口地址和示例模型。

### `POST /api/models/test`

使用请求中的临时配置调用模型，检查 API Key、模型名称和接口连通性。该请求会产生一次简短的模型调用，可能计入服务商用量。

### `POST /api/generate/stream`

以 Server-Sent Events（SSE）流式返回结果。请求可选附带 `provider`、`base_url`、`model`、`api_key`；这些配置只用于当前请求。基本请求示例：

```json
{
  "topic": "为一款习惯养成 App 写推广文案",
  "context": "产品支持每日打卡和每周复盘",
  "audience": "希望培养学习习惯的大学生",
  "style": "balanced",
  "include_variables": true
}
```

`style` 可选值：`balanced`、`detailed`、`concise`、`creative`。

## 数据与隐私说明

- 当前没有数据库；输入内容不会由本项目写入服务器数据库。
- 最近生成记录保存在当前页面内存中，刷新页面后会清空。
- 背景选择保存在浏览器的本地存储中。
- 使用真实模型模式时，生成所需的输入内容会发送给你配置的模型服务商，并受其服务条款和隐私政策约束。
- 页面提交的 API Key 只用于本次连接测试或生成请求，不会持久化。公开部署时应使用 HTTPS，并为实际用户规模增加认证、限流和滥用防护。
- 自定义模型接口只接受 HTTPS 公网地址；本机和内网地址会被拒绝，避免后端代理访问私有网络。

## 后端接口测试

```powershell
Set-Location .\backend
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

## 生产构建

```powershell
Set-Location .\frontend
npm run build
```

构建产物会输出到 `frontend/dist/`。当前项目提供的是本地开发与 MVP 运行配置；正式公开部署前，需要配置生产环境的前端 API 地址、后端 CORS 来源、HTTPS、密钥管理和使用限额。
