# Allo 开发者上手指南

本文档面向 Allo 项目的开发人员，覆盖本地开发环境搭建和线上服务器部署两条路径。

## 环境要求

| 工具 | 版本要求 | 安装方式 |
|------|----------|----------|
| Node.js | >= 22 | https://nodejs.org |
| pnpm | >= 10 | `npm install -g pnpm` |
| Python | >= 3.12 | https://python.org |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| nginx | any | `brew install nginx` (macOS) |

运行 `make check` 可一键验证所有依赖是否就绪。

## 项目结构速览

```
Allo/
├── backend/           Python 后端（LangGraph agent + FastAPI gateway）
├── frontend/          Next.js 前端
├── docker/            Docker 和 nginx 配置
├── scripts/           启动、部署、运维脚本
├── skills/public/     内置技能包
├── config.example.yaml   配置模板
├── extensions_config.example.json  MCP/技能扩展配置模板
├── Makefile           所有开发命令的入口
└── .env               环境变量（gitignored）
```

## 服务架构

```
浏览器 → nginx (:2026)
           ├── /api/langgraph/* → LangGraph Server (:2024)  agent 执行
           ├── /api/*           → Gateway API (:8001)        产品 API
           └── /*               → Next.js Frontend (:3000)   Web 界面
```

四个进程，nginx 统一入口，所有请求走 `localhost:2026`。

---

## 路径一：本地开发

适用于日常开发、调试、功能迭代。支持热重载。

### 1. 克隆仓库

```bash
git clone <repo-url> Allo
cd Allo
```

### 2. 安装依赖

```bash
make install
# 等价于：cd backend && uv sync + cd frontend && pnpm install
```

### 3. 生成配置文件

```bash
make config
```

这会从模板生成三个文件：
- `config.yaml` — 模型、工具、沙箱等主配置
- `.env` — API Key 等环境变量
- `extensions_config.json` — MCP 服务器和技能扩展

> `make config` 只在配置文件不存在时执行。已有配置时会中止，这是设计行为。

### 4. 配置模型

编辑 `config.yaml`，至少配置一个可用模型。示例（OpenAI 兼容代理）：

```yaml
models:
  - name: gpt-4o
    display_name: GPT-4o
    use: langchain_openai:ChatOpenAI
    model: gpt-4o
    api_base: https://your-relay/v1
    api_key: $OPENAI_API_KEY
    supports_vision: true
```

在 `.env` 中设置对应的 API Key：

```
OPENAI_API_KEY=sk-xxx
TAVILY_API_KEY=tvly-xxx    # 搜索工具需要
```

> `.env` 放在项目根目录。LangGraph 需要 `backend/.env`，可以用符号链接：`ln -s ../.env backend/.env`

### 5. 启动服务

```bash
make dev
```

启动顺序：LangGraph (:2024) → Gateway (:8001) → Frontend (:3000) → nginx (:2026)

启动成功后会看到：

```
✓ DeerFlow development server is running!

  🌐 Application: http://localhost:2026
```

日志位置：`logs/langgraph.log`、`logs/gateway.log`、`logs/frontend.log`、`logs/nginx.log`

### 6. 停止服务

```bash
make stop
```

### 常用开发命令

```bash
# 后端（在 backend/ 目录下）
make lint              # ruff 代码检查
make format            # ruff 自动格式化
make test              # 运行测试（277+ 用例）
make dev               # 单独启动 LangGraph server
make gateway           # 单独启动 Gateway API

# 前端（在 frontend/ 目录下）
pnpm dev               # 单独启动前端（Turbopack 热重载）
pnpm lint              # ESLint 检查
pnpm typecheck         # TypeScript 类型检查
pnpm build             # 生产构建（需要 BETTER_AUTH_SECRET）

# 注意：不要用 pnpm check，它是坏的。用 pnpm lint + pnpm typecheck 代替。
```

### 提交前检查清单

```bash
cd backend && make lint && make test        # 必须
cd frontend && pnpm lint && pnpm typecheck  # 如果改了前端
```

CI 会在每个 PR 上运行后端 lint + test（`.github/workflows/backend-unit-tests.yml`）。

---

## 路径二：服务器部署

适用于将代码部署到远程服务器运行。当前线上环境使用 systemd 管理服务。

### 服务器信息

| 项目 | 值 |
|------|-----|
| IP | 146.56.239.94 |
| SSH 用户 | ubuntu |
| 项目路径 | /srv/allo |
| 项目文件 owner | allo (uid 998) |
| 环境变量 | /etc/allo/allo.env |

### 服务器上的服务架构

```
Nginx (:80)
  ├── /api/langgraph/* → LangGraph (:2024)
  ├── /api/*           → Gateway (:8001)
  └── /*               → Frontend (:3000)
```

三个 systemd 服务：

| 服务名 | 进程 | 端口 |
|--------|------|------|
| allo-langgraph | `uv run langgraph dev --no-browser --allow-blocking` | 2024 |
| allo-gateway | `uv run uvicorn app.gateway.app:app --workers 2` | 8001 |
| allo-frontend | `node .next/standalone/server.js` | 3000 |

### 运行目录与用户一致性

线上环境要明确区分 **登录/部署用户** 和 **服务运行用户**：

- `ubuntu`：用于 SSH 登录、上传 bundle、执行 `sudo`
- `allo`：systemd 服务实际运行用户，也是代码目录和运行时数据目录的 owner

当前开发机上的路径约定是：

