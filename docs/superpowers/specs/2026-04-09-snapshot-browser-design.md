# Snapshot Browser — 设计文档

## 概述

在对话右侧面板中新增「Snapshots」Tab，以"翻书"的方式逐轮浏览 agent 的执行过程。每一页对应一轮 AI 消息（thinking + 所有 tool calls），用户可以在面板内通过 Prev/Next 按钮翻页。流式响应时自动打开并跟踪最新轮次，对话结束后可自由回顾。

## 面板布局

右侧面板顶部加 Tab 栏：`Artifacts | Snapshots`

- Artifacts tab：保持现有行为不变
- Snapshots tab：快照浏览器，包含导航栏 + 快照内容区

面板打开/关闭仍由 `ArtifactsContext.open` 控制，Tab 切换由新增的 `panelTab` 状态控制。

```
┌──────────────────────────────────────────────────────────┐
│  Chat (60%)                    │  Panel (40%)             │
│                                │ ┌──────────────────────┐ │
│  [用户消息]                     │ │ Artifacts | Snapshots│ │
│                                │ ├──────────────────────┤ │
│  [AI 回复 + 工具调用卡片]       │ │ ← Prev  2/4  Next → │ │
│                                │ ├──────────────────────┤ │
│                                │ │                      │ │
│                                │ │  快照内容区           │ │
│                                │ │                      │ │
│  ┌─────────────────────┐      │ │                      │ │
│  │ StepTimeline (保持)  │      │ │                      │ │
│  └─────────────────────┘      │ └──────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## 快照粒度

一页快照 = 一个 message group（来自 `groupMessages()`）。

对应关系：
- `assistant:processing` 组 → 标准快照页（thinking + tool calls）
- `assistant:subagent` 组 → 子任务快照页
- `assistant` 组 → 回复快照页
- `human` 组 → 用户输入页（简略展示）
- `assistant:clarification` 组 → 澄清问题页
- `assistant:present-files` 组 → 文件展示页

不新建数据结构，直接复用 `groupMessages()` 的分组结果。

`groupMessages()` 位于 `frontend/src/core/messages/utils.ts`，当前 `MessageGroup` 是内部类型，需要导出。

## 组件接口定义

### SnapshotBrowser

快照浏览器主组件，负责导航和页面容器。

```tsx
// frontend/src/components/workspace/snapshots/snapshot-browser.tsx

interface SnapshotBrowserProps {
  messages: Message[];       // 来自 thread.messages
  isLoading: boolean;        // 来自 thread.isLoading
  className?: string;
}

// 内部状态
// currentRoundIndex: number — 当前查看的轮次索引，初始值 0
// autoFollow: boolean — 是否自动跟踪最新轮次，初始值 true

// 核心逻辑：
// 1. 调用 groupMessages(messages, group => group) 获取所有 message groups
// 2. rounds = groups（所有组都作为快照页，包括 human）
// 3. 渲染导航栏 + SnapshotPage
// 4. isLoading && autoFollow 时，currentRoundIndex 自动跟踪 rounds.length - 1
// 5. 用户点击 Prev/Next 时，设置 autoFollow = false
```

导航栏 UI 结构：
```
┌─────────────────────────────────────┐
│  [← Prev]   Round 2 / 4   [Next →] │
└─────────────────────────────────────┘
```

- Prev 按钮：`currentRoundIndex > 0` 时可点击
- Next 按钮：`currentRoundIndex < rounds.length - 1` 时可点击
- 页码：`Round {currentRoundIndex + 1} / {rounds.length}`
- 使用现有 `Button` 组件（`@/components/ui/button`），`variant="ghost"` + `size="icon-sm"`

### SnapshotPage

单页快照渲染组件，根据 group type 分发到不同的渲染逻辑。

```tsx
// frontend/src/components/workspace/snapshots/snapshot-page.tsx

