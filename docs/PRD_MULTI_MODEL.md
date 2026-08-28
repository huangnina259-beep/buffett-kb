# 复利国生成模型与向量模型多供应商重构 PRD

> 文档状态：Draft v1.0
> 目标版本：多模型架构 V1
> 最后更新：2026-08-27
> 本文描述产品需求与建议架构，不代表相关功能已经实现。

## 1. 产品背景

“复利国（The Compounder）”是一套面向价值投资学习和研究的 AI 工作台。系统以巴菲特、芒格、Howard Marks、李录等人的原始资料为知识库，通过 RAG、结构化提示词和对话式教学，提供知识问答、投资课程、公司分析、案例训练、投资教练与每日简报等能力。

现有系统的核心生成式 AI 链路直接依赖 Anthropic SDK、`ANTHROPIC_API_KEY` 和固定 Claude 模型；每日简报则单独使用 OpenAI SDK 调用 MiniMax 的 OpenAI 兼容接口。向量化链路同样直接绑定本地 `sentence-transformers/all-MiniLM-L6-v2`：入库和查询均在进程内加载模型，Docker 构建还会安装 PyTorch 并预下载模型。不同业务入口各自创建客户端、读取密钥、指定模型并解析结果，已经形成明显的重复和供应商耦合，也把计算与内存压力转移给了部署机器。

本次重构的目标不是简单地把 Claude 或本地向量模型替换成另一家服务，而是分别建立统一、可配置、可扩展的生成模型网关与向量化网关，让业务能力不再感知具体厂商。生产环境默认使用云端 Embedding API，本地向量化只作为显式启用的开发或离线选项。

## 2. 问题定义

### 2.1 当前问题

1. **供应商耦合**：知识库问答、Tutor、Coach、Gym、Analyst 均直接调用 Anthropic。
2. **模型硬编码**：多个模块直接写死 `claude-sonnet-4-6`，部分模块只支持单独的模型环境变量。
3. **配置分散**：Claude 使用 `ANTHROPIC_API_KEY`，每日简报使用 `MINIMAX_API_KEY`、`LLM_MODEL`、`LLM_BASE_URL`，缺少统一配置模型。
4. **能力假设不统一**：业务代码默认模型支持 system prompt、流式文本和特定 JSON 输出，但没有显式能力声明。
5. **协议不统一**：Anthropic Messages 与 OpenAI Chat Completions 的消息、流事件、错误结构和 token 用量不同。
6. **故障处理不足**：没有统一超时、重试、降级、备用模型和可观测性策略。
7. **密钥治理不足**：缺少配置校验、脱敏展示、连接测试和按用途分配模型的管理入口。
8. **结构化输出脆弱**：Gym、Analyst 依赖模型返回“严格 JSON”，目前主要通过去除代码块后手工解析。
9. **向量模型耦合**：入库、RAG 查询和 Tutor 检索直接实例化同一个本地 Sentence Transformer。
10. **终端资源门槛**：PyTorch、模型下载与本地推理增加镜像体积、冷启动时间、内存和 CPU 负担，普通用户未必具备 GPU 或足够的 CPU 能力。
11. **索引迁移缺失**：系统没有记录索引使用的向量模型、维度和版本，切换模型可能造成不可比较的向量混用。

### 2.2 产品机会

通过统一模型网关，可以：

- 根据质量、成本、速度或可用地区选择模型；
- 接入 Anthropic、OpenAI、Google Gemini、MiniMax、DeepSeek、通义千问、智谱、Moonshot 等服务；
- 接入 OpenRouter、硅基流动等模型聚合平台；
- 接入主流云端 Embedding API，并允许通过标准适配器扩展向量模型供应商；
- 在不要求用户具备 GPU 或高性能 CPU 的情况下完成知识库入库和检索；
- 将本地生成/向量模型保留为可选能力，而非默认依赖；
- 为不同功能分配不同模型，并在故障时自动降级；
- 在不修改业务逻辑的前提下新增供应商。

