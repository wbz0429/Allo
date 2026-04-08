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

## 九、2026-04-06 本地/线上 Skill 运行问题补充总结

### 1. 问题概览

本次排查的对象是自定义 skill `huaneng-bidding-scaffold`。问题不是单点崩溃，而是多类运行时问题叠加：

- 长任务执行链路过长，容易在真正进入生成脚本阶段前就耗尽 graph recursion budget
- 模型可见路径与实际可执行路径不完全一致，导致 agent 会混用宿主路径和 `/mnt/...` 虚拟路径
- `reference_impl.py` 相关“权限错误”更多是 agent 推断或路径策略误判，不是宿主文件本身不可读
- 运行环境里 `python-docx` 不是基础依赖，skill 会在执行期动态安装依赖，进一步拉长执行链路
- thread history / context 链路存在不稳定现象，长任务时会加剧 agent 不收敛问题

### 2. 已确认的关键现象

#### 2.1 用户侧观察到的现象

用户侧反馈和运行轨迹中，出现过这些关键现象：

- thread 长时间停留在“正在执行任务...”，没有明确结束
- skill 执行步骤中，反复出现：
  - 查看技能目录和资产文件
  - 读取 `reference_impl.py`
  - 检查 Python 依赖
  - 创建 `.venv`
  - 安装 `python-docx`
- 用户明确观察到：
  - “当前阻碍：reference_impl.py 无法直接读取，报权限错误；但文件存在”
  - “本地也有权限问题”
  - “三次读取，是用的系统路径，不是软隔离路径”
  - “这个任务很长，主要就是历史截断和配置环境异常”

#### 2.2 真实运行轨迹中观察到的现象

本地与线上的实际执行轨迹显示：

- skill 的 assets 目录存在，且 `reference_impl.py`、图标文件都存在
- agent 在某些阶段会正确使用虚拟路径：
  - `/mnt/skills/custom/huaneng-bidding-scaffold/...`
  - `/mnt/user-data/workspace/...`
- 但 agent 也会拿到宿主真实路径，例如：
  - `/Users/steven/VaaT-Flow/backend/.deer-flow/users/.../skills/custom/.../reference_impl.py`
  - 线上对应 `/srv/allo/backend/.deer-flow/users/.../skills/custom/...`
- 这类真实路径不是 skill 自己定义的固定接口，而是系统内部运行态信息泄漏到 agent 可见上下文后，被 agent 复用进后续步骤

### 3. 关于“权限错误”的排查结论

#### 3.1 宿主文件系统权限本身没有坏

本地实际验证结果：

- `reference_impl.py` 文件存在
- 文件权限正常（`0644`）
- 当前用户可以直接读取该文件
- 可以把该文件复制到 workspace

这意味着：

- 宿主机层面的 Linux/macOS 文件权限不是主因
- “Permission denied” 不是当前问题的核心根因

#### 3.2 真正的问题是“路径策略 + 上下文污染”

当前系统既有：

- 宿主真实路径（内部 runtime state 使用）
- `/mnt/...` 虚拟路径（希望 agent 使用）

但实际执行里，agent 同时看到了两套路径。这会造成：

- agent 有时按 `/mnt/...` 正常工作
- agent 有时又抄用 `/Users/...` 或 `/srv/...`
- 一旦后续工具链只对某一类路径做了校验/映射，就会出现“模型看到的路径”和“真正可执行的路径”不一致

### 4. 为什么会出现“没有被 mask”

当前问题不只是“正则漏了一种路径格式”，更关键的是：

- 现有 mask 主要针对 tool 文本输出与 bash 命令字符串
- 但 `ThreadDataMiddleware.before_agent` 之类的结构化 `updates` 事件，直接把真实 `thread_data` 发到了流里
- 这类结构化 payload 没有经过现有文本 mask 管道

因此会出现：

- `workspace_path` / `user_skills_path` 等真实宿主路径被暴露给 agent
- agent 后续将这些路径作为“可用路径知识”继续使用

这解释了为什么用户会看到：

