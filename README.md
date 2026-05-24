# 医疗AI智能客服 — Medical AI Assistant

基于 FastAPI + RAG 的合规医疗知识问答平台，提供向量检索问答、智能分诊、报告解读、医院搜索、中医/用药咨询等功能。

## 架构

```
用户消息 → ChatPipeline（三阶段处理）
  ├─ preprocess()   合规检查 → 诊断拦截 → 敏感词过滤 → 智能分诊
  ├─ build_context() 问题分类 → 情绪识别 → FAISS 向量检索 → Skill 匹配
  └─ run()          DeepSeek V4 / Ollama 双模型 LLM 生成
```

## 快速启动

### 环境要求

- Python 3.10+
- MySQL 8.0
- Ollama（可选，本地模型降级用）
- DeepSeek API Key（推荐）

### 安装运行

```bash
# 1. 克隆仓库
git clone https://github.com/keykey6/AI-health.git
cd AI-health

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 MySQL 密码、DeepSeek API Key 等

# 3. 一键启动
python start.py
```

### 服务端口

| 服务 | 地址 | 说明 |
|------|------|------|
| 主服务 | http://localhost:8000 | API + 前端界面 |
| 管理后台 | http://localhost:8001/admin/login.html | 仪表盘、会话分析、合规监控 |

## 模型配置

`.env` 中 `CURRENT_MODEL` 控制默认模型：
- `deepseek`（推荐）：DeepSeek V4 优先，失败自动降级 Ollama
- `ollama`：本地 qwen2.5:7b 模型

## 项目结构

```
AI-health/
├── backend/           # 主 API 服务（FastAPI + RAG）
│   ├── api/           # 路由层
│   ├── core/          # 日志、异常中间件
│   ├── database/      # MySQL 仓库层
│   └── services/      # 业务逻辑（LLM、RAG、合规等）
├── admin/             # 管理后台（独立进程 :8001）
├── shared/            # 共享工具（auth_utils）
├── frontend/          # Web 前端（HTML/CSS/JS）
├── 知识库/            # RAG 知识库文档
├── skills/            # Agent 技能扩展
├── tests/             # 测试
├── scripts/           # 工具脚本
└── docs/              # 文档
```

## 合规声明

本系统仅供医疗科普参考，不构成诊断或治疗建议。包含敏感词过滤、诊断拦截、免责声明自动追加等合规机制。

## License

仅供学习和研究使用。