## 3. 产品目标

### 3.1 核心目标

1. 所有生成式 AI 功能通过统一接口调用模型，不直接依赖某一厂商 SDK。
2. 支持原生供应商适配器和 OpenAI 兼容接口。
3. 支持自定义 `base_url`、API Key、模型 ID 和必要的扩展参数。
4. 支持按业务场景配置主模型和备用模型。
5. 对前端保持统一的普通响应与 SSE 流式事件格式。
6. 在配置错误、限流、超时或供应商故障时提供可理解、可追踪的错误。
7. 保持现有 Claude 配置可继续使用，重构后功能行为不倒退。
8. 向量化模型支持多供应商配置，且生产默认路径不在应用进程内运行模型推理。
9. 索引与 embedding profile 强绑定，模型切换通过新索引重建和原子切换完成。

### 3.2 成功指标

- 100% 的生成式 AI 调用经过统一模型网关。
- 新增一个 OpenAI 兼容供应商只需配置，不需要改业务代码。
- 新增一种非兼容协议时，只新增适配器及测试，不修改业务模块。
- 现有七类 AI 调用场景全部通过回归验收。
- 流式首 token 延迟、总耗时、错误类型和 token 用量可记录。
- 配置与密钥不会出现在前端、日志、Git 仓库或错误响应中。
- 新部署在使用云端向量模型时不需要安装 PyTorch、下载模型权重或使用 GPU。
- 任一向量集合都能追溯其供应商、模型 ID、维度、配置版本和创建时间。

### 3.3 非目标

- 本期不训练或微调自有大模型。
- 本期不替换 ChromaDB，也不改变语料清洗、分块和元数据的业务规则；但会重构 embedding 生成、索引版本和重建流程。
- 本期不建设完整计费系统，只预留成本统计字段。
- 本期不承诺无需适配即可兼容世界上所有私有协议；“支持所有第三方模型”定义见第 4 节。
- 本期不改变投资教学内容、课程体系和核心提示词目标。

## 4. “支持所有第三方模型”的产品定义

生成模型接入范围划分为三层：

1. **原生适配器**：对主流且协议独特的供应商提供一等支持，例如 Anthropic、Google Gemini。
2. **OpenAI 兼容适配器**：任何提供 OpenAI 兼容 Chat Completions 接口的云端、聚合或本地服务，可通过配置直接接入。
3. **扩展适配器**：不兼容上述协议的服务，通过稳定的 Adapter 接口插件化接入。

因此，V1 的“广泛兼容”验收标准是：

- Anthropic Claude 可用；
- OpenAI 官方模型可用；
- Google Gemini 可用；
- 至少两个 OpenAI 兼容第三方服务可通过配置接入；
- 至少一个本地 OpenAI 兼容生成服务可作为可选部署验证，但不作为默认配置；
- 业务层不包含任何供应商专属调用代码。

向量模型接入范围同样划分为三层：

1. **原生向量适配器**：面向 OpenAI/Azure OpenAI、Google、Cohere、Voyage AI、Jina AI 等主流 Embedding API；实际首批名单以实现阶段确认结果为准。
2. **OpenAI 兼容向量适配器**：任何实现兼容 `/embeddings` 接口的云服务、聚合平台或自托管服务可通过配置接入。
3. **扩展向量适配器**：其他协议通过统一 `EmbeddingAdapter` 接口接入。

V1 向量模型验收标准：

- 至少两个不同供应商的云端 Embedding API 可用；
- 至少一个 OpenAI 兼容 `/embeddings` 服务可通过配置接入；
- 入库与查询共用同一个显式 embedding profile；
- 默认生产安装和启动不依赖 PyTorch、Sentence Transformers、本地模型权重或 GPU；
- 本地向量化仅作为可选 profile，不影响云端默认部署。

## 5. 用户与核心场景

### 5.1 用户角色

