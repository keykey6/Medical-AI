# 医疗AI智能客服系统 — 架构文档

> 版本：v3.0 | 更新时间：2026-05-21 | 基于代码实际状态生成

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [系统架构全景图](#3-系统架构全景图)
4. [目录结构](#4-目录结构)
5. [核心流程](#5-核心流程)
6. [API层详述](#6-api层详述)
7. [服务层详述](#7-服务层详述)
8. [数据层详述](#8-数据层详述)
9. [认证与会话隔离](#9-认证与会话隔离)
10. [知识库与Skills体系](#10-知识库与skills体系)
11. [前端架构](#11-前端架构)
12. [配置体系](#12-配置体系)
13. [部署与运维](#13-部署与运维)
14. [扩展指南](#14-扩展指南)

---

## 1. 项目概述

基于 FastAPI 的合规医疗知识问答平台。定位为**科普辅助 + 就医引导**，严禁越界进入诊断/处方/治疗领域。

### 核心能力矩阵

| 能力域 | 功能 | 实现层 |
|--------|------|--------|
| RAG知识问答 | FAISS向量检索 + LLM生成回答 | `rag_service.py` → `llm_service.py` |
| 智能分诊 | 症状关键词 → 科室推荐 | `triage_service.py` |
| 报告解读 | 图片上传 → llava转录 → LLM整理 | `report_service.py` + `multimodal_service.py` |
| 医院搜索 | 内置数据库 + 百度地图API | `map_service.py` |
| 中医科普 | 中医药文化介绍（禁辨证开方） | `health_service.py` |
| 药品查询 | 内置药品库 + LLM扩展 | `health_service.py` |
| 健康管理 | 档案存储 + BMI + 生活方式建议 | `health_service.py` |
| 多模态识别 | 食物/药品包装拍照分析 | `multimodal_service.py` |
| 语音输入 | Whisper语音转文字 | `speech_service.py` |
| 联网搜索 | 百度/NHC网页爬取 | `web_search.py` |
| 用户认证 | JWT注册/登录 + 游客模式 | `auth_service.py` + `user_repo.py` |
| 会话隔离 | 用户级会话归属 + 权限校验 | `session_repo.py` + `chat_pipeline.py` |
| Skills路由 | SKILL.md触发词 → 功能引导 | `knowledge_loader.py` |
| 暗色主题UI | Noir Medical设计系统 | `frontend/css/common.css` |
| 管理后台 | 独立服务,仪表盘/会话分析/合规监控/QoS | `admin/` (端口8001) |

### 合规红线

```
禁止: 疾病诊断 | 开具处方 | 治疗方案 | 中医辨证 | 药物推荐 | 急救指导 | 预后判断 | 医疗评价
必须: 所有回答末尾包含免责声明
拦截: 敏感词过滤 → 诊断关键词拦截 → 合规检查 → 转人工触发
```

---

## 2. 技术栈

| 层级 | 技术 | 版本/说明 |
|------|------|-----------|
| Web框架 | FastAPI | 0.115.0 |
| ASGI服务器 | Uvicorn | 0.31.0 (--reload热重载) |
| 数据库 | MySQL 8.0 | mysql-connector-python 9.0.0, 连接池 |
| 本地LLM | Ollama | qwen2.5:7b (文本) / llava:7b (多模态) |
| 远程LLM | DeepSeek API | deepseek-chat, 自动降级 |
| 向量检索 | FAISS-cpu 1.8.0 | IndexFlatL2, 384维 |
| 嵌入模型 | SentenceTransformers 3.0.1 | all-MiniLM-L6-v2 |
| 语音识别 | OpenAI Whisper | CLI调用, small模型 |
| 地图服务 | 百度地图 Web API | 地点搜索 / 地理编码 |
| 网页爬取 | BeautifulSoup4 4.12.3 | 百度搜索 + NHC内容抓取 |
| 数据校验 | Pydantic 2.8.2 | Request/Response模型 |
| 认证 | PyJWT | JWT令牌签发/验证, sha256+salt密码哈希 |
| 环境管理 | python-dotenv 1.0.1 | .env配置 |
| 前端 | 原生 HTML/CSS/JS | 零框架, Playfair Display + DM Sans字体 |
| 图标 | Font Awesome 6.5.1 | CDN加载 |

---

## 3. 系统架构全景图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        前端 (frontend/)                                    │
│                                                                          │
│  index.html   login.html   report.html   map.html                         │
│  (聊天+档案+服务) (登录注册) (报告解读)    (医院地图)                        │
│  ├─ common.css (Noir Medical设计系统)                                      │
│  ├─ chat.css / report.css / map.css                                       │
│  └─ common.js / chat.js / report.js / map.js                              │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │ HTTP REST / WebSocket / SSE / File Upload
┌────────────────────────────▼─────────────────────────────────────────────┐
│                        API 路由层 (api/)                                    │
│                                                                          │
│  chat.py     session.py   report.py   health.py   map.py   auth.py       │
│  /api/chat   /api/session /api/report /api/health /api/map /api/auth     │
│                                                                          │
│  职责: 参数校验 → 鉴权(get_current_user) → 调用Service → 序列化响应          │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                        服务层 (services/)                                   │
│                                                                          │
│  ┌───────────────────┐  ┌──────────────────┐  ┌───────────────────┐     │
│  │ chat_pipeline.py  │  │ knowledge_loader  │  │ llm_service.py    │     │
│  │ ★主流程编排       │  │ ★Skills元数据加载 │  │ Ollama/DeepSeek   │     │
│  │ 会话归属校验+标题 │  │ 触发词→功能路由   │  │ 双模型+流式+降级  │     │
│  └───────┬───────────┘  └────────┬─────────┘  └────────┬──────────┘     │
│          │                       │                      │                │
│  ┌───────▼───────────┐  ┌───────▼──────────┐  ┌────────▼──────────┐    │
│  │ compliance_service│  │ triage_service   │  │ rag_service.py    │    │
│  │ 敏感词/诊断拦截   │  │ 症状→科室映射    │  │ FAISS向量检索     │    │
│  │ 合规检查/转人工   │  │ 14类症状覆盖     │  │ 知识库文件导入    │    │
│  └───────────────────┘  └──────────────────┘  └───────────────────┘    │
│                                                                          │
│  ┌───────────────────┐  ┌──────────────────┐  ┌───────────────────┐     │
│  │ report_service.py │  │ health_service.py│  │ map_service.py    │     │
│  │ 16种报告转录      │  │ 中医/药品/食物   │  │ 6城市20+医院内置  │     │
│  │ 合规校验+三段声明 │  │ 健康评估/生活方式│  │ 百度地图API融合   │     │
│  └───────────────────┘  └──────────────────┘  └───────────────────┘     │
│                                                                          │
│  ┌───────────────────┐  ┌──────────────────┐  ┌───────────────────┐     │
│  │ multimodal_service│  │ speech_service   │  │ auth_service.py   │     │
│  │ llava多模态       │  │ Whisper语音识别  │  │ JWT签发/验证      │     │
│  │ 图片格式/大小校验 │  │ 临时文件管理     │  │ 密码哈希/游客     │     │
│  └───────────────────┘  └──────────────────┘  └───────────────────┘     │
│                                                                          │
│  ┌───────────────────┐                                                    │
│  │ web_search.py     │                                                    │
│  │ 百度爬取+NHC抓取 │                                                    │
│  └───────────────────┘                                                    │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                        数据层 (database/)                                   │
│                                                                          │
│  db.py (统一入口，re-export所有repo)                                       │
│  ├─ connection.py    MySQL连接池 (10连接) + init_database() DDL            │
│  ├─ session_repo.py  sessions表 CRUD + 用户隔离列表/重命名                  │
│  ├─ chat_repo.py     chat_logs表 写入/历史查询                              │
│  ├─ knowledge_repo.py knowledge_base表 (INSERT IGNORE去重)                  │
│  ├─ report_repo.py   report_records表 存储/查询                             │
│  ├─ health_repo.py   health_profiles表 UPSERT                              │
│  └─ user_repo.py     users表 + session_user表 注册/绑定/匿名                │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                      ┌──────▼──────┐
                      │  MySQL 8.0  │
                      │  7 张表     │
                      └─────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                    管理后台 (admin/ 端口 8001, 独立进程)                     │
│                                                                          │
│  main.py (FastAPI应用工厂)  config.py (独立配置类)                          │
│  api/admin.py (聚合统计路由)                                                │
│  services/ (dashboard / session_analytics / compliance_monitor /           │
│            qos_service / system_ops 聚合统计服务)                            │
│  database/admin_db.py (只读连接 + 聚合查询封装)                              │
│  core/auth.py (管理员JWT)  core/security.py (限速/脱敏/熔断)                │
│  core/audit_logger.py (操作审计日志)                                         │
│  frontend/ (admin.html + login.html + css/ + js/)                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                      基础设施 (core/)                                       │
│  backend/core/: logging.py (统一日志格式)                                   │
│               exception_handler.py (全局异常中间件)                          │
│  backend/config.py (Settings类，.env → 60个配置项)                           │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                    知识体系 (知识库/ + skills/)                              │
│                                                                          │
│  知识库/ (RAG检索源)             skills/ (Agent能力扩展)                    │
│  ├─ ai-pr-medical-report/       ├─ baidu-map-api/                        │
│  │  ├─ SKILL.md (6触发词)       │  └─ SKILL.md (8触发词)                  │
│  │  ├─ README.md                ├─ find/                                 │
│  │  └─ workflow.json (6步骤)    ├─ planning-with-files-zh/               │
│  ├─ 问答/                       └─ self-improving-agent自我提升/          │
│  │  └─ 标准问答.md (42+Q&A)                                             │
│  └─ 系统能力边界与回答规范.md                                             │
│                                                                          │
│  knowledge_loader.py → 扫描两个目录 → 提取triggers → 注入LLM上下文          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 目录结构

```
医疗知识库/
│
├── start.py                      # 一键启动脚本（安装依赖→MySQL检测→知识库→uvicorn）
├── start.bat                     # Windows双击启动
├── test_chat.py                  # 功能测试脚本
├── .env                          # 环境变量 (25个变量)
├── CLAUDE.md                     # AI助手指引
├── ARCHITECTURE.md               # 架构文档 (当前文件)
├── ADMIN_SYSTEM_INSTRUCTION.md   # 管理后台架构文档
│
├── backend/                      # 主服务 (端口 8000)
│   ├── main.py                   # FastAPI应用工厂 (create_app + lifespan)
│   ├── config.py                 # Settings统一配置类 (60个配置项)
│   ├── requirements.txt          # 依赖清单
│   │
│   ├── api/                      # API路由层 (薄层，6个路由文件)
│   │   ├── chat.py               # 8个端点 + WebSocket + 语音上传
│   │   ├── session.py            # 6个端点 (create/list/rename/delete/keepalive)
│   │   ├── report.py             # 7个端点 (分类/上传/解读/追问/历史)
│   │   ├── health.py             # 11个端点 (档案/评估/中医/药品/食物/生活方式)
│   │   ├── map.py                # 8个端点 (搜索/附近/详情/AK)
│   │   └── auth.py               # 4个端点 (register/login/guest/me)
│   │
│   ├── services/                 # 业务逻辑层 (13个服务文件)
│   │   ├── chat_pipeline.py      # ★ 聊天主流程编排 + 会话归属校验 + 自动标题
│   │   ├── knowledge_loader.py   # ★ Skills元数据加载 + 触发词路由
│   │   ├── llm_service.py        # Ollama/DeepSeek双模型 + 流式 + 分类/情绪
│   │   ├── rag_service.py        # FAISS向量检索 + 知识库文件导入
│   │   ├── compliance_service.py # 敏感词过滤/诊断拦截/合规检查
│   │   ├── triage_service.py     # 14类症状→科室匹配
│   │   ├── report_service.py     # 16种报告类型转录/解读/合规校验
│   │   ├── health_service.py     # 中医/药品/食物/健康评估/生活方式
│   │   ├── map_service.py        # 6城市20+医院 + 百度地图API
│   │   ├── multimodal_service.py # llava多模态图片分析 + 格式校验
│   │   ├── speech_service.py     # Whisper语音识别
│   │   ├── auth_service.py       # JWT认证 + 密码哈希 + 游客管理
│   │   └── web_search.py         # 百度/NHC网页爬取
│   │
│   ├── database/                 # 数据访问层 (8个文件)
│   │   ├── connection.py         # MySQL连接池 + init_database() DDL (7张表)
│   │   ├── db.py                 # 统一入口 + hash_data()
│   │   ├── session_repo.py       # sessions表 CRUD + 用户隔离
│   │   ├── chat_repo.py          # chat_logs表 写入/历史查询
│   │   ├── knowledge_repo.py     # knowledge_base表 INSERT IGNORE
│   │   ├── report_repo.py        # report_records表
│   │   ├── health_repo.py        # health_profiles表 UPSERT
│   │   └── user_repo.py          # users表 + session_user表
│   │
│   └── core/                     # 基础设施
│       ├── logging.py            # 统一日志配置
│       └── exception_handler.py  # 全局异常捕获中间件
│
├── frontend/                     # 主前端 (Noir Medical设计)
│   ├── index.html                # 主页面 (会话侧边栏 + 三面板)
│   ├── login.html                # 登录/注册页
│   ├── report.html               # 报告解读页
│   ├── map.html                  # 医院地图页
│   ├── css/
│   │   ├── common.css            # 设计系统 (暗色优先, 暖金主题)
│   │   ├── chat.css              # 聊天页 + 会话侧边栏样式
│   │   ├── report.css            # 报告页样式
│   │   └── map.css               # 地图页样式
│   └── js/
│       ├── common.js             # 共享工具 (会话/认证/主题/API/DOM)
│       ├── chat.js               # 聊天逻辑 + 会话侧边栏 (新建/删除/重命名/切换)
│       ├── report.js             # 报告逻辑
│       └── map.js                # 地图逻辑
│
├── admin/                        # 管理后台 (端口 8001, 独立进程)
│   ├── main.py                   # FastAPI应用工厂
│   ├── config.py                 # 独立配置类 (AdminSettings)
│   ├── requirements.txt          # 独立依赖 (fastapi, uvicorn, pyjwt, mysql-connector)
│   │
│   ├── api/                      # 管理API路由
│   │   └── admin.py              # /admin/api/* 所有端点
│   │
│   ├── services/                 # 聚合统计服务层
│   │   ├── dashboard_service.py  # 仪表盘指标聚合
│   │   ├── session_analytics.py  # 会话分析聚合
│   │   ├── compliance_monitor.py # 合规监控聚合
│   │   ├── qos_service.py        # 服务质量指标
│   │   └── system_ops.py         # 系统运维探测
│   │
│   ├── database/                 # 只读数据访问层
│   │   └── admin_db.py           # 只读连接池 + 聚合查询封装
│   │
│   ├── core/                     # 基础设施
│   │   ├── auth.py               # 管理员JWT签发/验证
│   │   ├── security.py           # 限速/脱敏/熔断中间件
│   │   └── audit_logger.py       # 操作审计日志
│   │
│   └── frontend/                 # 管理后台前端
│       ├── admin.html            # 单页应用主入口
│       ├── login.html            # 独立登录页
│       ├── css/admin.css         # 暗色主题样式 (延续Noir Medical)
│       └── js/
│           ├── admin.js          # 主应用逻辑 + 路由切换
│           ├── charts.js         # Chart.js图表初始化
│           └── auth.js           # 登录状态管理 + API封装
│
├── 知识库/                       # RAG知识资料
│   ├── ai-pr-medical-report/     # 报告解读Skill定义
│   │   ├── SKILL.md              # Skill元数据 (6个触发词)
│   │   ├── README.md             # 业务场景与痛点分析
│   │   └── workflow.json         # 6步工作流定义
│   ├── 问答/
│   │   └── 医疗智能客服RAG知识库_标准问答.md  # 42+标准化问答对
│   └── 系统能力边界与回答规范.md  # 能力范围+越界处理+回答规范
│
├── skills/                       # Agent能力Skills
│   ├── baidu-map-api/            # 百度地图API (8个触发词)
│   ├── find/                     # 技能发现
│   ├── planning-with-files-zh/   # 文件化任务规划
│   └── self-improving-agent自我提升/  # 自我改进
│
└── vector_db/                    # FAISS向量索引持久化目录
```

---

## 5. 核心流程

### 5.1 聊天请求完整管道 (ChatPipeline.run)

```
用户消息 message
  │
  ▼
① save_session(session_id, user_id, title)  ── 会话归属绑定 + 首条消息自动标题
  │
  ▼
② filtered = filter_sensitive_words(msg)     ── 敏感词替换为 ***
  │
  ├─③ is_medical_diagnosis(filtered)?        ── 关键词命中? → 拦截返回
  │
  ▼
④ compliance = check_compliance(filtered)    ── 转人工/敏感内容? → 拦截返回
  │
  ├─⑤ triage = triage_analysis(filtered)     ── 症状关键词命中? → 分诊建议返回
  │
  ▼
⑥ matched_skill = find_matching_skill(msg)   ── Skills触发词匹配
  │
  ▼
⑦ question_type = classify_question()        ── LLM分类
   emotion_type = analyze_emotion()           ── LLM情绪识别
   comfort_text = generate_comfort()          ── 安抚语映射
  │
  ▼
⑧ knowledge_results = search_knowledge_base()── FAISS向量检索 Top-3
   knowledge_context = build_context()         ── 拼接检索结果 + Skill提示
  │
  ▼
⑨ llm_response = get_llm_response(            ── LLM生成回答
       prompt, knowledge_context, history)
     ├─ CURRENT_MODEL=ollama  → Ollama /api/generate
     └─ CURRENT_MODEL=deepseek → DeepSeek /v1/chat/completions
     失败时自动降级到另一个模型
  │
  ▼
⑩ save_chat_log(session_id, msg, response)   ── 持久化对话
  │
  ▼
PipelineResult { session_id, response, question_type, emotion_type,
                 comfort_text, source, message_type }
```

### 5.2 ChatPipeline 会话归属校验

```
ChatPipeline.__init__(session_id, user_id)
  ├─ user_id 为空 → 跳过校验（游客模式）
  └─ user_id 不为空:
       ├─ get_session(session_id) 查询会话
       ├─ 会话存在且 user_id 不匹配 → 创建新session_id（隔离保护）
       └─ 会话不存在或属于当前用户 → 正常使用
```

### 5.3 模型调用与降级

```
get_llm_response(prompt, context, history)
  │
  ├─ CURRENT_MODEL == "deepseek"
  │   └─ _get_deepseek_response()
  │       ├─ 成功 → 返回
  │       └─ 失败 → _get_ollama_response()  ← 自动降级
  │
  └─ CURRENT_MODEL == "ollama"
      └─ _get_ollama_response()
          ├─ 成功 → 返回
          └─ 失败 → _get_deepseek_response()  ← 自动降级

分类/情绪分析: 固定使用 Ollama (temp=0.1, max_tokens=50)
生成任务: temp=0.3, max_tokens=2000
```

---

## 6. API层详述

### 6.1 Auth — `/api/auth` (auth.py)

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| POST | `/register` | `{username, password}` | 注册新用户 |
| POST | `/login` | `{username, password, session_id?}` | 登录获取JWT + 绑定session |
| POST | `/guest` | `{session_id?}` | 创建游客会话 |
| GET | `/me` | Header `Authorization` | 获取当前用户信息 |

### 6.2 Chat — `/api/chat` (chat.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/send` | ChatPipeline管道 |
| POST | `/send_with_type` | 含分类/情绪的ChatPipeline |
| POST | `/send_image` | multipart图片上传分析 |
| POST | `/send_image_base64` | Base64图片分析 |
| WS | `/ws/{session_id}` | WebSocket流式对话 |
| GET | `/history/{session_id}` | 对话历史 |
| POST | `/transfer/{session_id}` | 转人工 |
| POST | `/speech_to_text` | 语音转文字 |

### 6.3 Session — `/api/session` (session.py)

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/create` | 可选 | 创建会话 (UUID), 登录用户自动绑定 |
| GET | `/list` | 需登录 | 用户会话列表 (含消息数/最后消息/标题) |
| GET | `/{session_id}` | 无 | 查询会话信息 |
| POST | `/{session_id}/keepalive` | 无 | 心跳保活 |
| DELETE | `/{session_id}` | 可选 | 删除会话 (校验归属) |
| POST | `/{session_id}/rename` | 需登录 | 重命名会话 (仅所有者) |

### 6.4 Report, Health, Map

与 v2.0 保持一致，见 §6.3-§6.5 旧版文档。

---

## 7. 服务层详述

### 7.1 auth_service.py — 认证服务 (NEW)

```
密码管理:
  hash_password(password)    sha256 + salt 哈希
  verify_password(pw, hash)  验证密码

令牌管理:
  create_access_token(uid, uname)  签发JWT (HS256, 72h过期)
  decode_token(token)              验证并解码JWT
  get_current_user(authorization)  从Header提取用户 {user_id, username}

用户管理:
  register_user(username, password) → user dict
  login_user(username, password, session_id?) → {token, user_id, username}
  create_guest_session(session_id?) → {session_id, is_anonymous}
```

### 7.2 其他服务

与 v2.0 架构保持一致：`chat_pipeline.py`（新增会话归属校验+自动标题）、`llm_service.py`、`rag_service.py`、`compliance_service.py`、`triage_service.py`、`report_service.py`、`health_service.py`、`map_service.py`、`multimodal_service.py`、`speech_service.py`、`web_search.py`、`knowledge_loader.py`。

---

## 8. 数据层详述

### 8.1 数据库连接

```
connection.py:
  get_pool()       → MySQLConnectionPool (pool_size=10, charset=utf8mb4)
  get_connection() → 从连接池获取连接
  init_database()  → CREATE DATABASE + 7张表DDL + 迁移兼容
```

### 8.2 表结构 (7张表)

```
users ──< session_user >── sessions ──< chat_logs
                    │
                    ├──< report_records
                    └──< health_profiles

knowledge_base (独立，无外键)
```

#### users (NEW)

| 字段 | 类型 | 约束 |
|------|------|------|
| user_id | VARCHAR(64) | PK |
| username | VARCHAR(100) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

#### session_user (NEW)

| 字段 | 类型 | 约束 |
|------|------|------|
| session_id | VARCHAR(64) | PK, FK → sessions ON DELETE CASCADE |
| user_id | VARCHAR(64) | FK → users ON DELETE SET NULL |
| is_anonymous | BOOLEAN | DEFAULT TRUE |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

#### sessions

| 字段 | 类型 | 约束 |
|------|------|------|
| session_id | VARCHAR(64) | PK |
| user_id | VARCHAR(64) | NULL (NEW — 用户归属) |
| title | VARCHAR(200) | NULL (NEW — 会话标题) |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| last_active | DATETIME | ON DUPLICATE KEY UPDATE |
| user_info | TEXT | NULL |

#### chat_logs / knowledge_base / report_records / health_profiles

与 v2.0 保持一致。`health_profiles` 新增 `user_id` 列。

### 8.3 数据访问模式

```
所有Repo遵循统一模式:
  conn = get_connection()     # 从连接池获取
  try:
      cursor = conn.cursor()
      # ... 执行SQL ...
      conn.commit()
  finally:
      cursor.close()
      conn.close()            # 归还连接到池

特殊:
  session_repo: list_user_sessions() 使用LEFT JOIN统计msg_count
  knowledge_repo: INSERT IGNORE 去重
  sessions: INSERT ON DUPLICATE KEY UPDATE 续期
  health_profiles: UPDATE or INSERT (UPSERT)
  user_repo: session_user使用ON DUPLICATE KEY UPDATE绑定
```

---

## 9. 认证与会话隔离

### 9.1 认证流程

```
用户注册
  → hash_password(password) = salt:sha256(salt+password)
  → INSERT INTO users

用户登录
  → verify_password(password, stored_hash)
  → create_access_token(user_id, username) [JWT HS256, 72h]
  → bind_session_to_user(session_id, user_id)  [更新session_user表]
  → 返回 {token, user_id, username}

游客模式
  → create_guest_session(session_id)
  → mark_session_anonymous(session_id)
  → 前端localStorage存session_id
```

### 9.2 会话隔离机制

```
API请求携带 Authorization: Bearer <token>
  → get_current_user() 解析JWT → {user_id, username}
  → 所有操作带user_id:
      ├─ session创建: save_session(sid, user_id=uid)
      ├─ session列表: list_user_sessions(uid) 仅返回自己的会话
      ├─ session删除: delete_session(sid, user_id=uid) 仅能删除自己的
      ├─ session重命名: rename_session(sid, uid, title) 仅所有者
      └─ ChatPipeline: 校验session归属, 不匹配则创建新会话

游客 (无token):
  → get_current_user() 返回 None
  → 会话操作不传user_id (向后兼容)
  → 前端localStorage管理本地sessionId
```

### 9.3 前端认证UI

```
topbar:
  ├─ 未登录: 显示"游客" + 登录按钮 → 跳转 /static/login.html
  └─ 已登录: 显示用户名 + 退出按钮

login.html:
  ├─ 登录表单 (用户名 + 密码 + 验证码)
  └─ 注册表单 (用户名 + 密码 + 确认密码)

会话侧边栏:
  ├─ 未登录: "登录后查看历史会话"
  └─ 已登录: 会话列表 (新建/切换/重命名/删除, 实时刷新)
```

---

## 10. 知识库与Skills体系

### 10.1 知识文件结构

```
知识库/
├── ai-pr-medical-report/
│   ├── SKILL.md              # YAML frontmatter: name, description, triggers(6个)
│   ├── README.md             # 业务场景, 痛点分析, Skill编排图
│   └── workflow.json         # 6步工作流定义
├── 问答/
│   └── 医疗智能客服RAG知识库_标准问答.md  # 42+Q&A, 8大类
└── 系统能力边界与回答规范.md  # 10项能力, 6类禁止, 5种越界模板

skills/
├── baidu-map-api/SKILL.md    # 百度地图API (8个触发词)
├── find/SKILL.md             # 技能发现 (内部)
├── planning-with-files-zh/   # 任务规划 (10个触发词)
└── self-improving-agent/     # 自我改进 (内部)
```

### 10.2 知识自动加载机制

```
系统启动 (lifespan / start.py)
  → rag_service.load_knowledge_base()
    → import_knowledge_files("知识库")
      → glob 扫描 **/*.md
      → _parse_markdown_sections() 按 ## 拆分
      → INSERT IGNORE 写入MySQL
      → model.encode() → index.add() 写入FAISS
  → knowledge_loader.load_skills()
    → 扫描 知识库/ 和 skills/
    → 发现 SKILL.md → 解析YAML frontmatter
    → 提取 triggers → 构建触发词映射
    → LLM system prompt 注入 Skills 上下文
```

---

## 11. 前端架构

### 11.1 页面结构

```
index.html (主页面)
├── topbar (导航栏, 毛玻璃效果, 含认证状态)
├── session-sidebar (260px, 左侧)
│   ├── 新建会话按钮
│   └── 会话列表 (切换/重命名/删除, 实时刷新)
├── main-area (右侧, 三面板)
│   ├── profilePanel (健康档案表单 + 评估结果)
│   ├── chatPanel (聊天主面板)
│   │   ├── disclaimer (合规提示)
│   │   ├── question-chips (6个快捷提问)
│   │   ├── quick-grid (8个快捷功能卡片)
│   │   ├── chat-messages (消息列表)
│   │   └── chat-input-bar (输入 + 图片/发送)
│   ├── servicesPanel (就医/生活方式/用药管理)
│   └── genericModal (通用弹窗)
│
login.html (登录/注册页)
├── 登录选项卡 (用户名/密码/验证码)
└── 注册选项卡 (用户名/密码/确认密码)

report.html + map.html (独立工具页)
```

### 11.2 JS模块职责

| 文件 | 核心功能 | 依赖 |
|------|----------|------|
| common.js | getSessionId, getToken, isLoggedIn, login/logout, initTheme, toggleTheme, apiGet, apiPost, escapeHtml | localStorage, fetch |
| chat.js | sendMsg, sendQuick, handleChatImage, createNewSession, switchSession, deleteCurrentSession, renameSession, loadSessionList, loadProfile, saveProfile, openModal系列 | common.js, /api/chat, /api/session, /api/health |
| report.js | loadCategories, selectType, submitAnalysis, sendFollowup, loadHistory | common.js, /api/report |
| map.js | onBMapLoaded, doSearch, getUserLocation, selectHospital, renderMarkers | common.js, /api/map, 百度地图JS SDK |

### 11.3 设计系统 (Noir Medical)

```
方向: 深色优先 | 暖金点缀 | 玻璃质感 | 精工排版

调色板:
  基底: #070a13 → #f7f5f0 (light)
  表面: #0d1120 → #131a2e → #1a2340
  主色: #d4a855 (暖金)  辅助: #14b8a0 (青绿)
  文字: #ede7d9 / #9d9587 / #6b6357

字体:
  标题: Playfair Display, Noto Serif SC, STSong, serif
  正文: DM Sans, PingFang SC, Microsoft YaHei, sans-serif
```

---

## 12. 配置体系

### 12.1 配置项全表

| 分类 | 变量 | 默认值 | 说明 |
|------|------|--------|------|
| MySQL | MYSQL_HOST | localhost | 数据库地址 |
| | MYSQL_PORT | 3306 | 端口 |
| | MYSQL_USER | root | 用户名 |
| | MYSQL_PASSWORD | — | 密码 |
| | MYSQL_DATABASE | medical_ai | 库名 |
| | DB_POOL_SIZE | 10 | 连接池大小 |
| Ollama | OLLAMA_BASE_URL | http://localhost:11434 | API地址 |
| | OLLAMA_MODEL | qwen2.5:7b | 文本模型 |
| | OLLAMA_EMBED_MODEL | nomic-embed-text | 嵌入模型 |
| | OLLAMA_MULTIMODAL_MODEL | llava:7b | 多模态模型 |
| DeepSeek | DEEPSEEK_API_KEY | — | API密钥 |
| | DEEPSEEK_API_URL | https://api.deepseek.com/v1/chat/completions | 端点 |
| 百度地图 | BAIDU_MAP_AK | — | 前端AK |
| | BAIDU_MAP_SERVER_AK | — | 服务端AK |
| 向量DB | VECTOR_DB_PATH | ./vector_db | FAISS索引路径 |
| | EMBEDDING_MODEL | all-MiniLM-L6-v2 | 嵌入模型名 |
| | EMBEDDING_DIM | 384 | 向量维度 |
| 应用 | CURRENT_MODEL | ollama | 当前模型 |
| | LOG_LEVEL | INFO | 日志级别 |
| | MAX_CONTEXT_LENGTH | 10 | 对话历史轮数 |
| | ENABLE_WEB_SEARCH | true | 联网搜索开关 |
| | HOST | 0.0.0.0 | 监听地址 |
| | PORT | 8000 | 监听端口 |
| 认证 | SECRET_KEY | (内置默认) | JWT签名密钥 |
| | JWT_EXPIRE_HOURS | 72 | 令牌过期时间 |
| | JWT_ALGORITHM | HS256 | JWT算法 |
| 合规 | DISCLAIMER | 本文仅供科普参考... | 通用免责声明 |

---

## 13. 部署与运维

### 13.1 启动流程

```
python start.py
  ├─ install_requirements()     pip install -r backend/requirements.txt
  ├─ check_mysql()              连接测试
  │   └─ init_database()        CREATE DATABASE + 7表DDL + 列迁移
  ├─ load_knowledge_base()      从MySQL + 知识库/ 导入向量化
  └─ start_server()             uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 13.2 降级策略

| 故障组件 | 影响范围 | 自动处理 |
|----------|----------|----------|
| MySQL不可用 | 全部功能 | 启动脚本告警, 允许继续 |
| Ollama不可用 | LLM生成 | 自动降级到DeepSeek |
| DeepSeek不可用 | LLM生成 | 自动降级到Ollama |
| FAISS不可用 | 知识库检索 | rag_enabled=False, 回退纯LLM |
| 嵌入模型下载失败 | 向量化 | RAG不可用, 基础问答正常 |
| 百度地图AK未配置 | 实时搜索 | 仅返回内置医院数据 |
| Whisper未安装 | 语音输入 | 返回"服务未就绪" |
| llava未安装 | 图片分析 | 返回"服务暂时不可用" |

### 13.3 访问入口

```
前端主页:    http://localhost:8000/static/index.html
登录页面:    http://localhost:8000/static/login.html
报告解读:    http://localhost:8000/static/report.html
医院地图:    http://localhost:8000/static/map.html
API文档:     http://localhost:8000/docs
健康检查:    http://localhost:8000/health
管理后台:    http://localhost:8001/admin/admin.html
后台登录:    http://localhost:8001/admin/login.html
后台健康:    http://localhost:8001/health
```

---

## 14. 扩展指南

### 14.1 新增知识条目

```
方式一: 直接编辑 知识库/ 中的 .md 文件
  → 重启系统 → 自动导入 (INSERT IGNORE去重)

方式二: 调用 API
  POST /api/knowledge/add { title, content, category, source_url }
  → add_knowledge_to_vector_db()
```

### 14.2 新增Skill

```
1. 在 知识库/ 或 skills/ 新建目录
2. 创建 SKILL.md (YAML frontmatter: name, description, triggers)
3. (可选) 创建 workflow.json 定义工作流
4. 重启系统 → knowledge_loader 自动发现
5. (可选) 在 chat_pipeline._build_skill_hint() 添加专用引导逻辑
```

### 14.3 新增API端点

```
1. 在 api/ 创建新路由文件
2. 在 main.py create_app() 中 include_router
3. 业务逻辑放在 services/ 新文件
4. 数据库操作放在 database/ 新repo文件
5. 在 database/db.py 中 re-export
```

### 14.4 新增前端页面

```
1. 在 frontend/ 创建新 .html 文件
2. 引用 /static/css/common.css (设计系统)
3. 如需专属样式, 在 frontend/css/ 创建新 .css
4. 如需专属逻辑, 在 frontend/js/ 创建新 .js (引用 common.js)
5. 在其他页面添加导航链接
```

### 14.5 扩展点标注

```
★ 高扩展性节点:
  - auth_service.py        → JWT可替换为OAuth2.0/OIDC
  - knowledge_loader.py    → 自动发现新Skill, 无需改代码
  - rag_service.py         → 自动导入知识库文件, 支持按##拆分
  - chat_pipeline.py       → 管道模式, 灵活插入/移除步骤
  - config.py              → 集中配置, 新增变量即可用
  - llm_service.py         → 新增模型只需添加引擎函数
  - database/db.py         → 统一入口, 新repo直接re-export

▲ 需要注意:
  - compliance_service.py  → 关键词硬编码, 新增规则需改代码
  - triage_service.py      → 症状关键词映射, 新增需改两个dict
  - map_service.py         → 医院数据硬编码, 建议改为数据库存储
  - 前端HTML               → 功能卡片硬编码, 可改为配置驱动
```

---

*本文档基于 2026-05-21 代码实际状态生成，涵盖 7 张数据表、14 个服务模块、6 个 API 路由、4 个前端页面的完整架构。*