interface SnapshotPageProps {
  group: MessageGroup;       // 当前轮次的 message group
  allMessages: Message[];    // 完整消息列表，用于 findToolCallResult()
  isLoading: boolean;
}

// 根据 group.type 分发渲染：
// switch (group.type) {
//   case "assistant:processing": return <ProcessingSnapshot ... />
//   case "assistant:subagent":   return <SubagentSnapshot ... />
//   case "assistant":            return <ResponseSnapshot ... />
//   case "human":                return <HumanSnapshot ... />
//   case "assistant:clarification": return <ClarificationSnapshot ... />
//   case "assistant:present-files": return <PresentFilesSnapshot ... />
// }
```

## 快照页面内容详细设计

### 1. 标准快照页 ProcessingSnapshot（assistant:processing）

这是最复杂的快照类型，包含 thinking 和多个 tool calls。

```tsx
// 数据提取逻辑（在组件内部）：
// 遍历 group.messages，对每条 AI 消息：
//   1. extractReasoningContentFromMessage(msg) → reasoning 文本
//   2. msg.tool_calls → 工具调用列表
//   3. 对每个 tool_call，用 findToolCallResult(tool_call.id, allMessages) 获取结果

// 渲染结构：
// ┌─ Thinking（如果有 reasoning）──────────────────┐
// │  左侧黄色竖线 border-l-3 border-amber-400      │
// │  可折叠（Collapsible），默认展开                  │
// │  内容：MarkdownContent 渲染 reasoning 文本       │
// └────────────────────────────────────────────────┘
// ┌─ Tool Call 1 ──────────────────────────────────┐
// │  左侧蓝色竖线 border-l-3 border-blue-500        │
// │  头部：工具名 Badge + 状态标签                    │
// │  INPUT 区：JSON 代码块（CodeBlock language="json"）│
// │  OUTPUT 区：根据工具类型渲染（见下方）             │
// └────────────────────────────────────────────────┘
// ┌─ Tool Call 2 ──────────────────────────────────┐
// │  ...同上                                        │
// └────────────────────────────────────────────────┘
```

工具名 Badge 样式：
- 背景色 `bg-blue-100 dark:bg-blue-900/30`，文字色 `text-blue-700 dark:text-blue-300`
- 图标复用 `message-group.tsx` 中的映射：web_search→SearchIcon, web_fetch→GlobeIcon, read_file→BookOpenTextIcon, write_file→NotebookPenIcon, bash→SquareTerminalIcon, 其他→WrenchIcon

状态标签：
- completed: `bg-emerald-100 text-emerald-700` + CheckIcon
- in_progress: `bg-blue-100 text-blue-700` + Loader2Icon (animate-spin)
- 判断逻辑：`findToolCallResult(toolCallId, allMessages) !== undefined` → completed，否则 in_progress

INPUT 区渲染规则：
- 默认：`<CodeBlock language="json" code={JSON.stringify(args, null, 2)} />`
- `bash` 工具：`<CodeBlock language="bash" code={args.command} />`
- 如果 args 只有一个 `query` 或 `url` 字段，直接显示文本，不用 JSON 代码块

OUTPUT 区渲染规则：
- `web_search`：结果是数组时，渲染为链接列表（复用 `ChainOfThoughtSearchResults` + `ChainOfThoughtSearchResult`）
- `image_search`：渲染缩略图网格
- `web_fetch`：渲染为 MarkdownContent（截断到前 500 字符 + "..."）
- `write_file` / `str_replace`：显示文件路径 + "View in Artifacts →" 按钮（点击调用 `setPanelTab("artifacts")` + `select(artifactUrl)`）
- `bash`：`<CodeBlock language="text" code={result} />`（截断到前 2000 字符）
- `read_file`：`<CodeBlock code={result} />`（截断到前 2000 字符）
- 其他：如果 result 是 JSON 对象，`<CodeBlock language="json" />`；如果是字符串，纯文本显示（截断到前 2000 字符）
- result 为 undefined（工具还在执行中）：显示 `<Loader2Icon className="animate-spin" />` + "执行中..."

### 2. 子任务快照页 SubagentSnapshot（assistant:subagent）

```tsx
// 数据提取：
// 遍历 group.messages 中 type === "ai" 的消息
// 对每个 tool_call.name === "task" 的调用：
//   taskId = tool_call.id
//   description = tool_call.args.description
//   prompt = tool_call.args.prompt
//   通过 useSubtask(taskId) 获取实时状态（status, latestMessage, result, error）
//   通过 findToolCallResult(taskId, allMessages) 获取最终结果文本