- **普通用户**：使用问答、课程、教练、分析和简报，不需要理解模型配置。
- **管理员/部署者**：配置供应商、密钥、模型、路由和故障降级策略。
- **开发者**：新增适配器、能力映射和自动化测试。

### 5.2 业务场景清单

| 场景 | 当前入口 | 响应形态 | 关键要求 |
| --- | --- | --- | --- |
| 知识库问答 | `/query`、`/api/chat` | JSON | RAG 引用、追问建议 |
| 知识库流式问答 | `/api/chat/stream` | SSE | searching/token/done/error |
| 理论课程 Tutor | `/api/tutor/stream` | SSE | 长对话、课程状态、元标签解析 |
| 投资教练 Coach | `/api/coach/stream` | SSE | 长对话、结构化 record 标签 |
| 案例逐轮反馈 | `/gym/feedback` | JSON | 严格结构化输出 |
| 案例综合报告 | `/gym/synthesis` | JSON/Markdown | 长文本、引用 |
| 公司分析反馈 | `/analyst/feedback` | JSON | 严格结构化输出 |
| 公司分析综合报告 | `/analyst/synthesis` | JSON/Markdown | 长文本、引用 |
| 每日简报 | `/api/digest` | JSON | 无 RAG、结构化新闻摘要 |

持仓页面当前主要是本地数据和计算，不属于本期模型网关改造范围。

## 6. 核心产品需求

### 6.1 供应商管理（P0）

管理员能够配置多个供应商实例，每个实例包含：

- 唯一 ID 与显示名称；
- 适配器类型：Anthropic、OpenAI、Gemini、OpenAI Compatible、Custom；
- API Base URL；
- API Key 的安全引用；
- 可选组织、项目、API 版本及自定义请求头；
- 启用/停用状态；
- 请求超时、最大重试次数；
- 是否允许日志记录请求元数据；
- 连接测试状态与最近测试时间。

要求：

- API Key 只允许服务端读取；
- 管理界面只展示脱敏值；
- 错误日志不得包含密钥或完整鉴权头；
- 自定义 URL 必须支持 `http://localhost` 等本地部署场景，同时提供生产环境安全提示。

### 6.2 生成模型目录（P0）

每个模型配置至少包含：

- 模型配置 ID；
- 所属供应商实例；
- 供应商侧模型 ID；
- 显示名称；
- 上下文窗口与最大输出 token；
- 默认 temperature、top_p 等参数；
- 能力标签；
- 启用状态；
- 可选成本信息。

V1 能力标签：

- `chat`
- `streaming`
- `system_message`
- `json_output`
- `tool_calling`
- `vision`
- `reasoning`

业务在发起请求前必须校验所选模型是否满足场景需要。

### 6.3 向量化供应商与模型管理（P0）

向量模型使用独立于生成模型的配置目录。每个 embedding profile 至少包含：

- 唯一 profile ID 与显示名称；
- 供应商实例与适配器类型；
- 供应商侧 embedding 模型 ID；
- 向量维度；
- 最大单条输入长度；
- 单批最大条数和 token 限制；
- 文档与查询的 input type/task type（供应商支持时）；
- 归一化策略；
- 超时、重试、并发与批量大小；
- 配置版本和启用状态。

首批能力要求：

- 批量文档向量化；
- 单条或批量查询向量化；
- OpenAI 兼容 `/embeddings` 协议；
- 云端限流重试与指数退避；
- 幂等入库和批次断点续传；
- 可选的内容哈希缓存，避免未变化文本重复计费；
- token/条数、耗时和错误统计。

**默认策略：**

- 生产与普通用户部署默认选择云端 Embedding API；
- 默认 Docker 镜像不安装 PyTorch，不在构建阶段下载模型权重；
- 本地 Sentence Transformers、Ollama Embeddings 等只作为可选 extras/profile；
- 本地模式必须由部署者显式启用，并明确提示 CPU、内存、磁盘和耗时要求；
- 不以本地量化模型作为默认方案，也不假设用户拥有 GPU。

