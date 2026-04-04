# 线上部署 SOP

## 部署前检查

```bash
# 本地
cd /Users/steven/VaaT-Flow
PYTHONPATH=backend uv run pytest backend/tests/test_harness_boundary.py backend/tests/test_runtime_context.py backend/tests/test_skill_catalog_resolver.py -q
cd frontend && pnpm lint --quiet && pnpm typecheck
```

## 推送代码

```bash
git push origin feature/pre_develop_local
```

## 服务器拉取

```bash
# 服务器上（gitclone.com 镜像有延迟，用 SCP 更快）
# 方式 1: git pull（镜像同步后）
ssh ubuntu@146.56.239.94 "cd /srv/allo && git pull"

# 方式 2: SCP 单文件（镜像未同步时）
scp <file> ubuntu@146.56.239.94:/tmp/<file>
ssh ubuntu@146.56.239.94 "sudo cp /tmp/<file> /srv/allo/<path> && sudo chown allo:allo /srv/allo/<path>"
```

## 后端部署

```bash
ssh ubuntu@146.56.239.94 "
  sudo chown -R ubuntu:ubuntu /srv/allo/backend/
  cd /srv/allo/backend && export PATH=\$HOME/.local/bin:\$PATH && uv sync
  sudo chown -R allo:allo /srv/allo/
  sudo systemctl restart allo-gateway allo-langgraph
"
```

## 前端部署

```bash
ssh ubuntu@146.56.239.94 "
  sudo chown -R ubuntu:ubuntu /srv/allo/frontend/.next/
  cd /srv/allo/frontend && pnpm build
  sudo chown -R allo:allo /srv/allo/
  sudo systemctl restart allo-frontend
"
```

## 部署后 SOP 测试（必须执行）

```bash
ssh ubuntu@146.56.239.94 "
echo '=== 1. 服务状态 ==='
for svc in allo-gateway allo-langgraph allo-frontend; do
  echo \"\$svc: \$(systemctl is-active \$svc)\"
done

echo '=== 2. 端口 ==='
for port in 80 3000 8001 2024; do
  echo \"port \$port: \$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:\$port)\"
done

echo '=== 3. 登录 ==='
curl -s -c /tmp/sop.txt -X POST http://127.0.0.1:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{\"email\":\"dev@allo.local\",\"password\":\"Password123!\"}' | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"email\",\"FAIL\"))'

echo '=== 4. Skills ==='
curl -s -b /tmp/sop.txt http://127.0.0.1:8001/api/skills | python3 -c 'import sys,json; print(len(json.load(sys.stdin).get(\"skills\",[])))'

echo '=== 5. 创建 Thread + 发消息 ==='
TID=\$(python3 -c 'import uuid; print(uuid.uuid4())')
curl -s -b /tmp/sop.txt -X POST http://127.0.0.1:8001/api/threads \
  -H 'Content-Type: application/json' \
  -d \"{\\\"thread_id\\\":\\\"\$TID\\\",\\\"title\\\":\\\"SOP\\\"}\" > /dev/null

RESULT=\$(curl -s -b /tmp/sop.txt --max-time 60 \
  -X POST \"http://127.0.0.1:80/api/langgraph/threads/\$TID/runs/stream\" \
  -H 'Content-Type: application/json' \
  -d \"{\\\"assistant_id\\\":\\\"lead_agent\\\",\\\"input\\\":{\\\"messages\\\":[{\\\"role\\\":\\\"user\\\",\\\"content\\\":\\\"hi\\\"}]},\\\"stream_mode\\\":[\\\"messages\\\"],\\\"config\\\":{\\\"configurable\\\":{\\\"thread_id\\\":\\\"\$TID\\\"}}}\")

if echo \"\$RESULT\" | grep -q 'event: messages/complete'; then
  echo 'message: OK'
elif echo \"\$RESULT\" | grep -q 'event: messages/metadata'; then
  echo 'message: STREAM_STARTED (model may be slow)'
else
  echo 'message: FAIL'
  echo \"\$RESULT\" | head -5
fi

echo '=== 6. 错误检查 ==='
sudo journalctl -u allo-gateway --no-pager --since '2 min ago' --output=cat 2>&1 | grep -iE 'error|exception|500' | grep -v 'hardlink' | tail -3
sudo journalctl -u allo-langgraph --no-pager --since '2 min ago' --output=cat 2>&1 | grep -v '.venv\|changes detected' | grep -iE 'error|exception|startup failed' | tail -3
"
```

## 已知的坑（部署时注意）

### 1. 文件权限

服务以 `allo` 用户运行，但 git/scp 操作用 `ubuntu` 用户。每次修改文件后必须：
```bash
sudo chown -R allo:allo /srv/allo/
```

### 2. systemd ProtectSystem=strict

服务文件有 `ProtectSystem=strict`，只有 `ReadWritePaths` 列出的目录可写。当前允许：
- `/var/lib/allo` — 数据 + uv cache
- `/var/log/allo` — 日志
- `/tmp`
- `/srv/allo` — 代码 + .venv

如果新增需要写入的路径，必须加到 systemd 的 `ReadWritePaths`。

### 3. 前端 env 变量名

前端代码使用的变量名：
- `NEXT_PUBLIC_BACKEND_BASE_URL` — 留空（前端代码自己拼 `/api` 前缀）
- `NEXT_PUBLIC_LANGGRAPH_BASE_URL` — `http://<IP>/api/langgraph`

**不是** `NEXT_PUBLIC_GATEWAY_URL` 或 `NEXT_PUBLIC_LANGGRAPH_URL`。

env 变量在 `pnpm build` 时注入，修改后必须重新 build。

### 4. config.yaml 有两份

- `/srv/allo/config.yaml` — 根目录的，不被 LangGraph 读取
- `/srv/allo/backend/config.yaml` — 实际被加载的

修改 checkpointer、models 等配置时改 `backend/config.yaml`。

### 5. Checkpointer 必须用 PostgreSQL

`backend/config.yaml` 中：
```yaml
checkpointer:
  type: postgres
  connection_string: postgresql://allo:<password>@127.0.0.1:5432/allo?sslmode=disable
```

SQLite 在 systemd 环境下因权限问题无法创建文件。

### 6. DATABASE_URL 需要 `?ssl=disable`

本地 PG 连接不需要 SSL，但 asyncpg 默认尝试 SSL 客户端证书，被 `ProtectHome=true` 阻止。

### 7. gitclone.com 镜像同步延迟

GitHub 推送后 gitclone.com 镜像可能需要几分钟同步。紧急部署用 SCP。

### 8. uv 安装位置

uv 装在 `/home/ubuntu/.local/bin/`，已复制到 `/usr/local/bin/uv`。systemd 服务使用 `/usr/local/bin/uv`。

### 9. PyPI 镜像

服务器配置了清华镜像加速：`~/.config/uv/uv.toml`