// 渲染结构：
// ┌─ Task 1 ───────────────────────────────────────┐
// │  头部：🔄 Subagent Badge + 状态标签              │
// │  TASK: description 文本                          │
// │  PROMPT: prompt 文本（可折叠，默认收起）           │
// │                                                  │
// │  EXECUTION LOG（如果 latestMessage 有 tool_calls）│
// │  ┌──────────────────────────────────────────┐   │
// │  │ ✓ web_search — "query text"              │   │
// │  │ ✓ web_fetch — url                        │   │
// │  │ ⟳ read_file — 正在读取...                │   │
// │  └──────────────────────────────────────────┘   │
// │                                                  │
// │  RESULT（completed 时显示）:                      │
// │  结果文本（MarkdownContent 渲染）                 │
// │                                                  │
// │  ERROR（failed 时显示）:                          │
// │  错误信息（红色文字）                              │
// └─────────────────────────────────────────────────┘
```

EXECUTION LOG 的数据来源：
- `useSubtask(taskId).latestMessage` — 这是子任务最新的 AI 消息
- 如果 `latestMessage` 有 `tool_calls`，显示最后一个 tool call 的名称和简要描述
- 注意：子任务的完整内部步骤在前端不可用（只有 latestMessage），所以 EXECUTION LOG 只能显示最新的一步
- 如果后续后端支持推送完整的子任务步骤历史，可以扩展此区域

状态标签样式：
- in_progress: `bg-amber-100 text-amber-700` + Loader2Icon (animate-spin)
- completed: `bg-emerald-100 text-emerald-700` + CheckCircleIcon
- failed: `bg-red-100 text-red-700` + XCircleIcon

### 3. 回复快照页 ResponseSnapshot（assistant）

```tsx
// 数据提取：
// message = group.messages[0]
// content = extractContentFromMessage(message)
// reasoning = extractReasoningContentFromMessage(message)

// 渲染结构：
// ┌─────────────────────────────────────────────────┐
// │  💬 Response Badge                               │
// │                                                  │
// │  [如果有 reasoning，显示可折叠的 Thinking 区域]    │
// │                                                  │
// │  MarkdownContent 渲染 content                    │
// └─────────────────────────────────────────────────┘
```

复用 `MarkdownContent` 组件（`components/workspace/messages/markdown-content.tsx`）。

### 4. 用户输入页 HumanSnapshot（human）

```tsx
// 数据提取：
// message = group.messages[0]
// text = extractContentFromMessage(message)
// files = message.additional_kwargs?.files（如果有）

// 渲染结构：
// ┌─────────────────────────────────────────────────┐
// │  👤 User Input Badge                             │
// │                                                  │
// │  用户消息文本                                     │
// │                                                  │
// │  [如果有附件文件，显示文件列表]                     │
// └─────────────────────────────────────────────────┘
```

### 5. 澄清问题页 ClarificationSnapshot（assistant:clarification）

```tsx
// message = group.messages[0]
// content = extractContentFromMessage(message)

// 渲染：❓ Clarification Badge + MarkdownContent
```

### 6. 文件展示页 PresentFilesSnapshot（assistant:present-files）

```tsx
// files = extractPresentFilesFromMessage(group.messages[0])

