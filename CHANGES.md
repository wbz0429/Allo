# CORS 和 Auth 修复总结

## 修复概述

本次修复解决了前端"工具"页面无法访问 MCP 配置接口的问题，主要包含以下三个方面的修改：

### 1. CORS 支持 (backend/app/gateway/app.py, backend/app/gateway/config.py)

**问题**: 前端在浏览器中直接请求 `http://localhost:8001/api/mcp/config` 时，由于网关没有启用 CORS，导致浏览器报 `Failed to fetch` 错误。

**修复**:
- 在 `app.py` 中添加了 `CORSMiddleware`，允许来自 `http://localhost:3000` 和 `http://127.0.0.1:3000` 的跨域请求
- 在 `config.py` 中更新了默认 CORS origins，包含两个本地开发地址
- 支持通过 `CORS_ORIGINS` 环境变量自定义允许的源

**关键代码**:
```python
# app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_gateway_config().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# config.py
cors_origins: list[str] = Field(
    default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
    description="Allowed CORS origins",
)
```

### 2. MCP 配置接口可选鉴权 (backend/app/gateway/routers/mcp.py)

**问题**: MCP 配置接口 (`/api/mcp/config`) 使用严格的鉴权，导致本地开发时页面因为 session/dev auth 状态异常而直接失败。

**修复**:
- 将 `get_auth_context` 替换为 `get_optional_auth_context`
- 允许接口在无认证状态下返回 200
- 保持有认证时的正常行为

**关键代码**:
```python
# 修改前
from app.gateway.auth import AuthContext, get_auth_context
async def get_mcp_configuration(auth: AuthContext = Depends(get_auth_context)) -> McpConfigResponse:

# 修改后
from app.gateway.auth import AuthContext, get_optional_auth_context
async def get_mcp_configuration(auth: AuthContext | None = Depends(get_optional_auth_context)) -> McpConfigResponse:
```

### 3. SKIP_AUTH 运行时读取 (backend/app/gateway/auth.py)

**问题**: `SKIP_AUTH` 是模块级别的常量，在导入时就被确定，导致导入顺序可能影响本地开发模式的生效。

**修复**:
- 将 `SKIP_AUTH` 改为运行时函数 `_get_runtime_skip_auth()`
- 每次调用时重新读取环境变量
- 确保导入顺序不会影响行为

**关键代码**:
```python
# 修改前
_env = os.getenv("ENV", os.getenv("NODE_ENV", "development")).lower()
_skip_auth_raw = os.getenv("SKIP_AUTH", "0") == "1"
if _skip_auth_raw and _env not in ("development", "dev", "test"):
    SKIP_AUTH = False
else:
    SKIP_AUTH = _skip_auth_raw

# 修改后
def _get_runtime_env() -> str:
    return os.getenv("ENV", os.getenv("NODE_ENV", "development")).lower()

def _get_runtime_skip_auth() -> bool:
    env_name = _get_runtime_env()
    skip_auth_raw = os.getenv("SKIP_AUTH", "0") == "1"
    if skip_auth_raw and env_name not in ("development", "dev", "test"):
        return False
    return skip_auth_raw
```

## 测试更新

### 更新的测试文件

1. **backend/tests/test_auth.py**
   - 更新了所有使用 `SKIP_AUTH` 的测试，改为使用 `_get_runtime_skip_auth()`
   - 添加了新的测试函数：
     - `test_get_runtime_env_from_env()`
     - `test_get_runtime_env_from_node_env()`
     - `test_get_runtime_env_defaults_to_development()`
     - `test_get_runtime_env_is_lowercased()`
     - `test_get_runtime_skip_auth_true_in_dev()`
     - `test_get_runtime_skip_auth_false_in_production()`
     - `test_get_runtime_skip_auth_false_when_zero()`
     - `test_get_runtime_skip_auth_false_when_not_set()`
     - `test_get_runtime_skip_auth_true_in_test()`
     - `test_get_runtime_skip_auth_true_in_dev_short()`

2. **backend/tests/test_gateway_config.py** (新增)
   - 测试 CORS 配置默认值
   - 测试环境变量解析
   - 测试多 origin 分割
   - 测试配置缓存行为

### 测试验证方法

```bash
cd backend
PYTHONPATH=. uv run pytest tests/test_auth.py -v
PYTHONPATH=. uv run pytest tests/test_gateway_config.py -v
```

## 验证步骤

1. 重启网关服务 (port 8001)
2. 刷新前端页面
3. 进入"设置 -> 工具"
4. 确认 GET `/api/mcp/config` 返回 200

## 安全注意事项

- `SKIP_AUTH=1` 仅在 `development`, `dev`, `test` 环境下生效
- 生产环境 (`production`) 即使设置 `SKIP_AUTH=1` 也会被拒绝
- CORS 配置仅影响本地开发，生产环境应通过 nginx 处理 CORS