### 6.4 向量索引一致性与迁移（P0）

向量模型与生成模型的降级逻辑不同。不同 embedding 模型生成的向量通常维度、归一化方式和语义空间不同，因此：

- 同一 collection/index 内禁止混用不同 embedding profile 生成的向量；
- 查询必须使用该索引创建时绑定的同一个 profile 和版本；
- 不允许在一次查询失败后直接切换另一向量模型继续搜索旧索引；
- 每个索引必须保存 `provider`、`model_id`、`dimension`、`profile_version`、分块配置、语料版本和创建时间；
- 应用启动和查询前必须校验当前 profile 与索引 manifest 一致；
- 切换向量模型时创建新版本索引，全量或可验证地增量重建，通过检索评估后原子切换别名；
- 旧索引保留可配置的回滚窗口，稳定后再清理。

建议采用蓝绿索引：

```text
buffett_kb_active -> buffett_kb_v1
                         │
新 embedding profile -> buffett_kb_v2（后台重建与评估）
                         │
验证通过后：buffett_kb_active -> buffett_kb_v2
```

模型切换验收不能只比较“能否返回结果”，还需要使用固定检索集评估 Recall@K、引用命中率、跨中英文检索质量、延迟和成本。

### 6.5 统一生成模型调用接口（P0）

业务层只使用统一请求模型：

- system prompt；
- 标准化 messages；
- model profile 或 task ID；
- max tokens、temperature 等通用参数；
- 是否流式；
- 可选结构化输出 schema；
- request ID、用户/会话等追踪上下文。

统一响应至少包含：

- 文本内容；
- finish reason；
- provider、model；
- input/output/total token 用量（供应商可提供时）；
- latency；
- request ID；
- 原始供应商请求 ID（如可用）。

供应商特有字段允许通过受控的 `extra` 参数传入，但业务模块不得依赖它们才能正常工作。

### 6.6 流式响应标准（P0）

后端继续向前端提供统一 SSE 协议，至少保留现有事件：

- `searching`：开始知识库检索；
- `token`：增量文本；
- `done`：完成，携带最终文本、来源和业务元数据；
- `error`：标准化错误。

可新增但不强制前端使用的元数据：

- `provider`
- `model`
- `usage`
- `latency_ms`
- `fallback_used`

适配器负责把 Anthropic event、OpenAI delta、Gemini chunk 等转换为统一 token 事件。

### 6.7 生成任务路由（P0）

系统以“任务”而非页面来选择模型。首批任务：

- `knowledge_answer`
- `tutor_dialogue`
- `coach_dialogue`
- `structured_feedback`
- `long_synthesis`
- `daily_digest`

每个任务可配置：

- 主模型；
- 备用模型列表；
- 超时；
- 最大输出 token；
- temperature；
- 是否要求流式；
- 是否要求 JSON/Schema 输出；
- 是否允许自动降级。

所有现有业务入口默认映射到一个任务，前端 V1 不允许普通用户随意覆盖模型，以避免行为和成本不可控。

### 6.8 生成模型故障降级（P0）

允许在以下错误发生时尝试备用模型：

- 连接超时；
- HTTP 429；
- 供应商 5xx；
- 模型暂不可用；
- 可重试的流建立失败。

默认不在以下情况自动重试或降级：

- 鉴权失败；
- 参数或内容长度错误；
- 内容安全拒绝；
- 已输出部分流式内容后失败。

降级后需在服务端日志和响应元数据中标记，前端是否展示由产品配置决定。

向量化调用只允许对同一 embedding profile 的暂时性错误进行重试。不得将另一向量模型作为旧索引查询的即时备用模型；如需高可用，应为相同模型配置多区域端点，或预先维护并验证另一套完整索引。

### 6.9 结构化输出（P0）