// 渲染：📁 Files Badge + 文件路径列表
```

## 导航交互

面板内独立导航：
- 顶部导航栏：`← Prev | Round N/M | Next →`
- 键盘快捷键：暂不实现。现有 StepTimeline 在 window 级别监听 ArrowLeft/ArrowRight，快照浏览器的键盘导航留作后续优化
- 流式时自动跟随最新 round，用户手动翻页后暂停自动跟随
- 底部 StepTimeline 保持不变，两者独立运作

自动跟随逻辑（在 SnapshotBrowser 内部）：
```tsx
useEffect(() => {
  if (isLoading && autoFollow && rounds.length > 0) {
    setCurrentRoundIndex(rounds.length - 1);
  }
}, [isLoading, autoFollow, rounds.length]);

// 用户点击 Prev/Next 时：
const handlePrev = () => {
  setCurrentRoundIndex(i => Math.max(0, i - 1));
  setAutoFollow(false);
};
const handleNext = () => {
  setCurrentRoundIndex(i => Math.min(rounds.length - 1, i + 1));
  // 如果翻到最后一页，恢复自动跟随
  if (currentRoundIndex + 1 >= rounds.length - 1) {
    setAutoFollow(true);
  } else {
    setAutoFollow(false);
  }
};
```

## 自动打开行为

- `thread.isLoading` 变为 `true` 时 → `setOpen(true)` + `setPanelTab("snapshots")`
- 用户手动关闭面板后，不再自动打开（复用现有 `autoOpen` 逻辑）
- `write_file` 自动打开 artifact 的现有行为保持不变（它会切到 artifacts tab）

实现位置：`ChatBox` 组件中新增 useEffect：
```tsx
const prevIsLoading = useRef(false);
useEffect(() => {
  if (thread.isLoading && !prevIsLoading.current && autoOpen) {
    setArtifactsOpen(true);
    setPanelTab("snapshots");
  }
  prevIsLoading.current = thread.isLoading;
}, [thread.isLoading, autoOpen, setArtifactsOpen, setPanelTab]);
```

`write_file` 自动打开 artifact 时切换 tab（在 `message-group.tsx` 中）：
```tsx
// 现有代码（line 338-349）在 autoOpen 时 select artifact
// 新增：同时切换到 artifacts tab
if (isLoading && isLast && autoOpen && autoSelect && path) {
  setTimeout(() => {
    // ... 现有 select 逻辑 ...
    setPanelTab("artifacts"); // 新增
  }, 100);
}
```

## 状态管理

### ArtifactsContext 扩展

文件：`frontend/src/components/workspace/artifacts/context.tsx`

```tsx
// 新增到 ArtifactsContextType：
export interface ArtifactsContextType {
  // ... 现有字段 ...
  panelTab: "artifacts" | "snapshots";
  setPanelTab: (tab: "artifacts" | "snapshots") => void;
}

// 在 ArtifactsProvider 中：
const [panelTab, setPanelTab] = useState<"artifacts" | "snapshots">("artifacts");

// 加入 value 对象：
const value: ArtifactsContextType = {
  // ... 现有字段 ...
  panelTab,
  setPanelTab,
};
```

### SnapshotBrowser 内部状态

```tsx
const [currentRoundIndex, setCurrentRoundIndex] = useState(0);
const [autoFollow, setAutoFollow] = useState(true);

