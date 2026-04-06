import {
  CompassIcon,
  GraduationCapIcon,
  ImageIcon,
  MicroscopeIcon,
  PenLineIcon,
  ShapesIcon,
  SparklesIcon,
  VideoIcon,
} from "lucide-react";

import type { Translations } from "./types";

export const zhCN: Translations = {
  // Locale meta
  locale: {
    localName: "中文",
  },

  // Common
  common: {
    home: "首页",
    settings: "设置",
    delete: "删除",
    rename: "重命名",
    share: "分享",
    openInNewWindow: "在新窗口打开",
    close: "关闭",
    more: "更多",
    search: "搜索",
    download: "下载",
    thinking: "思考",
    artifacts: "文件",
    public: "公共",
    custom: "自定义",
    notAvailableInDemoMode: "在演示模式下不可用",
    loading: "加载中...",
    version: "版本",
    lastUpdated: "最后更新",
    code: "代码",
    preview: "预览",
    cancel: "取消",
    save: "保存",
    install: "安装",
    create: "创建",
    signOut: "退出登录",
  },

  // Welcome
  welcome: {
    greeting: "你好，欢迎回来！",
    description:
      "欢迎使用 Allo，你的 AI 办公助手。通过内置和自定义的 Skills，\nAllo 可以帮你搜索网络、分析数据，还能为你生成幻灯片、\n图片、视频、播客及网页等，几乎可以做任何事情。",

    createYourOwnSkill: "创建你自己的 Agent SKill",
    createYourOwnSkillDescription:
      "创建你的 Agent Skill 来释放 Allo 的潜力。通过自定义技能，Allo\n可以帮你搜索网络、分析数据，还能为你生成幻灯片、\n网页等作品，几乎可以做任何事情。",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "复制到剪贴板",
    copiedToClipboard: "已复制到剪贴板",
    failedToCopyToClipboard: "复制到剪贴板失败",
    linkCopied: "链接已复制到剪贴板",
  },

  // Input Box
  inputBox: {
    placeholder: "今天我能为你做些什么？",
    createSkillPrompt:
      "我们一起用 skill-creator 技能来创建一个技能吧。先问问我希望这个技能能做什么。",
    addAttachments: "添加附件",
    mode: "模式",
    flashMode: "闪速",
    flashModeDescription: "快速且高效的完成任务，但可能不够精准",
    reasoningMode: "思考",
    reasoningModeDescription: "思考后再行动，在时间与准确性之间取得平衡",
    proMode: "Pro",
    proModeDescription: "思考、计划再执行，获得更精准的结果，可能需要更多时间",
    ultraMode: "Ultra",
    ultraModeDescription:
      "继承自 Pro 模式，可调用子代理分工协作，适合复杂多步骤任务，能力最强",
    reasoningEffort: "推理深度",
    reasoningEffortMinimal: "最低",
    reasoningEffortMinimalDescription: "检索 + 直接输出",
    reasoningEffortLow: "低",
    reasoningEffortLowDescription: "简单逻辑校验 + 浅层推演",
    reasoningEffortMedium: "中",
    reasoningEffortMediumDescription: "多层逻辑分析 + 基础验证",
    reasoningEffortHigh: "高",
    reasoningEffortHighDescription: "全维度逻辑推演 + 多路径验证 + 反推校验",
    searchModels: "搜索模型...",
    surpriseMe: "小惊喜",
    surpriseMePrompt: "给我一个小惊喜吧",
    followupLoading: "正在生成可能的后续问题...",
    followupConfirmTitle: "发送建议问题？",
    followupConfirmDescription: "当前输入框已有内容，选择发送方式。",
    followupConfirmAppend: "追加并发送",
    followupConfirmReplace: "替换并发送",
    suggestions: [
      {
        suggestion: "写作",
        prompt: "撰写一篇关于[主题]的博客文章",
        icon: PenLineIcon,
      },
      {
        suggestion: "研究",
        prompt: "深入浅出的研究一下[主题]，并总结发现。",
        icon: MicroscopeIcon,
      },
      {
        suggestion: "收集",
        prompt: "从[来源]收集数据并创建报告。",
        icon: ShapesIcon,
      },
      {
        suggestion: "学习",
        prompt: "学习关于[主题]并创建教程。",
        icon: GraduationCapIcon,
      },
    ],
    suggestionsCreate: [
      {
        suggestion: "网页",
        prompt: "生成一个关于[主题]的网页",
        icon: CompassIcon,
      },
      {
        suggestion: "图片",
        prompt: "生成一个关于[主题]的图片",
        icon: ImageIcon,
      },
      {
        suggestion: "视频",
        prompt: "生成一个关于[主题]的视频",
        icon: VideoIcon,
      },
      {
        type: "separator",
      },
      {
        suggestion: "技能",
        prompt:
          "我们一起用 skill-creator 技能来创建一个技能吧。先问问我希望这个技能能做什么。",
        icon: SparklesIcon,
      },
    ],
  },

  // Sidebar
  sidebar: {
    newChat: "新对话",
    chats: "对话",
    recentChats: "最近的对话",
    demoChats: "演示对话",
    agents: "智能体",
    knowledge: "知识库",
    marketplace: "市场",
    admin: "管理后台",
  },

  // Agents
  agents: {
    title: "智能体",
    description: "创建和管理具有专属 Prompt 与能力的自定义智能体。",
    newAgent: "新建智能体",
    emptyTitle: "还没有自定义智能体",
    emptyDescription: "创建你的第一个自定义智能体，设置专属系统提示词。",
    chat: "对话",
    delete: "删除",
    deleteConfirm: "确定要删除该智能体吗？此操作不可撤销。",
    deleteSuccess: "智能体已删除",
    newChat: "新对话",
    createPageTitle: "设计你的智能体",
    createPageSubtitle: "描述你想要的智能体，我来帮你通过对话创建。",
    nameStepTitle: "给新智能体起个名字",
    nameStepHint:
      "只允许字母、数字和连字符，存储时自动转为小写（例如 code-reviewer）",
    nameStepPlaceholder: "例如 code-reviewer",
    nameStepContinue: "继续",
    nameStepInvalidError: "名称无效，只允许字母、数字和连字符",
    nameStepAlreadyExistsError: "已存在同名智能体",
    nameStepCheckError: "无法验证名称可用性，请稍后重试",
    nameStepBootstrapMessage:
      "新智能体的名称是 {name}，现在开始为它生成 **SOUL**。",
    agentCreated: "智能体已创建！",
    startChatting: "开始对话",
    backToGallery: "返回 Gallery",
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "工作区",
    chats: "对话",
  },

  // Workspace
  workspace: {
    officialWebsite: "访问 Allo 官方网站",
    settingsAndMore: "设置和更多",
    contactUs: "联系我们",
    about: "关于 Allo",
  },

  // Conversation
  conversation: {
    noMessages: "还没有消息",
    startConversation: "开始新的对话以查看消息",
  },

  // Chats
  chats: {
    searchChats: "搜索对话",
  },

  // Page titles (document title)
  pages: {
    appName: "Allo",
    chats: "对话",
    newChat: "新对话",
    untitled: "未命名",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `查看其他 ${count} 个步骤`,
    lessSteps: "隐藏步骤",
    executeCommand: "执行命令",
    presentFiles: "展示文件",
    needYourHelp: "需要你的协助",
    useTool: (toolName: string) => `使用 “${toolName}” 工具`,
    searchFor: (query: string) => `搜索 “${query}”`,
    searchForRelatedInfo: "搜索相关信息",
    searchForRelatedImages: "搜索相关图片",
    searchForRelatedImagesFor: (query: string) => `搜索相关图片 “${query}”`,
    searchOnWebFor: (query: string) => `在网络上搜索 “${query}”`,
    viewWebPage: "查看网页",
    listFolder: "列出文件夹",
    readFile: "读取文件",
    writeFile: "写入文件",
    clickToViewContent: "点击查看文件内容",
    writeTodos: "更新 To-do 列表",
    skillInstallTooltip: "安装技能并使其可在 Allo 中使用",
  },

  uploads: {
    uploading: "上传中...",
    uploadingFiles: "文件上传中，请稍候...",
  },

  subtasks: {
    subtask: "子任务",
    executing: (count: number) =>
      `${count > 1 ? "并行" : ""}执行 ${count} 个子任务`,
    in_progress: "子任务运行中",
    completed: "子任务已完成",
    failed: "子任务失败",
  },

  // Auth
  auth: {
    login: {
      title: "登录",
      description: "输入邮箱和密码以继续",
      email: "邮箱",
      password: "密码",
      emailPlaceholder: "you@example.com",
      submit: "登录",
      submitting: "登录中…",
      failed: "登录失败",
      unexpectedError: "发生意外错误",
      noAccount: "还没有账号？",
      register: "注册",
      devAccount: "本地开发账号",
      fillDevAccount: "填入开发账号",
    },
    register: {
      title: "创建账号",
      description: "输入你的信息以开始使用",
      name: "姓名",
      namePlaceholder: "你的姓名",
      email: "邮箱",
      emailPlaceholder: "you@example.com",
      password: "密码",
      submit: "创建账号",
      submitting: "创建中…",
      failed: "注册失败",
      unexpectedError: "发生意外错误",
      hasAccount: "已有账号？",
      signIn: "登录",
    },
  },

  // Knowledge
  knowledge: {
    title: "知识库",
    newButton: "新建",
    createTitle: "创建知识库",
    createDescription: "知识库用于存储文档，支持检索增强生成（RAG）。",
    name: "名称",
    namePlaceholder: "例如：产品文档",
    description: "描述",
    descriptionPlaceholder: "可选描述",
    creating: "创建中...",
    created: "知识库已创建",
    createFailed: "创建知识库失败",
    empty: "暂无知识库",
    createFirst: "创建第一个",
    searchPlaceholder: "搜索知识库...",
    searching: "搜索中...",
    searchButton: "搜索",
    keywordSearch: "关键字搜索",
    semanticSearch: "语义搜索",
    noResults: "未找到结果",
    noResultsIndexHint: "未找到结果，请确认文档已完成索引。",
    resultCount: (count: number) => `${count} 条结果`,
    matches: "匹配",
    relevance: "相关度",
    chunk: "片段",
    keywordSearchFailed: "关键字搜索失败",
    semanticSearchFailed: "语义搜索失败",
  },

  // Marketplace
  marketplace: {
    title: "市场",
    description: "浏览并安装适用于你组织的 MCP 工具和技能。",
    tools: "工具",
    skills: "技能",
    loadingTools: "加载工具中…",
    loadingSkills: "加载技能中…",
    noTools: "暂无可用工具。",
    noSkills: "暂无可用技能。",
    toolInstalled: "工具安装成功",
    toolUninstalled: "工具已卸载",
    skillInstalled: "技能安装成功",
    skillUninstalled: "技能已卸载",
    installToolFailed: "安装工具失败",
    uninstallToolFailed: "卸载工具失败",
    installSkillFailed: "安装技能失败",
    uninstallSkillFailed: "卸载技能失败",
    loadFailed: "加载市场数据失败",
  },

  // Soul / Personality
  soul: {
    title: "个性",
    description:
      "定义你的 AI 助手的个性、语气和行为风格。此设置会注入到每次对话中。",
    placeholder:
      "例如：你是一个友好且简洁的助手，使用轻松的语气交流...",
    hint: "更改将在下次对话时生效。",
    saving: "保存中...",
  },

  // Admin
  admin: {
    dashboard: "仪表盘",
    dashboardDescription: "查看平台级运行指标与近期使用情况。",
    usage: "用量",
    usageDescription: "全平台使用统计",
    platformAdmin: "平台管理后台",
    backToWorkspace: "返回工作区",
    checkingAccess: "正在检查访问权限...",
    usageLoadFailed: "加载使用数据失败",
    organizationsLoadFailed: "加载组织列表失败",
    organizations: "组织",
    organizationsDescription: "管理平台上的所有组织",
    allOrganizations: "所有组织",
    orgCount: (count: number) => `${count} 个组织`,
    usageRecords: "使用记录",
    inputTokens: "输入 Tokens",
    outputTokens: "输出 Tokens",
    totalTokens: "总 Tokens",
    totalApiCalls: "总 API 调用数",
    tokensToday: "今日 Tokens",
    apiCallsToday: "今日 API 调用数",
    tokenUsageByOrganization: "按组织划分的 Token 用量",
    topOrganizationsByTokenConsumption: "Token 消耗最高的组织",
    inputTokensLabel: "输入 Tokens",
    outputTokensLabel: "输出 Tokens",
    apiCallsLabel: "API 调用数",
    apiCallsByOrganization: "按组织划分的 API 调用",
    totalApiCallVolume: "API 调用总量",
    noUsageData: "暂无使用数据",
    detailedBreakdown: "详细明细",
    usagePerOrganization: "各组织使用情况",
    organization: "组织",
    members: "成员数",
    tokensUsed: "已用 Tokens",
    created: "创建时间",
    noOrganizationsFound: "暂无组织",
  },

  // Streaming status
  streaming: {
    connecting: "正在连接...",
    thinking: "正在思考...",
    executing: "正在执行任务...",
    generating: "正在生成回复...",
  },

  // Settings
  settings: {
    title: "设置",
    description: "根据你的偏好调整 Allo 的界面和行为。",
    sections: {
      appearance: "外观",
      memory: "记忆",
      tools: "工具",
      skills: "技能",
      notification: "通知",
      about: "关于",
    },
    memory: {
      title: "记忆",
      description:
        "Allo 会在后台不断从你的对话中自动学习。这些记忆能帮助 Allo 更好地理解你，并提供更个性化的体验。",
      empty: "暂无可展示的记忆数据。",
      rawJson: "原始 JSON",
      markdown: {
        overview: "概览",
        userContext: "用户上下文",
        work: "工作",
        personal: "个人",
        topOfMind: "近期关注（Top of mind）",
        historyBackground: "历史背景",
        recentMonths: "近几个月",
        earlierContext: "更早上下文",
        longTermBackground: "长期背景",
        updatedAt: "更新于",
        facts: "事实",
        empty: "（空）",
        table: {
          category: "类别",
          confidence: "置信度",
          confidenceLevel: {
            veryHigh: "极高",
            high: "较高",
            normal: "一般",
            unknown: "未知",
          },
          content: "内容",
          source: "来源",
          createdAt: "创建时间",
          view: "查看",
        },
      },
    },
    appearance: {
      themeTitle: "主题",
      themeDescription: "跟随系统或选择固定的界面模式。",
      system: "系统",
      light: "浅色",
      dark: "深色",
      systemDescription: "自动跟随系统主题。",
      lightDescription: "更明亮的配色，适合日间使用。",
      darkDescription: "更暗的配色，减少眩光方便专注。",
      languageTitle: "语言",
      languageDescription: "在不同语言之间切换。",
    },
    tools: {
      title: "工具",
      description: "管理 MCP 工具的配置和启用状态。",
    },
    skills: {
      title: "技能",
      description: "管理 Agent Skill 配置和启用状态。",
      marketplace: "市场",
      uploadSkill: "上传技能",
      uploading: "上传中...",
      createSkill: "新建技能",
      emptyTitle: "还没有技能",
      emptyDescription:
        "将你的 Agent Skill 文件夹放在 Allo 根目录下的 `/skills/custom` 文件夹中。",
      emptyButton: "创建你的第一个技能",
    },
    notification: {
      title: "通知",
      description:
        "Allo 只会在窗口不活跃时发送完成通知，特别适合长时间任务：你可以先去做别的事，完成后会收到提醒。",
      requestPermission: "请求通知权限",
      deniedHint:
        "通知权限已被拒绝。可在浏览器的网站设置中重新开启，以接收完成提醒。",
      testButton: "发送测试通知",
      testTitle: "Allo",
      testBody: "这是一条测试通知。",
      notSupported: "当前浏览器不支持通知功能。",
      disableNotification: "关闭通知",
    },
    acknowledge: {
      emptyTitle: "致谢",
      emptyDescription: "相关的致谢信息会展示在这里。",
    },
  },
};
