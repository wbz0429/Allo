---
date: 2026-04-06
topic: work-mode-redesign
status: draft
---

# 工作模式重设计：自主 / 精确 / 极速

## Context

当前 Allo 的模式系统（flash/thinking/pro/ultra）是基于模型能力的功能分级，控制 thinking、plan mode、subagent 等能力开关。但未来所有模型都将支持全部能力，模式选择器不再需要 gate 功能。

同时，当前 agent 的交互风格过于频繁地向用户澄清（system prompt 强制 CLARIFY → PLAN → ACT），部分用户希望 agent 能自主推进、快速交付。

本次重设计将模式从"能力分级"转变为"工作风格"，通过 system prompt 差异控制 agent 的交互行为。

## 模式定义

| 内部 ID | 中文名 | 英文名 | 图标 | 默认推理力度 | 是否默认 |
|---------|--------|--------|------|-------------|---------|
| `autonomous` | 自主 | Autonomous | 🧭 CompassIcon | `high` | ✅ |
| `precise` | 精确 | Precise | 🎯 TargetIcon | `high` | |
| `express` | 极速 | Express | ⚡ ZapIcon | `high` | |

所有模式全能力开启：`thinking_enabled=true`、`is_plan_mode=true`、`subagent_enabled=true`。

推理力度默认都是 `high`，与模式解耦，用户可通过独立选择器手动调整。

## 模式行为差异

### 自主模式（Autonomous）— 默认
- 描述（中）：自主决策，关键节点才确认，适合日常工作
- 描述（英）：Makes decisions autonomously, only confirms at critical points
- `ask_clarification` 工具：可用
- 澄清策略：只在高风险/不可逆操作时才澄清；需求模糊时选择最合理方案自主推进；完成后简要说明做了哪些决策和假设
- `recursion_limit`: 150

### 精确模式（Precise）
- 描述（中）：每步确认，确保结果精准，适合重要任务
- 描述（英）：Confirms each step for precise results, ideal for critical tasks
- `ask_clarification` 工具：可用
- 澄清策略：保留当前完整的 CLARIFY → PLAN → ACT 流程，5 种场景都必须澄清
- `recursion_limit`: 100

### 极速模式（Express）
- 描述（中）：直接交付，不中断提问，适合快速出活
- 描述（英）：Delivers end-to-end without interruptions, ideal for quick results
- `ask_clarification` 工具：从工具列表移除
- 澄清策略：无澄清指令，直接执行，完成后简要汇报假设和决策
- `recursion_limit`: 300

## 前端改动

### 1. 类型定义
- `InputMode` 从 `"flash" | "thinking" | "pro" | "ultra"` 改为 `"autonomous" | "precise" | "express"`
- 影响文件：`input-box.tsx`、`local.ts`（LocalSettings）

### 2. 模式→后端标志映射（`hooks.ts:451-453`）
```typescript
// 旧
thinking_enabled: context.mode !== "flash",
is_plan_mode: context.mode === "pro" || context.mode === "ultra",
subagent_enabled: context.mode === "ultra",

// 新
thinking_enabled: true,
is_plan_mode: true,
subagent_enabled: true,
interaction_style: context.mode,  // 新增
```

### 3. recursion_limit 动态设置（`hooks.ts:463`）
```typescript
// 旧
config: { recursion_limit: 150 },

// 新
config: {
  recursion_limit: context.mode === "express" ? 300
    : context.mode === "precise" ? 100
    : 150,
},
```

### 4. 推理力度映射（`input-box.tsx` handleModeSelect）
```typescript
// 旧：不同模式映射不同力度
reasoning_effort: mode === "ultra" ? "high" : mode === "pro" ? "medium" : ...

// 新：统一 high
reasoning_effort: "high",
```

### 5. 推理力度选择器显示条件
```typescript
// 旧：mode !== "flash" 时显示
{supportReasoningEffort && context.mode !== "flash" && (

// 新：始终显示（所有模式都开启 thinking）
{supportReasoningEffort && (
```

### 6. getResolvedMode() 简化
```typescript
// 旧：需要判断 supportsThinking
function getResolvedMode(mode, supportsThinking) {
  if (!supportsThinking && mode !== "flash") return "flash";
  ...
}

// 新：所有模型都支持，直接返回
function getResolvedMode(mode: InputMode | undefined): InputMode {
  return mode ?? "autonomous";
}
```

### 7. 模式选择器 UI（`input-box.tsx` 约 499-663 行）
- 替换图标：CompassIcon / TargetIcon / ZapIcon
- 替换文案：使用新的 i18n key
- 去掉 `{supportThinking && (` 条件包裹（所有模式都显示）
- ultra 的金色特殊样式去掉

### 8. i18n 文案（`en-US.ts` / `zh-CN.ts`）
替换模式相关的 key：
- `flashMode` → `autonomousMode`（自主 / Autonomous）
- `reasoningMode` → `preciseMode`（精确 / Precise）
- `proMode` → `expressMode`（极速 / Express）
- 删除 `ultraMode`
- 更新对应的 description key

## 后端改动

### 1. agent.py — 读取 interaction_style
```python
# 新增
interaction_style = cfg.get("interaction_style", "autonomous")

# 硬编码全开（不再依赖前端传入）
thinking_enabled = cfg.get("thinking_enabled", True)  # 保持默认 True
is_plan_mode = True   # 硬编码
subagent_enabled = True  # 硬编码
```

传递给 `apply_prompt_template()` 和 `get_available_tools()`。

### 2. prompt.py — 根据 interaction_style 注入不同澄清策略
`apply_prompt_template()` 新增 `interaction_style` 参数。

根据值选择不同的 `<clarification_system>` 段：
- `precise`：保留当前完整的澄清系统（CLARIFY → PLAN → ACT，5 种必须澄清场景）
- `autonomous`：新写一段，只在高风险/不可逆操作时澄清，其他自主推进
- `express`：不注入 `<clarification_system>` 段，替换为"直接执行"指令

### 3. tools.py — 根据 interaction_style 控制工具
`get_available_tools()` 新增 `interaction_style` 参数：
- `express` 时不包含 `ask_clarification` 工具
- 其他模式保留

### 4. AgentThreadContext 类型（`threads/types.ts`）
新增 `interaction_style` 字段。`thinking_enabled`、`is_plan_mode`、`subagent_enabled` 保留但前端固定传 `true`。

### 5. IM 渠道默认值（`app/channels/manager.py`）
`DEFAULT_RUN_CONTEXT` 同步更新：
```python
# 旧
DEFAULT_RUN_CONTEXT = {
    "thinking_enabled": True,
    "is_plan_mode": False,
    "subagent_enabled": False,
}

# 新
DEFAULT_RUN_CONTEXT = {
    "thinking_enabled": True,
    "is_plan_mode": True,
    "subagent_enabled": True,
    "interaction_style": "autonomous",
}
```

## 持久化
与当前一致：模式选择存在 localStorage 的全局设置中，所有对话共享。

## 验证方案
1. 前端：`pnpm lint && pnpm typecheck`
2. 后端：`cd backend && make lint && make test`
3. 手动测试：
   - 切换三个模式，通过 LangSmith trace 确认 system prompt 差异
   - 极速模式：确认 ask_clarification 不在工具列表，agent 不中断提问
   - 精确模式：确认频繁澄清行为
   - 自主模式：确认只在关键决策点澄清
   - 推理力度选择器在所有模式下可见且可调