// rounds 通过 useMemo 计算：
const rounds = useMemo(
  () => groupMessages(messages, (group) => group),
  [messages],
);
```

不修改 `StepContext`，快照浏览器有自己独立的导航状态。

## ChatBox Tab 栏 UI

文件：`frontend/src/components/workspace/chats/chat-box.tsx`

Tab 栏渲染在右侧面板内容区的最顶部：

```tsx
// 在 <ResizablePanel id="artifacts"> 内部，现有内容之前加 Tab 栏：
<div className="flex h-full flex-col">
  {/* Tab 栏 */}
  <div className="flex items-center border-b px-1">
    <button
      className={cn(
        "px-3 py-2 text-sm transition-colors",
        panelTab === "artifacts"
          ? "border-b-2 border-primary font-medium text-foreground"
          : "text-muted-foreground hover:text-foreground",
      )}
      onClick={() => setPanelTab("artifacts")}
    >
      Artifacts
    </button>
    <button
      className={cn(
        "px-3 py-2 text-sm transition-colors",
        panelTab === "snapshots"
          ? "border-b-2 border-primary font-medium text-foreground"
          : "text-muted-foreground hover:text-foreground",
      )}
      onClick={() => setPanelTab("snapshots")}
    >
      Snapshots
    </button>
    <div className="flex-1" />
    <Button size="icon-sm" variant="ghost" onClick={() => setArtifactsOpen(false)}>
      <XIcon />
    </Button>
  </div>

  {/* 内容区 */}
  <div className="min-h-0 flex-1">
    {panelTab === "snapshots" ? (
      <SnapshotBrowser
        messages={thread.messages}
        isLoading={thread.isLoading}
      />
    ) : (
      // 现有 artifacts 内容（selectedArtifact ? ArtifactFileDetail : ArtifactFileList/EmptyState）
    )}
  </div>
</div>
```

## 边界情况处理

1. **没有消息时**：rounds 为空，SnapshotBrowser 显示空状态（"暂无执行记录"）
2. **只有用户消息时**：只有一个 human round，显示用户输入页
3. **流式中断**：最后一个 tool call 没有 result → 显示 in_progress 状态
4. **切换 thread**：`ChatBox` 已有 `threadIdRef` 检测 thread 切换并调用 `deselect()`，SnapshotBrowser 因为 `messages` prop 变化会自动重新计算 rounds 并重置 `currentRoundIndex`
5. **面板关闭再打开**：SnapshotBrowser 的状态保持（因为组件没有卸载，只是 opacity-0 + translate-x-full）
6. **非常长的 tool call 结果**：OUTPUT 区域设置 `max-h-[300px] overflow-auto`，超长内容可滚动查看
7. **tool call args 包含敏感信息**：不做特殊处理，和现有 MessageGroup 行为一致

## MessageGroup 类型导出

文件：`frontend/src/core/messages/utils.ts`

当前 `MessageGroup` 及其子类型（`HumanMessageGroup`、`AssistantProcessingGroup` 等）是文件内部类型。需要在类型定义前加 `export`：

```tsx
export interface HumanMessageGroup extends GenericMessageGroup<"human"> {}
export interface AssistantProcessingGroup extends GenericMessageGroup<"assistant:processing"> {}
export interface AssistantMessageGroup extends GenericMessageGroup<"assistant"> {}
export interface AssistantPresentFilesGroup extends GenericMessageGroup<"assistant:present-files"> {}
export interface AssistantClarificationGroup extends GenericMessageGroup<"assistant:clarification"> {}
export interface AssistantSubagentGroup extends GenericMessageGroup<"assistant:subagent"> {}

export type MessageGroup =
  | HumanMessageGroup
  | AssistantProcessingGroup
  | AssistantMessageGroup
  | AssistantPresentFilesGroup
  | AssistantClarificationGroup
  | AssistantSubagentGroup;