- 同一个 skill 执行过程中，既出现 `/mnt/skills/custom/...`
- 又出现 `/Users/.../.deer-flow/...` 或 `/srv/allo/backend/.deer-flow/...`

### 5. 当前对执行效果最重要的原则

当前优先级不应是“绝对不泄漏路径”，而应是：

> 模型看到的路径，必须能成功执行。

也就是说，系统至少要保证其中一种成立：

- agent 看到 `/mnt/...`，且 `/mnt/...` 能稳定执行
- agent 看到了宿主真实路径，系统也能兼容并成功执行

最差情况是：

- agent 看到的是路径 A
- 系统真正只能执行路径 B
- 最终导致长任务空转、重试、循环增加

### 6. 已做的兼容性修复

为了不先改 skill，本次优先在 Allo 内部做了兼容：

- local sandbox 增加了对“用户 custom skill 宿主路径”的兼容识别
- 允许将用户 custom skill host path 映射/兼容到 `/mnt/skills/custom/...` 语义通道
- 对应测试已补齐并通过

这部分已经证明：

- custom skill 资产路径兼容本身不是当前主 blocker
- 现在更大的问题已经切换到长任务 orchestration

### 7. 当前真正的主 blocker：Graph Recursion / 长任务不收敛

本地重跑 skill 后，已经确认：

- skill 会成功读 `SKILL.md`
- 会成功列出 `assets/`
- 会识别缺失依赖并尝试安装 `python-docx`
- 但经常还没进入真正的文档生成脚本执行阶段，就先撞上 graph recursion limit

已确认的失败形态：

- `GraphRecursionError`
- `Recursion limit of 25 reached without hitting a stop condition`

这说明当前主问题已经从“路径权限”转移为：

- agent 在“读 skill 说明 -> 读资产 -> 检查环境 -> 再决策”之间来回过多轮
- 执行图没有足够快地收敛到“复制 reference_impl / 写生成脚本 / 执行脚本”阶段

### 8. context / history 问题

用户反馈“context 给得太少、thread 看不到历史记录”，这点不是错觉。

排查中出现过：

- 某些 thread 的 history / detail 查询不稳定
- 长任务时历史回放和上下文注入体验不足

这会进一步加剧：

- agent 不知道自己已经做到了哪一步
- 模型更容易重复读 skill 说明、重复探测环境、重复规划
- recursion 消耗更快

### 9. 已调整的默认运行参数

为减轻当前长任务问题，已经在本地提高：

- 默认 `recursion_limit`：`100 -> 250`
- `memory.max_injection_tokens`：`2000 -> 6000`

对应测试已在本地通过，说明默认值调整本身有效。

### 10. 当前建议修复方向

优先级建议如下：

1. **执行一致性优先**
   - 保证 agent 看到的路径一定可执行
   - 不要出现“显示路径”和“执行路径”两套语义脱节

2. **修复结构化 updates 的路径泄漏/不一致问题**
   - 不一定非要 mask
   - 但必须保证 agent 不会被注入不可执行的宿主路径知识

3. **继续优化长任务 orchestration**
   - 降低 skill 说明重复阅读
   - 更快进入复制/写脚本/执行脚本阶段
   - 减少无效决策轮次

4. **必要时再固化运行环境**
   - 避免每次运行时都重新安装 `python-docx`
   - 或对依赖检查/安装做更明确的收敛策略

### 11. 当前总体判断

当前 `huaneng-bidding-scaffold` 的问题，不应再简单归类为“文件权限错误”。

更准确的判断是：

- 路径可见性与执行一致性存在缺口
- 结构化 updates 泄漏了宿主路径知识
- 长任务 orchestration 不收敛，先撞上 recursion limit
- context/history 体验不足，加重了重复决策与长链路问题

因此后续修复应以：

- **保证模型看到的路径可执行**
- **保证长任务尽快收敛到真正的脚本执行阶段**

为核心目标，而不是仅仅围绕“是否要 mask 宿主路径”做表层处理。

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
