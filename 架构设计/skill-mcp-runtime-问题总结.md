# Skill / MCP Runtime 问题总结

更新时间：2026-04-01

## 一、结论摘要

当前系统里，`skill` 和 `MCP` 的多租户能力不处于同一成熟度。

- `MCP`：配置隔离和执行级隔离已经基本打通
- `Skill`：用户级 toggle 已打通，但 marketplace install 与 runtime / settings 最终视图还没有统一收口

也就是说，当前最核心的问题不是多租户主架构错误，而是：

1. `marketplace installed skills`
2. `settings /api/skills` 返回的 skills 列表
3. `make_lead_agent` / prompt / runtime 真正可用的 skills 集合

这三层还没有统一成一份“最终 skill catalog”。


## 二、当前 Skill 的真实状态

### 1. 已经成立的部分

#### 1.1 用户级 skill toggle 已租户化

当前 `skills` 配置已经从全局文件态切到了数据库：

- 表：`user_skill_configs`
- 路由：`/api/skills`
- store：`PostgresSkillConfigStore`

已经验证：

- 用户 A 可以把 `bootstrap` 设为 `enabled=false`
- 用户 B 不受影响

#### 1.2 marketplace 安装记录已租户化

当前 marketplace skill install/uninstall 记录已经按 org 落库并隔离：

- 表：`org_installed_skills`
- A 安装的 skill，B 看不到
- A 卸载后记录会消失

#### 1.3 runtime 上下文已能拿到 user/org

已经验证真实 LangGraph runtime 能拿到：

- `user_id`
- `org_id`

也就是说，多租户上下文透传不是当前的主阻塞点。


### 2. 当前真正的问题

#### 2.1 `/api/skills` 不是最终用户 skill 表单

当前 `backend/app/gateway/routers/skills.py` 的逻辑本质上是：

1. `load_skills(enabled_only=False)`
2. 应用用户 toggle（`_apply_user_toggles`）

但它没有合并：

- marketplace installed skills

所以当前 `/api/skills` 返回的其实是：

- “公共 skill 列表 + 用户 toggle 视图”

不是：

- “当前用户最终拥有的 skill catalog”

这意味着：

- 未安装的 marketplace skill，理论上不该出现在用户 skill 表单中
- 但当前 `/api/skills` 还没有体现这一层过滤

#### 2.2 runtime 也没有稳定使用统一 skill catalog

当前 runtime 侧已经开始做 `marketplace -> runtime_skill_name` 映射和 gating，但还没有完全收口。

已有进展：

- `marketplace_skills.runtime_skill_name` 已加入 schema
- 例如：
  - `skill-deep-research -> deep-research`
  - `skill-data-analysis -> data-analysis`

但目前 skill runtime 仍存在以下问题：

- 脚本级验证中，A/B 差异可以生效
- 真实 runtime 链路里，最终 skill 集合仍未完全与 install 记录保持一致

这说明：

- `marketplace installed skills`
- `settings skills`
- `runtime skills`

三者还没有共享同一个最终决议逻辑。


## 三、Skill 的正确目标模型

正确的产品与运行时模型应该是：

### 1. 用户 skill catalog

对每个用户/组织，系统应先形成一个统一的 skill catalog。

其来源为：

- 平台默认分配的 built-in skills
- 当前 org 已安装的 marketplace skills

即：

`user_skill_catalog = builtins_assigned + marketplace_installed`

### 2. enable / disable 只作用于 catalog 内部

启用状态不是决定“有没有资格拥有 skill”，而是决定：

- 已经属于该用户 catalog 的 skill，当前是否启用

即：

`runtime_available_skills = user_skill_catalog ∩ enabled_skills`

### 3. 必须统一到一个 resolver

后续系统中以下两处都应该读同一个 resolver：

- `/api/skills` 管理页视图
- `make_lead_agent` / prompt / runtime 的最终可用 skill 集合

否则会继续出现：

- 管理页看到一套
- runtime 实际跑的是另一套


## 四、为什么当前 Skill 是个真实问题

因为现在 install / enable / runtime 三层没有统一，用户会遇到这些真实语义问题：

1. 我 install 了 skill，但为什么 runtime 不一定能用？
2. 我没 install，为什么 settings 里仍然能看到它？
3. settings enable 和 marketplace install 到底谁决定最终可用？

这些不是文案问题，而是模型没有完全收口。


## 五、MCP 是否存在同样问题？

### 1. 结论

`MCP` 不完全是同一个问题。

当前 MCP 的主问题不是 “install 与 runtime 脱节”，而是配置与执行隔离是否成立。

这部分目前已经基本打通：

- `/api/mcp/config` 已切到 per-user / per-org DB 配置
- `PostgresMcpConfigStore` 已按用户读取不同 MCP 配置
- MCP 执行级验证已做过：
  - 用户 A 与 B 对同一个 MCP server 名称
  - 注入不同 env
  - tool 执行返回不同结果

所以 MCP 当前的状态更像：

- 配置层：已租户化
- 执行层：已验证隔离

### 2. 为什么 MCP 和 Skill 不一样

因为当前 MCP 没有完全等价于 marketplace skill 的“双状态”结构。

Skill 当前被拆成了：

- built-in/public skill
- marketplace installed skill
- settings enabled skill

而 MCP 当前更接近：

- 当前用户有哪些 MCP 配置
- runtime 直接加载这些配置

也就是说，MCP 缺少一个像 skill 那样的“catalog / install / enable 三层并存”的历史包袱。

所以它没有 Skill 那么明显的“install 记录和 runtime 不一致”的问题。

### 3. MCP 仍然可能有的后续问题

虽然 MCP 不存在完全同样的问题，但后续如果引入“公共 MCP marketplace”，也会出现类似结构风险：

- 平台公共 MCP 模板
- 用户安装态
- 用户启用态
- runtime 最终可用 MCP 集合

如果未来做这层 marketplace，就应该从一开始就设计成统一 resolver，而不要重复 Skill 当前的分裂状态。


## 六、当前建议的修复方向

### Skill

应新增一个统一的 skill catalog 决议层（resolver），统一输入：

- built-in 默认技能
- org installed marketplace skills
- user/org skill toggles

统一输出：

- 当前用户最终拥有的 skill catalog
- 当前用户最终启用的 runtime skill 集合

且以下两处必须共享同一套 resolver：

- `/api/skills`
- `make_lead_agent` / prompt / runtime

### MCP

MCP 当前主线可以保持：

- per-user config
- per-user runtime load
- per-user execution context

短期不需要引入和 Skill 一样复杂的 install 层。


## 七、最终判断

### Skill

当前是一个真实未收口问题：

- 多租户基础没错
- install / toggle / runtime 三层没有统一
- 需要继续实现统一 skill catalog resolver

### MCP

当前不属于同一个问题类型：

- 它的 per-user config 和执行隔离主线已经基本成立
- 暂时没有 Skill 那种 install/runtime 脱节问题


## 八、后续实施建议

建议后续按以下顺序推进：

1. 实现统一 skill catalog resolver
2. 让 `/api/skills` 改为返回最终 catalog 视图
3. 让 runtime 读取同一 resolver 的结果
4. 用真实请求验证：
   - 未安装不可用
   - 已安装且启用可用
   - 已安装但禁用不可用
   - 卸载后不可用
5. 最后统一前端文案：
   - built-in: enable / disable
   - marketplace: install / uninstall
   - 最终页只展示属于当前用户 catalog 的项目
