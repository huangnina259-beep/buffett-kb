# 复利国 · The Compounder

复利国是一套面向价值投资学习、研究和复盘的 AI 工作台。项目把巴菲特股东信、查理·芒格著述、Howard Marks 备忘录、李录演讲与相关书籍整理为本地知识库，并通过 RAG 和对话式教学帮助用户理解投资原则、分析公司和记录投资思考。

> 本项目用于学习与研究，不构成任何投资建议。

## 当前能力

React 工作台位于 `/app`，包含：

- **每日简报**：按全球商业、美股、A 股、港股、价值信号和宏观周期生成摘要。
- **持仓分析**：展示研究笔记、估值假设、观察清单和更新记录；当前部分内容为项目内置数据。
- **思维训练营**：七章价值投资理论课程，通过苏格拉底式对话推进。
- **投资教练**：围绕商业模式、护城河、财务质量、管理层和估值引导公司分析，并保存分析记录。
- **知识库问答**：检索原始语料，生成带来源引用的回答和后续问题。
- **模型设置**：在页面新增供应商和模型、填写 Key、测试连接并为各任务选择模型。

项目还保留旧版独立页面：

- `/qa`：知识库问答
- `/gym`：案例训练
- `/analyst`：公司分析
- `/tutor`：理论课程
- `/coach`：投资教练

## 技术架构

```text
React / Vite                 静态 HTML 页面
       │                           │
       └──────── FastAPI API ──────┘
                     │
          RAG / Tutor / Coach / Analysis
             │                  │
       ChromaDB + Embedding      第三方生成模型 API
                     │
             SQLite / PostgreSQL
```

主要技术：

- 后端：Python 3.11、FastAPI、Uvicorn
- 前端：React 18、TypeScript、Vite；另有旧版原生 HTML/CSS/JavaScript
- 检索：ChromaDB、云端 Embedding API；Sentence Transformers 为可选离线模式
- 状态存储：SQLite，部署时可使用 PostgreSQL
- 部署：Docker、Railway、GitHub Pages

## 多模型架构

所有生成式 AI 功能现已通过统一 Generation Gateway 调用，业务模块不再直接创建 Anthropic 或 OpenAI 客户端。知识库入库与查询则通过独立的 Embedding Gateway 生成向量，ChromaDB 只负责存储和检索。

当前支持：

- Anthropic 原生 Messages API；
- OpenAI Chat Completions 与 Embeddings API；
- Google Gemini 的 OpenAI 兼容入口；
- MiniMax、DeepSeek、通义千问、智谱、Moonshot、OpenRouter 等兼容 OpenAI 协议的服务；
- 任意兼容 `/embeddings` 的第三方向量服务；
- 兼容 `/rerank` 的第三方重排服务；
- 按任务配置主模型、备用模型和模型参数；
- 统一普通响应、流式输出、错误处理与结构化 JSON 模式；
- Embedding profile、索引 manifest 与模型/维度一致性校验。

生产环境以**云端向量化为默认方案**，不安装 PyTorch、不下载模型权重，也不要求 GPU 或高性能 CPU。本地 Sentence Transformers 仅在显式配置并安装可选依赖后启用。

详细设计、验收范围和后续阶段见 [多模型接入重构 PRD](docs/PRD_MULTI_MODEL.md)。

## 目录结构

```text
buffett-kb/
├── server.py                 # FastAPI 应用与 API 路由
├── start.py                  # 本地/部署启动入口，必要时后台构建向量库
├── src/
│   ├── rag.py                # 检索、上下文组装与知识库回答
│   ├── tutor.py              # 七章理论课程引擎
│   ├── coach.py              # 投资教练引擎
│   ├── ai_gateway.py         # 生成模型适配器与任务路由
│   ├── embedding_gateway.py  # 云端/可选本地向量化适配器
│   ├── vector_store.py       # ChromaDB 与索引 manifest 校验
│   ├── database.py           # 教练状态和公司档案
│   ├── ingest_md.py          # Markdown 语料入库
│   └── ingest.py             # PDF 等语料入库
├── react-app/                # React 工作台
├── frontend/                 # 旧版静态页面
├── data/clean_mds/           # 清洗后的 Markdown 知识库
├── data/pdfs/                # PDF 原始资料
├── docs/                     # 产品与设计文档
├── Dockerfile
└── requirements.txt
```