Gym 与 Analyst 的反馈依赖稳定 JSON。统一网关需要：

1. 对支持 JSON Schema 的模型使用原生结构化输出；
2. 对只支持 JSON mode 的模型使用 JSON mode；
3. 对均不支持的模型使用提示词约束、清洗和一次受控修复；
4. 最终使用 Pydantic schema 校验；
5. 校验失败返回标准错误，禁止将任意文本伪装成有效结构。

### 6.10 配置方式（P0/P1）

**P0：页面管理 + 后端配置文件**

- 在模型设置页新增、编辑、停用供应商与模型；
- 在页面填写 API Base URL 和 API Key，并逐模型测试连接；
- Key 只提交到后端保存，配置读取接口仅返回是否已配置，不回传密钥；
- 为生成任务选择模型，并分别选择向量模型、重排模型及版本化向量集合；
- 后端保存时校验重复 ID、无效 URL、能力不匹配和无效路由；
- 在页面首次保存前兼容现有 `ANTHROPIC_API_KEY`、`MINIMAX_API_KEY` 等环境变量，作为旧部署迁移路径；
- 同时配置生成模型与 embedding profile；未配置可用 embedding profile 时禁止静默回落到本地重模型。

**P1：管理能力增强**

- 管理任务备用模型和模型级参数；
- 查看索引绑定关系并触发受控重建；
- 查看最近错误与基础用量。

### 6.11 可观测性（P1）

每次调用记录：

- 内部 request ID；
- task、provider、model；
- 是否流式、是否降级；
- 首 token 延迟、总耗时；
- token 用量；
- 标准化错误码；
- HTTP 状态和供应商请求 ID。

向量化链路还需记录 profile、索引版本、批次数、文本/token 数、缓存命中率、重试次数、维度和估算成本，但默认不记录原始语料正文。

默认不记录完整提示词、知识库上下文和用户回答。调试模式如需记录，必须显式启用并进行敏感信息治理。

### 6.12 管理与使用体验（P1）

- 健康检查可分别展示应用、向量库、生成模型配置、向量模型配置及索引一致性状态；
- 模型不可用时，用户看到业务化提示，不暴露 SDK 堆栈；
- 管理员能看到具体错误与排查建议；
- 可选在回答底部显示当前模型，但不让供应商品牌干扰教学体验。

## 7. 建议架构

```text
Web / React
    │
FastAPI 业务路由
    │
业务服务：RAG / Tutor / Coach / Gym / Analyst / Digest
    ├── Generation Task Router
    │       └── LLM Gateway
    │             ├── Anthropic / OpenAI / Gemini
    │             └── OpenAI-Compatible / Custom
    │
    └── Retrieval Service
            ├── Embedding Gateway
            │      ├── Cloud Native Adapters
            │      ├── OpenAI-Compatible Embeddings
            │      └── Optional Local Adapter
            └── Versioned ChromaDB Index
```

### 7.1 模块职责边界

- **业务服务**：提示词、RAG 上下文、课程状态和业务结果解析。
- **Task Router**：选择模型、参数和降级链。
- **LLM Gateway**：统一调用生命周期、重试、错误、流和用量。
- **Adapter**：厂商协议转换，不包含业务提示词。
- **Provider Registry**：配置加载、能力声明、实例生命周期。
- **Embedding Gateway**：统一批量、查询向量化、限流、重试、缓存与用量，不负责向量检索。
- **Index Registry**：保存索引 manifest、embedding profile 绑定、版本、构建状态和活动别名。

## 8. 配置模型示例（概念稿）

