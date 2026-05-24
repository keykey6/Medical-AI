# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

GitHub: https://github.com/keykey6/Medical-AI

## 项目概述

医疗AI智能客服系统，基于 FastAPI 的合规医疗知识问答平台。提供 RAG 向量检索问答、智能分诊、报告解读、医院搜索、中医/用药咨询、语音输入等功能。

## 项目结构

```
Medical-AI/
├── backend/           # 主 API 服务（FastAPI + RAG）
│   ├── api/           # 路由层
│   ├── core/          # 日志、异常中间件
│   ├── database/      # MySQL 仓库层
│   └── services/      # 业务逻辑（LLM、RAG、合规等）
├── admin/             # 管理后台（独立进程 :8001）
├── shared/            # 共享工具（auth_utils）
├── frontend/          # Web 前端（HTML/CSS/JS）
├── mobile-app/        # Capacitor 移动端
├── 知识库/            # RAG 知识库文档
├── skills/            # Agent 技能扩展
├── tests/             # 测试
├── scripts/           # 工具脚本
└── docs/              # 文档
```

## 常用命令

```bash
# 启动主服务（自动安装依赖、初始化DB、加载知识库）
python start.py

# 启动管理后台（独立进程，端口 8001）
python -m uvicorn admin.main:app --host 127.0.0.1 --port 8001 --reload

# 运行功能测试（需先启动服务）
python tests/test_chat.py
```

## 架构

### 服务端口

| 服务 | 端口 | 启动方式 |
|------|------|----------|
| 主服务 (API + 前端) | 8000 | `python start.py` |
| 管理后台 | 8001 | `uvicorn admin.main:app --port 8001` |

### 请求处理流程

```
用户消息 → ChatPipeline（backend/services/chat_pipeline.py）
  ├─ preprocess() 阶段（可复用）:
  │   ├─ filter_sensitive_words() 过滤敏感词
  │   ├─ is_medical_diagnosis()   拦截疾病诊断请求
  │   ├─ check_compliance()       合规检查（转人工/敏感内容拦截）
  │   └─ triage_analysis()        症状→科室分诊匹配
  ├─ build_context() 阶段（可复用）:
  │   ├─ classify_question()      问题分类（LLM）
  │   ├─ analyze_emotion()        情绪识别（LLM）
  │   ├─ search_knowledge_base()  FAISS向量检索
  │   └─ find_matching_skill()    Skill 匹配
  └─ run() 阶段:
      └─ get_llm_response()       LLM生成回答（Ollama/DeepSeek）
```

`ChatPipeline` 将预处理和上下文构建拆分为 `preprocess()` 和 `build_context()` 方法，**WebSocket 端点和 HTTP 端点共享同一套过滤/分类/检索逻辑，避免代码重复。**

### 模块职责

| 模块 | 职责 |
|------|------|
| `backend/config.py` | 统一配置中心，从 `.env` 加载所有设置，**所有服务文件通过 `from config import settings` 访问配置** |
| `backend/core/` | 日志系统、全局异常中间件 |
| `backend/database/connection.py` | MySQL 连接池管理、`init_database()` |
| `backend/database/__init__.py` | 统一 re-export 所有 repo 函数（优先使用此入口） |
| `backend/database/*_repo.py` | 按表拆分的 repo：session / chat / knowledge / report / health / user |
| `backend/services/llm_service.py` | Ollama/DeepSeek 双模型，支持流式/非流式，失败自动降级 |
| `backend/services/rag_service.py` | FAISS + SentenceTransformer 向量检索，含知识库加载 |
| `backend/services/chat_pipeline.py` | 聊天处理管道，`preprocess()` + `build_context()` + `run()` 三阶段 |
| `backend/services/compliance_service.py` | 敏感词过滤、诊断拦截、合规检查（纯关键词匹配） |
| `backend/services/triage_service.py` | 症状关键词 → 科室推荐映射 |
| `backend/services/knowledge_loader.py` | 扫描 `知识库/` 和 `skills/` 目录，加载 SKILL.md 元数据 |
| `backend/api/` | FastAPI 路由，薄层——调用 service 后返回 |
| `admin/` | 管理后台（独立进程），仪表盘/会话分析/合规监控/QoS/系统运维 |

### 配置管理规则

- **`backend/config.py` 是唯一读取 `.env` 的地方**。服务文件一律通过 `from config import settings` 获取配置，禁止在服务文件中直接调用 `load_dotenv()` 或 `os.getenv()`。
- 密码哈希函数 `hash_password`/`verify_password` 在 `backend/services/auth_service.py` 和 `admin/core/auth.py` 中各有一份（两个独立进程，各自维护认证逻辑）。

### 模型切换

`.env` 中 `CURRENT_MODEL=ollama`（默认）或 `CURRENT_MODEL=deepseek`。LLM 调用失败时自动降级到另一个模型。Ollama 默认使用 `qwen2.5:7b`，多模态使用 `llava:7b`。

### 关键约束

- **合规红线**：禁止疾病诊断、开处方、提供治疗方案。关键词拦截在 `compliance_service.py` 的 `MEDICAL_DIAGNOSIS_KEYWORDS` 列表中
- **免责声明**：所有 LLM 回答末尾必须包含 `"本文仅供科普参考，不构成医疗建议。如有不适，请及时就医。"`
- **数据库**：需 MySQL 8.0，密码在 `.env` 中配置，首次启动自动建表
- **Ollama**：非必需，未启动时 LLM 功能降级但服务可运行
