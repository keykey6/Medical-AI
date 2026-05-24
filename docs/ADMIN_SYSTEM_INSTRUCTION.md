# 后台数据管理系统 — 架构指令文档

> 版本：v1.0 | 生成时间：2026-05-21 | 关联主系统：医疗AI智能客服系统 v3.0

---

## 目录

1. [系统定位](#1-系统定位)
2. [技术栈](#2-技术栈)
3. [部署架构](#3-部署架构)
4. [功能模块](#4-功能模块)
5. [数据访问规范](#5-数据访问规范)
6. [认证体系](#6-认证体系)
7. [API路由](#7-api路由)
8. [前端架构](#8-前端架构)
9. [安全隔离](#9-安全隔离)
10. [扩展预留](#10-扩展预留)

---

## 1. 系统定位

独立运行的管理后台服务，与主应用（端口 8000）物理隔离，仅服务于管理员角色。

### 核心约束

| 约束项 | 要求 |
|--------|------|
| 端口隔离 | 独立端口 `8001`，禁止与主服务共享运行时 |
| 身份隔离 | 仅暴露聚合统计指标，任何接口不得返回 `username`、`user_id` 等可识别个人身份的信息 |
| 权限隔离 | 管理员身份通过独立认证体系校验，与主应用用户池完全隔离 |
| 数据隔离 | 只读连接主库，独立只读账号，禁止写操作 |

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| Web框架 | FastAPI | 与主系统保持一致 |
| ASGI服务器 | Uvicorn | `--port 8001` |
| 数据库 | MySQL 8.0 | 只读连接主库，独立账号 `medical_admin_ro` |
| 数据缓存 | Redis（可选） | 聚合统计缓存，TTL 5分钟 |
| 前端 | 原生 HTML/CSS/JS | 延续 Noir Medical 暗色主题 |
| 图表 | Chart.js | CDN 引入 |
| 认证 | PyJWT | 独立 JWT 签发/验证 |

---

## 3. 部署架构

```
┌─────────────────────────────────────────┐
│              外部网络                    │
│    (VPN/跳板机/内网白名单)              │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         管理后台服务 (端口 8001)         │
│                                          │
│  admin/                                  │
│  ├── main.py          FastAPI 应用工厂   │
│  ├── config.py        独立配置类         │
│  ├── api/             管理 API 路由      │
│  ├── services/        聚合统计服务       │
│  ├── database/        只读数据访问层     │
│  └── frontend/        管理后台前端页面   │
│                                          │
│  监听: 127.0.0.1:8001 (生产环境)        │
└──────────────┬──────────────────────────┘
               │ 只读连接 (独立账号)
┌──────────────▼──────────────────────────┐
│         主应用数据库 (MySQL 8.0)        │
│                                          │
│  主应用账号: medical_app_rw (读写)       │
│  管理账号:   medical_admin_ro (只读)    │
└─────────────────────────────────────────┘
```

### 启动命令

```bash
# 启动管理后台（独立进程，端口 8001）
python -m uvicorn admin.main:app --host 127.0.0.1 --port 8001 --reload
```

> **当前实现说明**：管理后台当前复用主应用 MySQL 账号（`MYSQL_USER`/`MYSQL_PASSWORD`），独立只读账号 `medical_admin_ro` 为未来增强项。

---

## 4. 功能模块

### 4.1 仪表盘（Dashboard）

聚合指标卡片：

| 指标 | 数据来源 | 说明 |
|------|----------|------|
| 总对话轮次 | `chat_logs` 总行数 | 累计消息量 |
| 今日活跃会话 | `DATE(created_at)` 去重 `session_id` | 当日会话活跃度 |
| 近7日对话趋势 | 按日聚合 `chat_logs` | 折线图 |
| 知识库命中率 | RAG 检索触发次数 / 总对话数 | 检索效能 |
| 模型调用分布 | Ollama vs DeepSeek 调用占比 | 饼图 |
| 平均响应耗时 | 请求日志统计 | 性能指标 |
| 合规拦截次数 | 敏感词/诊断/转人工 分类统计 | 柱状图 |
| 功能模块使用频次 | 分诊、报告、地图、健康评估 | 各模块触发计数 |

健康状态监控：

| 监控项 | 探测方式 |
|--------|----------|
| 主应用 API | 轮询 `http://localhost:8000/health` |
| MySQL 连接池 | 活跃连接数、慢查询计数 |
| Ollama 服务 | `GET /api/tags` 探测 |
| 向量索引 | FAISS 索引文档总数 |

### 4.2 会话分析（Session Analytics）

**禁止展示：** 会话列表中的 `user_id`、`username`、IP 地址、设备指纹、消息原文。

**允许展示：**

| 分析维度 | 统计方式 |
|----------|----------|
| 匿名会话趋势 | 按小时/日/周的会话创建量 |
| 会话生命周期分布 | 创建到最后活跃的时长分箱统计 |
| 会话消息深度分布 | 单会话消息数直方图：1-5条 / 6-10条 / 11-20条 / 20+条 |
| 会话流失点分析 | 最后消息意图类型与终止率关联 |
| 功能模块会话占比 | 触发分诊的会话%、触发报告解读的会话% |

### 4.3 内容合规监控（Compliance Monitor）

| 监控项 | 说明 |
|--------|------|
| 敏感词拦截热力图 | 按规则类别聚合：诊断拦截、处方拦截、急救拦截 |
| 高风险意图分布 | 时间维度上的合规事件趋势 |
| 转人工触发分析 | 触发转人工的消息类型占比 |
| 知识库越界查询 | 超出系统能力边界的问题分类统计 |

### 4.4 服务质量分析（QoS Analytics）

| 指标 | 统计方式 |
|------|----------|
| 模型响应延迟分位数 | P50 / P95 / P99 |
| 模型降级事件 | Ollama→DeepSeek / DeepSeek→Ollama 次数与时间戳 |
| 错误率趋势 | 按 HTTP 状态码分类：4xx / 5xx |
| 知识库检索质量 | Top-3 检索结果相关性评分分布 |

### 4.5 系统运维（System Ops）

| 功能 | 说明 |
|------|------|
| 配置项热览 | 只读展示 `.env` 关键配置（**禁止展示密钥**） |
| 知识库索引状态 | 已加载文档数、最后更新时间、索引文件大小 |
| 日志监控 | 日志文件大小、最近错误日志摘要（脱敏处理） |
| 手动刷新缓存 | 清除 Redis 统计缓存，强制重新聚合 |

---

## 5. 数据访问规范

### 5.1 查询铁律

**所有查询必须采用聚合模式，禁止返回明细。**

允许示例：

```sql
SELECT DATE(created_at) as day, COUNT(DISTINCT session_id) as session_count
FROM chat_logs
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY day;
```

禁止示例：

```sql
-- 绝对禁止
SELECT * FROM users;
SELECT username, message FROM chat_logs LIMIT 100;
SELECT * FROM session_user;
SELECT * FROM health_profiles WHERE user_id = 'xxx';
```

### 5.2 禁止访问清单

| 对象 | 限制级别 |
|------|----------|
| `users` 表 | 仅允许 `COUNT(*)`，禁止任何字段查询 |
| `session_user` 表 | 完全禁止查询，防止推导用户身份 |
| `chat_logs.message` | 禁止全文检索与展示原始消息 |
| `health_profiles` | 仅统计档案建立数量，禁止个体数据访问 |

### 5.3 数据库权限

```sql
-- 管理后台只读账号
CREATE USER 'medical_admin_ro'@'localhost' IDENTIFIED BY 'xxx';
GRANT SELECT ON medical_ai.chat_logs TO 'medical_admin_ro'@'localhost';
GRANT SELECT ON medical_ai.sessions TO 'medical_admin_ro'@'localhost';
GRANT SELECT ON medical_ai.knowledge_base TO 'medical_admin_ro'@'localhost';
GRANT SELECT ON medical_ai.report_records TO 'medical_admin_ro'@'localhost';
-- 禁止: GRANT SELECT ON medical_ai.users;
-- 禁止: GRANT SELECT ON medical_ai.session_user;
-- 禁止: GRANT SELECT ON medical_ai.health_profiles;
```

---

## 6. 认证体系

### 6.1 管理员账号

- 独立于主应用 `users` 表
- 通过环境变量配置：`ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH`
- 密码采用 `sha256 + salt` 哈希，与主应用一致

### 6.2 认证流程

```
POST /admin/api/login
  → 校验用户名密码
  → 签发独立 JWT (HS256, 2小时过期)
  → 返回 admin_token
  → 前端 localStorage 存储
```

### 6.3 安全策略

| 策略 | 实现 |
|------|------|
| 登录失败限速 | 同 IP 5分钟内最多5次尝试 |
| 令牌短时效 | JWT 有效期 2小时 |
| 操作审计 | 记录登录、数据导出、配置查看至 `admin_audit.log` |
| 依赖校验 | 所有管理 API 通过 `get_current_admin` 依赖项校验 |

---

## 7. API路由

前缀：`/admin/api`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/login` | 管理员登录 | 公开 |
| GET | `/dashboard/stats` | 仪表盘聚合指标 | 需 admin_token |
| GET | `/dashboard/trends` | 近7日趋势数据 | 需 admin_token |
| GET | `/sessions/analytics` | 会话聚合分析 | 需 admin_token |
| GET | `/compliance/summary` | 合规拦截统计 | 需 admin_token |
| GET | `/qos/metrics` | 服务质量指标 | 需 admin_token |
| GET | `/system/health` | 依赖服务健康状态 | 需 admin_token |
| GET | `/system/config` | 脱敏配置项（无密钥） | 需 admin_token |
| POST | `/system/flush-cache` | 刷新统计缓存 | 需 admin_token |

### 统一响应格式

```json
{
  "code": 200,
  "data": { /* 聚合数据对象 */ },
  "timestamp": "2026-05-21T09:17:00Z"
}
```

---

## 8. 前端架构

### 8.1 页面结构

```
admin.html（单页应用）
├── 登录页 /admin/login
│   └── 用户名 + 密码 + 登录按钮
│
└── 主控制台（登录后）
    ├── 顶部导航栏（毛玻璃效果，显示管理员状态）
    ├── 左侧导航菜单（260px）
    │   ├── 仪表盘（默认激活）
    │   ├── 会话分析
    │   ├── 合规监控
    │   ├── 服务质量
    │   └── 系统运维
    │
    └── 右侧内容区
        ├── 指标卡片网格（4列响应式）
        ├── Chart.js 图表容器
        └── 数据表格（聚合统计，无个体信息）
```

### 8.2 设计规范

| 项 | 规范 |
|----|------|
| 主题 | 延续 Noir Medical 暗色优先 |
| 调色 | 基底 `#070a13`，表面 `#0d1120`，主色 `#d4a855`，告警 `#ef4444` |
| 字体 | 标题 Playfair Display，正文 DM Sans |
| 图表 | Chart.js CDN，克制配色（深蓝/青绿/暖金/告警红） |
| 刷新 | 关键指标 30秒自动轮询，支持手动刷新 |

---

## 9. 安全隔离

### 9.1 只读强制

- 数据库连接设置 `read_only=True`
- 中间件拦截所有 `INSERT/UPDATE/DELETE` 语句
- 异常直接返回 403

### 9.2 网络隔离

- 开发环境：`127.0.0.1:8001`
- 生产环境：仅内网可达，通过 VPN/跳板机访问
- 禁止暴露至公网

### 9.3 数据脱敏

- 用户数 < 5 时显示 "`<5`"，不展示精确值
- 所有数值类统计采用阈值处理

### 9.4 查询熔断

- 慢查询超时：5秒自动中断
- 防止复杂聚合拖垮主库

### 9.5 CORS 策略

```python
# 严格限制来源，禁止通配符
origins = ["http://localhost:8001", "http://127.0.0.1:8001"]
```

---

## 10. 扩展预留

| 扩展项 | 说明 |
|--------|------|
| 告警通道 | 预留 Webhook 配置位：企业微信 / 钉钉 / 邮件 |
| 数据导出 | 聚合报表导出 PDF/CSV（脱敏后），非明细数据 |
| 多管理员 | 基于角色的细粒度权限：只读运维 vs 配置管理 |
| 缓存优化 | Redis 聚合结果缓存，支持手动/定时刷新 |
| 日志分析 | 接入 ELK/Loki 进行日志聚合分析 |

---

## 附录：目录结构（预期输出）

```
admin/                          # 后台管理系统根目录
├── main.py                     # FastAPI 应用工厂
├── config.py                   # 独立配置类（ADMIN_USERNAME, ADMIN_PASSWORD_HASH 等）
├── requirements.txt            # 独立依赖（fastapi, uvicorn, pyjwt, mysql-connector-python）
│
├── api/                        # API 路由层
│   └── admin.py                # /admin/api/* 所有端点
│
├── services/                   # 聚合统计服务层
│   ├── dashboard_service.py    # 仪表盘指标聚合
│   ├── session_analytics.py  # 会话分析聚合
│   ├── compliance_monitor.py # 合规监控聚合
│   ├── qos_service.py          # 服务质量聚合
│   └── system_ops.py          # 系统运维探测
│
├── database/                   # 只读数据访问层
│   └── admin_db.py            # 只读连接池 + 聚合查询封装
│
├── core/                       # 基础设施
│   ├── auth.py                # 管理员 JWT 签发/验证
│   ├── audit_logger.py        # 操作审计日志
│   └── security.py            # 限速/脱敏/熔断中间件
│
└── frontend/                   # 管理后台前端
    ├── admin.html             # 单页应用主入口
    ├── login.html             # 独立登录页
    ├── css/
    │   └── admin.css          # 暗色主题样式（延续 Noir Medical）
    └── js/
        ├── admin.js           # 主应用逻辑 + 路由切换
        ├── charts.js          # Chart.js 图表初始化
        └── auth.js            # 登录状态管理 + API 封装
```

---

*本文档基于医疗AI智能客服系统 v3.0 架构生成，要求管理后台与主系统零端口冲突、零用户身份泄露。*