```yaml
providers:
  anthropic_primary:
    type: anthropic
    api_key_env: ANTHROPIC_API_KEY

  openai_primary:
    type: openai
    api_key_env: OPENAI_API_KEY

  custom_compatible:
    type: openai_compatible
    base_url: https://example.com/v1
    api_key_env: CUSTOM_LLM_API_KEY

  cloud_embeddings:
    type: openai_compatible_embeddings
    base_url: https://example.com/v1
    api_key_env: EMBEDDING_API_KEY

models:
  high_quality:
    provider: anthropic_primary
    model: <provider-model-id>
    capabilities: [chat, streaming, system_message]

  local_fast:
    provider: custom_compatible
    model: <local-model-id>
    capabilities: [chat, streaming, system_message]

tasks:
  knowledge_answer:
    primary: high_quality
    fallbacks: [local_fast]
    max_tokens: 4000

embeddings:
  knowledge_base_default:
    provider: cloud_embeddings
    model: <provider-embedding-model-id>
    dimension: <provider-model-dimension>
    batch_size: 64

indexes:
  buffett_kb:
    embedding_profile: knowledge_base_default
    active_version: <index-version>
```

模型 ID 由部署者配置，项目不应把会随供应商更新的具体模型名称固化在业务代码中。embedding profile 的模型 ID 或维度发生变化时，必须创建新索引版本，不得直接覆盖旧索引配置。

## 9. API 兼容策略

### 9.1 V1 保持不变

- 保留现有业务 URL 和主要请求字段；
- 保留现有 SSE 事件名称；
- 保留来源、follow-ups、课程推进和 coach record 等业务字段；
- 前端无需在第一阶段理解供应商协议。

### 9.2 可选扩展

普通 JSON 响应可新增：

```json
{
  "meta": {
    "provider": "configured-provider",
    "model": "configured-model",
    "fallback_used": false,
    "request_id": "..."
  }
}
```

不得在响应中返回 API Key、鉴权头、完整上游错误体或内部配置路径。

## 10. 安全与合规需求

- 密钥不进入 Git、localStorage、前端构建产物或普通配置响应；后端不得回传已保存密钥；
- 前端不直接调用第三方模型；
- 配置输出和日志统一脱敏；
- 自定义 Base URL 需防范 SSRF，生产环境应使用允许列表或管理员级配置权限；
- 限制请求体、历史轮数和最大 token，避免滥用与成本失控；
- 云端向量化会把知识库分块发送给第三方，部署者必须确认语料授权、数据驻留和供应商数据保留政策；
- 支持对敏感语料禁用外部 embedding 或选择符合要求的专用端点，但不得无提示地上传；
- 不因模型切换弱化“非投资建议”和禁止编造财务数据的约束；
- 保留知识库引用与回答可验证性要求。

## 11. 迁移计划

### Phase 0：基线与契约测试

- 固化现有 API、SSE 事件和关键提示词输出契约；
- 为各业务场景准备最小回归样例；
- 建立 Claude 现有行为基线。

### Phase 1：统一网关

- 建立统一数据模型、异常类型、流事件和 Adapter 接口；
- 完成 Anthropic Adapter；
- 将现有 Claude 调用迁移到网关，行为保持一致。
- 建立 Embedding Gateway、profile 和索引 manifest；先用现有模型验证新接口契约。

### Phase 2：广泛兼容

- 完成 OpenAI 与 OpenAI-Compatible Adapter；
- 把 MiniMax 每日简报迁移进网关；
- 完成 Gemini Adapter；
- 支持任务路由和环境变量配置。
- 完成至少两个云端向量供应商和 OpenAI 兼容 `/embeddings` 适配器；
- 将默认入库和查询迁移至云端 embedding profile，移除默认镜像对 PyTorch 和模型权重的依赖；
- 提供蓝绿索引重建、检索基准评估和切换流程。

### Phase 3：可靠性与管理

- 增加备用模型、重试、能力校验和结构化输出策略；
- 增加连接测试、可观测性和管理页面；
- 补充供应商接入文档与适配器开发指南。

## 12. 验收标准

### 12.1 功能验收