- 代码目录：`/srv/allo`
- 环境变量文件：`/etc/allo/allo.env`
- runtime 数据目录：当前落在 `/srv/allo/backend/.deer-flow`

这里要注意两点：

1. `/srv/allo` 只是当前机器的部署约定，不是产品硬编码。企业环境可以换成别的目录。
2. 真正重要的不是目录名，而是 **runtime 数据目录必须归服务运行用户所有**。

也就是说，企业部署时不需要有 `allo` 这个目录名，但需要保证：

- systemd 运行用户明确（例如 `allo`、`svc-allo`、`appuser`）
- `DEER_FLOW_HOME` 或运行时解析出的 base dir 归这个用户所有
- 不要让 `ubuntu` 或 `root` 成为 `.deer-flow` 的长期 owner

如果用 `ubuntu`/`root` 去解压、恢复、拷贝 `.deer-flow`，可能出现：

- 新 thread 无法创建工作目录
- `read_file` / `ls` / `write_file` 工具持续报 `PermissionError`
- subagent 持续重试，最终触发 `GRAPH_RECURSION_LIMIT`

推荐检查命令：

```bash
# 查看服务实际运行用户
sudo systemctl cat allo-langgraph
sudo systemctl cat allo-gateway

# 查看 runtime 数据目录 owner
sudo ls -ld /srv/allo/backend/.deer-flow

# 当前机器如需修复 owner
sudo chown -R allo:allo /srv/allo/backend/.deer-flow
```

团队约定：

- `ubuntu` 只负责登录、传包、执行 sudo
- 所有 `git / uv / pnpm` 操作都通过 `sudo -u allo` 执行
- `.deer-flow` 及其子目录必须保持 `allo:allo`

### 代码部署流程

服务器的 git origin 用的是镜像，同步有延迟。用 `git bundle` 传代码最可靠。

#### 本地操作

```bash
# 1. 创建 bundle（只包含新 commit）
git bundle create /tmp/update.bundle <branch> --not <base-commit>

# 2. 传到服务器
scp /tmp/update.bundle ubuntu@146.56.239.94:/tmp/update.bundle
```

#### 服务器操作

```bash
# 3. 导入并合并
sudo -u allo bash -c 'cd /srv/allo && \
  git fetch /tmp/update.bundle <branch>:<local-ref> && \
  git merge <local-ref> --ff-only'

# 4. 后端依赖更新（如果后端有改动）
sudo -u allo bash -c 'cd /srv/allo/backend && uv sync'

# 5. 前端构建（如果前端有改动）
sudo -u allo bash -c 'cd /srv/allo/frontend && CI=true pnpm install && pnpm build'

# 6. 重启受影响的服务
sudo systemctl restart allo-gateway allo-langgraph  # 后端改动
sudo systemctl restart allo-frontend                 # 前端改动

# 7. 健康检查（等 15 秒让 LangGraph 启动）
sleep 15
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2024/ok   # 200 = OK
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/models  # 401 = OK
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/     # 200 = OK
```

### 服务器日常运维

```bash
# 所有 git/uv/pnpm 操作必须用 allo 用户
sudo -u allo bash -c 'cd /srv/allo && <command>'

# 查看服务状态
sudo systemctl status allo-gateway allo-langgraph allo-frontend

# 重启所有服务
sudo systemctl restart allo-gateway allo-langgraph allo-frontend

# 查看实时日志
sudo journalctl -u allo-langgraph -f --no-pager
sudo journalctl -u allo-gateway -f --no-pager

# 查看最近 5 分钟日志
sudo journalctl -u allo-gateway --since '5 min ago' --no-pager

# 端口检查
sudo ss -tlnp | grep -E '2024|8001|3000'
```

### 数据库操作

```bash
# 查看最近的 thread
sudo -u postgres psql -d allo -c "SELECT id, title, created_at FROM threads ORDER BY created_at DESC LIMIT 5;"

# 新建表后必须授权
sudo -u postgres psql -d allo -c "GRANT ALL ON TABLE <table_name> TO allo;"
```

---

## 路径三：Docker 部署

适用于不想手动管理进程的场景。

### Docker 开发环境

```bash
make config           # 生成配置（首次）
make docker-init      # 拉取沙箱镜像
make docker-start     # 启动所有服务
# 访问 http://localhost:2026
make docker-stop      # 停止
make docker-logs      # 查看日志
```

### Docker 生产部署

```bash
make up               # 构建镜像并启动（含 postgres、redis、nginx）
make down             # 停止并移除容器
```

生产 Docker 栈包含：postgres、redis、nginx、frontend、gateway、langgraph，全部容器化。

---

## 常见问题

### `make config` 报错说配置已存在

这是设计行为。`make config` 只用于首次生成。已有配置时直接编辑 `config.yaml`。

配置模板有更新时，运行 `make config-upgrade` 合并新字段。

### 前端 build 失败：缺少 BETTER_AUTH_SECRET

```bash
BETTER_AUTH_SECRET=local-dev-secret pnpm build
```

或设置 `SKIP_ENV_VALIDATION=1` 跳过环境校验。

### LangGraph 启动失败：ImportError

通常是 `uv sync` 删除了手动安装的包。确保所有依赖都在 `pyproject.toml` 中声明，然后重新 `uv sync`。

### 代理环境变量导致 pnpm install 失败

取消代理变量后重试：

```bash
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
pnpm install
```

### .env 路径不匹配

`langgraph.json` 期望 `.env` 在 `backend/` 下，但 `make config` 生成在项目根目录。用符号链接解决：

```bash
ln -s ../.env backend/.env
```
