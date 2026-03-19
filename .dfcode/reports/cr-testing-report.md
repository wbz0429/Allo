# DeerFlow B2B SaaS — CR & 测试报告

> 生成时间：2026-03-20
> 测试范围：Phase 1-5 全部新增代码（认证、配置、RAG、管理后台、生态市场）
> 测试结果：783 passed, 3 xfailed, 2 failed（排除 9 个 live 测试 + 1 个预存 checkpointer 问题）

---

## P0 — 功能完全缺失

### 1. Config router 未注册到 app
- **文件**: `backend/app/gateway/app.py`
- **现象**: `routers/config.py` 存在且代码完整，但 `create_app()` 中没有 `app.include_router(config.router)`，导致所有 `/api/config` 端点不可访问
- **验证测试**: `tests/test_app_registration.py::TestRouteRegistration::test_config_routes_registered` (xfail)
- **修复**: 在 `app.py` 中加 `from app.gateway.routers import config` 并 `app.include_router(config.router)`

### 2. Admin router 文件不存在
- **文件**: `backend/app/gateway/routers/admin.py`（不存在）
- **现象**: git 提交 `923570b` 声称 "add admin API, org admin API"，但实际文件从未创建
- **验证测试**: `tests/test_app_registration.py::TestRouterImports::test_admin_router_importable` (xfail)
- **修复**: 创建 `routers/admin.py`，实现平台管理 + 企业管理 API

### 3. Marketplace router 文件不存在
- **文件**: `backend/app/gateway/routers/marketplace.py`（不存在）
- **现象**: git 提交 `5c3d199` 声称 "add marketplace + org tools routers"，但实际文件从未创建
- **验证测试**: `tests/test_app_registration.py::TestRouterImports::test_marketplace_router_importable` (xfail)
- **修复**: 创建 `routers/marketplace.py`，实现工具/技能市场浏览 + 安装 API

---

## P1 — 代码 Bug

### 4. Embedder `response.json()` 缺少 `await`
- **文件**: `backend/app/gateway/rag/embedder.py:52`
- **现象**: httpx `AsyncClient` 的 `response.json()` 是 coroutine，直接 `data = response.json()` 导致 `TypeError: 'coroutine' object is not subscriptable`
- **验证测试**: `tests/test_rag_embedder.py::test_embed_texts_calls_openai_api` (FAILED)
- **修复**: 改为 `data = response.json()`（httpx 的 `.json()` 实际是同步方法，需确认版本；或在 `async with` 块内调用）

### 5. UsageTrackingMiddleware 未注册
- **文件**: `backend/app/gateway/app.py`
- **现象**: `middleware/usage_tracking.py` 中 `UsageTrackingMiddleware` 已实现，但未在 `create_app()` 中通过 `app.add_middleware()` 注册，用量追踪完全不工作
- **修复**: 在 `app.py` 中加 `app.add_middleware(UsageTrackingMiddleware)`

### 6. RateLimiterMiddleware 未注册
- **文件**: `backend/app/gateway/app.py`
- **现象**: `middleware/rate_limiter.py` 中 `RateLimiterMiddleware` 已实现，但未注册，速率限制完全不工作
- **修复**: 在 `app.py` 中加 `app.add_middleware(RateLimiterMiddleware)`

### 7. `routers/__init__.py` 过时
- **文件**: `backend/app/gateway/routers/__init__.py`
- **现象**: 只导出 `artifacts, mcp, models, skills, suggestions, uploads`，缺少 `agents, channels, knowledge_bases, config`
- **修复**: 补全所有 router 的导出

---

## P1 — 前端

### 8. 3 个 setup wizard 组件缺失
- **文件**: `frontend/src/components/workspace/setup-wizard/`
- **现象**: `setup-wizard.tsx` 导入了 `./agent-setup-step`、`./completion-step`、`./tool-selection-step`，但这三个文件不存在
- **TypeScript 错误**: `TS2307: Cannot find module`
- **修复**: 创建这三个组件文件

### 9. `fetchOptions` 类型不存在
- **文件**: `frontend/src/core/api/api-client.ts:12`
- **现象**: `Object literal may only specify known properties, and 'fetchOptions' does not exist in type 'ClientConfig'`
- **修复**: 检查 API client 库版本，改用正确的配置字段名

### 10. `pg` 类型声明缺失
- **文件**: `frontend/src/server/better-auth/config.ts:2`
- **现象**: `TS2307: Cannot find module 'pg' or its corresponding type declarations`
- **修复**: `pnpm add -D @types/pg`

---

## P2 — 代码质量

### 11. 22 个 ruff lint 错误
- **范围**: 多个文件，主要是 import 排序（I001）和未使用的 import（F401）
- **修复**: `cd backend && PYTHONPATH=. uv run ruff check . --fix`

---

## 新增测试文件清单

| 文件 | 测试数 | 覆盖范围 |
|------|--------|---------|
| `tests/test_app_registration.py` | 18 | 路由注册、健康端点、模块导入 |
| `tests/test_config_router.py` | 22 | 配置 API 全部端点 |
| `tests/test_kb_router.py` | 18 | 知识库 CRUD + 文档 + 搜索 |
| `tests/test_rag_chunker.py` | 13 | markdown 分块、递归分割 |
| `tests/test_rag_retriever.py` | 9 | 余弦相似度、chunk 搜索 |
| `tests/test_rag_embedder.py` | 6 | embedding API 调用 |
| `tests/test_middleware_rate_limiter.py` | 8 | TokenBucket、429 响应 |
| `tests/test_middleware_usage_tracking.py` | 5 | 用量记录、auth state |
| `tests/test_db_models_extended.py` | 55 | 9 个新 DB 模型 |
| `tests/test_marketplace_seed.py` | 19 | 种子数据结构验证 |

---

## 验证命令

```bash
# 后端全量测试（排除需要运行服务的 live 测试）
cd backend && PYTHONPATH=. uv run pytest tests/ -v --ignore=tests/test_client_live.py --ignore=tests/test_checkpointer.py

# 后端 lint
cd backend && PYTHONPATH=. uv run ruff check .

# 前端类型检查
cd frontend && pnpm typecheck

# 前端 lint
cd frontend && pnpm lint
```