- [ ] 所有 AI 入口均不直接 import 或实例化供应商客户端。
- [ ] Claude 作为默认配置时，现有功能与响应协议不回退。
- [ ] OpenAI 官方、Gemini、一个国内 OpenAI 兼容服务和一个本地服务均完成冒烟测试。
- [ ] 每项任务可以独立配置主模型。
- [ ] 主模型遇到可降级错误时能切换备用模型。
- [ ] Gym/Analyst 的 JSON 输出经过 schema 校验。
- [ ] SSE 在不同供应商下均输出一致的事件格式。
- [ ] 无可用模型时，所有入口返回一致且可理解的错误。
- [ ] 至少两个不同供应商的云端向量模型完成入库与查询冒烟测试。
- [ ] OpenAI 兼容 `/embeddings` 服务可以只通过配置接入。
- [ ] 默认 Docker 镜像无需 PyTorch、Sentence Transformers、模型权重或 GPU。
- [ ] 每个索引的 manifest 与 embedding profile 一致，不一致时拒绝查询并给出重建提示。
- [ ] 切换向量模型会创建新索引，验证通过后再切换活动版本。
- [ ] 固定检索集在新索引上的质量达到预设门槛。

### 12.2 安全验收

- [ ] API Key 不出现在前端构建产物、日志和响应中。
- [ ] `.env` 和本地运行数据不进入 Git。
- [ ] 自定义 URL 有生产环境安全约束。
- [ ] 错误响应不暴露供应商原始鉴权信息。

### 12.3 工程验收

- [ ] 每个生成适配器有普通调用、流式调用、错误映射测试。
- [ ] 每个向量适配器有文档批量、查询向量、维度校验、限流重试测试。
- [ ] 业务层只依赖统一接口。
- [ ] 配置启动校验覆盖缺失密钥、重复 ID、能力不匹配和无效路由。
- [ ] README 包含本地启动和多模型配置说明。

## 13. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 不同模型 system prompt 行为差异 | 教学角色和引用纪律不一致 | 建立任务级回归集，允许模型级参数覆盖 |
| JSON 输出能力不一致 | 反馈接口解析失败 | Schema 优先、降级修复、最终强校验 |
| 流式协议差异 | 前端卡住或重复 token | 适配器统一事件并做断流测试 |
| 上下文窗口不同 | RAG 输入超限 | 预估 token、裁剪历史和上下文预算 |
| 自动降级导致重复输出 | 用户看到拼接回答 | 已输出 token 后不自动跨模型重试 |
| 兼容接口实现不标准 | 请求字段被拒绝 | 能力声明、参数白名单、供应商级覆盖 |
| 模型成本不可控 | 运营成本上升 | 请求限额、task 路由、用量记录 |
| 向量模型切换后检索失效 | 召回错误或完全无结果 | profile 绑定、版本化索引、禁止混用、蓝绿重建 |
| 云端向量化上传语料 | 数据与版权风险 | 明示数据流、供应商政策审查、专用端点或可选离线模式 |
| Embedding API 限流 | 首次入库时间过长 | 批量、并发控制、退避、断点续传、缓存 |
| 本地向量化资源不足 | 安装失败、响应慢 | 云端默认；本地仅可选且提前检查资源 |

## 14. 待确认决策

以下事项不阻塞 Phase 0，但应在实现前确认：

1. 模型配置只由部署者通过环境变量维护，还是需要 Web 管理页面？
2. 是否允许普通用户在界面上选择模型，还是始终由任务路由决定？
3. 首批必须官方支持的国内供应商名单是什么？
4. 是否需要多租户，每个用户使用自己的 API Key？
5. 是否需要成本上限、每日额度和按用户统计？
6. 是否允许生产环境访问局域网或 localhost 模型服务？
7. 默认模型故障时，是否可以跨供应商自动降级？
8. 首批默认的云端 embedding 供应商和模型是什么？
9. 现有知识库语料是否允许发送到第三方 Embedding API，是否有地区或数据保留要求？
10. 向量索引存储继续使用本地 ChromaDB，还是后续需要支持托管向量数据库？