```

同时导出 `GenericMessageGroup`，因为 `SnapshotPage` 需要访问 `group.messages` 和 `group.type`。

## 需要修改的文件清单

### 新建文件（3 个）
| 文件 | 用途 |
|------|------|
| `frontend/src/components/workspace/snapshots/snapshot-browser.tsx` | 快照浏览器主组件（导航 + 页面容器） |
| `frontend/src/components/workspace/snapshots/snapshot-page.tsx` | 单页快照渲染（根据 group type 分发） |
| `frontend/src/components/workspace/snapshots/index.ts` | barrel export |

### 修改文件（3 个）
| 文件 | 改动 |
|------|------|
| `frontend/src/components/workspace/artifacts/context.tsx` | 新增 `panelTab` + `setPanelTab` 状态 |
| `frontend/src/components/workspace/chats/chat-box.tsx` | 加 Tab 栏 UI，条件渲染 artifacts 或 snapshots，自动打开逻辑 |
| `frontend/src/core/messages/utils.ts` | 导出 `MessageGroup` 及子类型 |

### 可能需要小改的文件（1 个）
| 文件 | 改动 |
|------|------|
| `frontend/src/components/workspace/messages/message-group.tsx` | `write_file` 自动打开时调用 `setPanelTab("artifacts")` |

### 复用的现有组件/函数
| 组件/函数 | 来源文件 | 用途 |
|-----------|----------|------|
| `groupMessages()` | `core/messages/utils.ts` | 消息分组 |
| `findToolCallResult()` | `core/messages/utils.ts` | 获取工具调用结果 |
| `extractReasoningContentFromMessage()` | `core/messages/utils.ts` | 获取思考内容 |
| `extractContentFromMessage()` | `core/messages/utils.ts` | 获取消息文本内容 |
| `extractPresentFilesFromMessage()` | `core/messages/utils.ts` | 获取展示文件列表 |
| `ChainOfThoughtStep` | `components/ai-elements/chain-of-thought.tsx` | 步骤渲染原语 |
| `CodeBlock` | `components/ai-elements/code-block.tsx` | 代码块渲染 |
| `MarkdownContent` | `components/workspace/messages/markdown-content.tsx` | Markdown 渲染 |
| `useSubtask()` | `core/tasks/context.tsx` | 子任务实时状态 |
| `useThread()` | `components/workspace/messages/context.tsx` | 获取 thread 消息 |
| `useArtifacts()` | `components/workspace/artifacts/context.tsx` | 面板状态 |
| `Button` | `components/ui/button.tsx` | 按钮组件 |
| `Collapsible` | `components/ui/collapsible.tsx` | 可折叠区域 |

## i18n

需要在 `frontend/src/core/i18n/locales/` 的 en-US 和 zh-CN 中新增翻译 key：

```tsx
snapshots: {
  title: "Snapshots" / "执行快照",
  round: "Round" / "轮次",
  noSnapshots: "No execution records yet" / "暂无执行记录",
  thinking: "Thinking" / "思考",
  input: "Input" / "输入",
  output: "Output" / "输出",
  executing: "Executing..." / "执行中...",
  viewInArtifacts: "View in Artifacts" / "在 Artifacts 中查看",
  task: "Task" / "任务",
  prompt: "Prompt" / "提示词",
  executionLog: "Execution Log" / "执行日志",
  result: "Result" / "结果",
  error: "Error" / "错误",
  userInput: "User Input" / "用户输入",
  response: "Response" / "回复",
  clarification: "Clarification" / "澄清",
  files: "Files" / "文件",
}
```

## 验证方式

1. 启动 `make dev`，打开对话页面
2. 发送一条需要 agent 调用工具的消息（如"搜索 AI agent 框架对比"）
3. 验证：流式开始时右侧面板自动打开并切到 Snapshots tab
4. 验证：每一轮 AI 消息对应一页快照，thinking 和 tool calls 在同一页
5. 验证：Prev/Next 按钮正常翻页，页码计数正确
6. 验证：流式期间自动跟踪最新轮次
7. 验证：手动翻到之前的轮次后，不再自动跟踪；翻到最后一页时恢复自动跟随
8. 验证：切换到 Artifacts tab 后，artifacts 功能正常
9. 验证：`write_file` 工具调用仍然能自动打开 artifact 预览（并切到 Artifacts tab）
10. 验证：对话结束后，可以自由翻阅所有轮次
11. 验证：切换到其他 thread 后，快照浏览器重置
12. 验证：中英文切换后，快照浏览器的文案正确显示
13. 运行 `pnpm lint && pnpm typecheck` 确认无错误