## 本地运行（Windows / PowerShell）

### 1. 环境要求

- Python 3.11
- Node.js 20（需要重新构建 React 前端时）
- Git

### 2. 创建虚拟环境

```powershell
git clone https://github.com/huangnina259-beep/buffett-kb.git
cd buffett-kb
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 使用清华源安装 Python 依赖

```powershell
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

默认安装使用云端 Embedding API，不会安装 PyTorch 或本地模型。如明确需要离线向量化，再安装可选依赖：

```powershell
python -m pip install -r requirements-local.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 在页面配置模型（推荐）

先启动服务并打开 <http://127.0.0.1:8000/app>，进入左侧的“模型设置”。页面已预置 WTSHT 的 OpenAI 兼容地址及以下模型：

- `DeepSeek-V4-Flash-YR`：生成模型
- `Qwen3-Embedding-8B`：向量模型
- `Qwen3-Reranker-0.6B`：重排模型
- `Qwen3.8-27b`：生成模型

在页面手动填写 API Key 后，可以逐个点击“测试”，确认成功后再“保存并应用”。Key 保存在后端忽略提交的 `database/ai_settings.json`，普通配置接口只返回 `has_api_key`，不会把 Key 回传给浏览器，也不会写入 localStorage。

页面同时支持新增/修改供应商、模型 ID、模型能力、任务路由及向量集合名。首次保存页面配置后，运行时优先使用页面配置；在此之前仍兼容原有环境变量，方便旧部署平滑升级。

> 更换向量模型必须使用新的向量集合并重新导入知识库。测试模型和保存配置不会自动发起全量向量化，以避免意外产生大量 API 调用和费用。

页面中的“向量维度”用于校验供应商实际返回的向量长度，第三方 OpenAI 兼容服务默认不会收到 `dimensions` 参数。只有明确支持 Matryoshka 输出裁剪的模型才应启用请求维度参数。

### 5. 旧部署的环境变量兼容方式

复制示例并填写所选供应商的密钥：

```powershell
Copy-Item .env.example .env
```

最小 Claude + OpenAI Embedding 配置示例：

```dotenv
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-6
AI_API_KEY_ENV=ANTHROPIC_API_KEY
ANTHROPIC_API_KEY=your_anthropic_api_key

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY_ENV=OPENAI_API_KEY
OPENAI_API_KEY=your_openai_api_key
VECTOR_COLLECTION=buffett_kb_openai_v1
```

接入其他 OpenAI 兼容生成或向量服务时，设置对应的 `AI_BASE_URL` 或 `EMBEDDING_BASE_URL`。生成模型使用 `AI_PROFILES_JSON`、`AI_TASKS_JSON` 注册供应商并按任务路由；向量模型使用 `EMBEDDING_PROFILES_JSON` 注册多家供应商，通过 `EMBEDDING_ACTIVE_PROFILE` 为当前索引选择一个 profile。完整模板见 `.env.example`。

可选数据库配置：

```dotenv
DATABASE_URL=sqlite:///./coach.db
```

`.env` 已被 Git 忽略，请勿提交任何真实密钥。

### 6. 构建 React 前端（按需）

仓库包含已构建的 `react-app/dist`。修改 React 源码后需要重新构建：

```powershell
cd react-app
npm install
npm run build
cd ..
```

### 7. 启动

```powershell
python start.py
```

打开：

- 工作台：<http://127.0.0.1:8000/app>
- 首页：<http://127.0.0.1:8000/>
- 健康检查：<http://127.0.0.1:8000/health>

首次启动若当前向量集合不存在，服务仍会正常启动，但不会默认执行可能产生费用的云端全量向量化。先在模型设置页测试向量接口，再手动运行 `python src/ingest_md.py`。确实需要启动时自动导入时，可显式设置 `AUTO_INGEST=true`。

## 前端开发模式

先启动 FastAPI，再运行 Vite：

```powershell
cd react-app
npm run dev
```

默认开发地址为 <http://127.0.0.1:5173>。FastAPI 已允许本地 Vite 开发端口跨域访问。

## 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 服务健康检查 |
| GET | `/api/ai/settings` | 获取脱敏后的页面模型配置 |
| PUT | `/api/ai/settings` | 保存并应用页面模型配置 |
| POST | `/api/ai/test` | 测试生成、向量或重排模型连接 |
| POST | `/query` | React 知识库问答 |
| POST | `/api/chat` | 非流式 RAG 问答 |
| POST | `/api/chat/stream` | SSE 流式 RAG 问答 |
| POST | `/api/tutor/stream` | SSE 理论课程 |
| POST | `/api/coach/stream` | SSE 投资教练 |
| POST | `/gym/feedback` | 案例单轮反馈 |
| POST | `/gym/synthesis` | 案例综合报告 |
| POST | `/analyst/feedback` | 公司分析单轮反馈 |
| POST | `/analyst/synthesis` | 公司分析综合报告 |
| POST | `/api/digest` | 每日简报生成 |

## 知识库

主要语料位于 `data/clean_mds/`，包括：

- Warren Buffett 股东信和股东大会记录；
- Charlie Munger 演讲与 Daily Journal/Wesco 会议记录；
- Howard Marks 备忘录；
- Li Lu 演讲、文章和中英文材料；
- 部分价值投资经典书籍。

默认使用云端 Embedding 配置；首次页面保存后，实际模型、接口和集合名由模型设置页决定，环境变量仅作为旧配置兼容路径。本地 ChromaDB 和页面模型配置保存在 `database/`，该目录不会提交到 Git。

入库进度按向量集合分别记录为 `ingestion_summary.<collection>.json`，切换模型或集合时不会错误复用旧集合的完成记录；中断后再次执行同一集合则会从已完成文件继续。

每个集合都会生成独立的 `<collection>.manifest.json`，记录供应商、模型和维度。切换向量模型时必须使用新的 `VECTOR_COLLECTION` 重建索引，不能用新模型查询旧模型生成的向量。

仓库升级前生成的 `buffett_kb` 没有 manifest。要临时继续使用该旧索引，必须明确配置：

```dotenv
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
LOCAL_EMBEDDING_ALLOW_DOWNLOAD=false
VECTOR_COLLECTION=buffett_kb
```

并安装 `requirements-local.txt`。生产环境建议配置云端 Embedding，使用新集合完成一次重建。

需要手动重建 Markdown 向量库时：

```powershell
python src/ingest_md.py
```

## 部署

### Railway / Docker

`Dockerfile` 不安装 PyTorch，也不下载本地 embedding 模型。它会安装 Python 与 Node.js 依赖、构建 React 前端，并通过 `python start.py` 启动服务。Railway 使用 `/health` 作为健康检查路径。

生产环境至少需要设置相应模型 API Key；Coach 的持久化数据建议配置 PostgreSQL `DATABASE_URL`。

### GitHub Pages

`.github/workflows/deploy.yml` 会构建并发布 `react-app/dist`。GitHub Pages 只能托管前端，AI 与数据库功能仍需连接可访问的 FastAPI 后端。

## 当前已知限制

- 当前生成网关实现 Anthropic 与 OpenAI 兼容协议；其他非兼容私有协议仍需新增适配器。
- 向量网关当前实现 OpenAI 兼容协议与可选 Sentence Transformers；不兼容 `/embeddings` 的供应商需要新增适配器。
- 项目同时存在 React 工作台与旧版静态页面，部分功能重复。
- React 持仓页面含特定公司的内置研究数据，并非通用持仓管理系统。
- 当前认证与用户隔离能力有限，Coach 和模型设置页默认面向本地单用户；部署到公网前必须增加管理员认证并限制自定义 Base URL。
- 云端首次构建完整向量库可能产生调用费用，并受供应商批量和限流策略影响。
- AI 生成内容可能出错；涉及财务数据和投资判断时必须核对原始来源。

## 开发约定

- 不提交 `.env`、API Key、`database/`、`coach.db` 或虚拟环境。
- 修改 React 源码后运行 `npm run build`。
- 修改模型调用逻辑前，先阅读 [多模型接入重构 PRD](docs/PRD_MULTI_MODEL.md)。
- 新的生成模型或向量模型接入都应通过统一适配器完成，不在业务路由、入库脚本或检索模块中新增供应商专属代码。
- 建议使用功能分支提交并通过 Pull Request 合并。

## License

仓库当前未提供明确的开源许可证。未经仓库所有者确认，不应假设代码或知识库语料可被自由复制、再分发或商用。
