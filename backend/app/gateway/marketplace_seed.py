"""Seed data for the MCP tool and skills marketplace.

Provides built-in tools and skills that are inserted into the database
on first startup if the marketplace tables are empty.
"""

import json

# ---------------------------------------------------------------------------
# MCP Tool seed data (5 tools)
# ---------------------------------------------------------------------------

SEED_TOOLS: list[dict] = [
    {
        "id": "tool-tavily-search",
        "name": "Tavily Search",
        "description": "AI-optimized search engine that delivers comprehensive, accurate, and trusted results. Designed specifically for AI agents and RAG pipelines with structured JSON responses.",
        "category": "search",
        "icon": "search",
        "mcp_config_json": json.dumps(
            {
                "command": "npx",
                "args": ["-y", "tavily-mcp@latest"],
                "env": {"TAVILY_API_KEY": ""},
            }
        ),
        "is_public": True,
    },
    {
        "id": "tool-firecrawl",
        "name": "Firecrawl",
        "description": "Web scraping and crawling API that converts any website into clean, LLM-ready markdown. Supports JavaScript rendering, pagination, and structured data extraction.",
        "category": "data",
        "icon": "globe",
        "mcp_config_json": json.dumps(
            {
                "command": "npx",
                "args": ["-y", "firecrawl-mcp@latest"],
                "env": {"FIRECRAWL_API_KEY": ""},
            }
        ),
        "is_public": True,
    },
    {
        "id": "tool-jina-ai",
        "name": "Jina AI Reader",
        "description": "Extract clean, readable content from any URL using Jina AI's Reader API. Returns markdown-formatted text optimized for LLM consumption with support for PDFs and dynamic pages.",
        "category": "data",
        "icon": "file-text",
        "mcp_config_json": json.dumps(
            {
                "command": "npx",
                "args": ["-y", "jina-mcp@latest"],
                "env": {"JINA_API_KEY": ""},
            }
        ),
        "is_public": True,
    },
    {
        "id": "tool-duckduckgo",
        "name": "DuckDuckGo Search",
        "description": "Privacy-focused web search powered by DuckDuckGo. No API key required. Returns organic search results with titles, snippets, and URLs.",
        "category": "search",
        "icon": "search",
        "mcp_config_json": json.dumps(
            {
                "command": "npx",
                "args": ["-y", "duckduckgo-mcp@latest"],
                "env": {},
            }
        ),
        "is_public": True,
    },
    {
        "id": "tool-code-sandbox",
        "name": "Code Sandbox",
        "description": "Secure, isolated code execution environment for running Python, JavaScript, and shell scripts. Supports file I/O, package installation, and long-running processes with configurable timeouts.",
        "category": "code",
        "icon": "terminal",
        "mcp_config_json": json.dumps(
            {
                "command": "npx",
                "args": ["-y", "code-sandbox-mcp@latest"],
                "env": {"SANDBOX_TIMEOUT": "30"},
            }
        ),
        "is_public": True,
    },
]

# ---------------------------------------------------------------------------
# Skill seed data (3 skills)
# ---------------------------------------------------------------------------

SEED_SKILLS: list[dict] = [
    {
        "id": "skill-deep-research",
        "name": "Deep Research",
        "description": "Conducts multi-step research by breaking complex questions into sub-queries, searching multiple sources, and synthesizing findings into a comprehensive report with citations.",
        "category": "research",
        "skill_content": "# Deep Research Skill\n\nYou are a research assistant that performs deep, multi-step research.\n\n## Process\n1. Break the user's question into 3-5 sub-queries\n2. Search each sub-query using available tools\n3. Cross-reference findings across sources\n4. Synthesize a comprehensive answer with citations\n\n## Output Format\n- Executive summary (2-3 sentences)\n- Detailed findings with source links\n- Confidence assessment\n",
        "is_public": True,
    },
    {
        "id": "skill-code-review",
        "name": "Code Review",
        "description": "Performs thorough code review with focus on security vulnerabilities, performance bottlenecks, code style consistency, and best practices. Provides actionable suggestions with code examples.",
        "category": "coding",
        "skill_content": "# Code Review Skill\n\nYou are a senior code reviewer.\n\n## Review Checklist\n1. Security: injection, auth, data exposure\n2. Performance: N+1 queries, unnecessary allocations, caching\n3. Correctness: edge cases, error handling, race conditions\n4. Style: naming, structure, documentation\n\n## Output Format\n- Severity: critical / warning / suggestion\n- File and line reference\n- Problem description\n- Suggested fix with code snippet\n",
        "is_public": True,
    },
    {
        "id": "skill-data-analysis",
        "name": "Data Analysis",
        "description": "Analyzes datasets by generating Python code for statistical analysis, visualization, and insight extraction. Supports CSV, JSON, and SQL data sources with pandas and matplotlib.",
        "category": "data",
        "skill_content": "# Data Analysis Skill\n\nYou are a data analyst that writes Python code to analyze data.\n\n## Capabilities\n- Load data from CSV, JSON, or SQL\n- Statistical summaries and distributions\n- Correlation analysis\n- Time series analysis\n- Generate matplotlib/seaborn visualizations\n\n## Process\n1. Understand the data schema\n2. Ask clarifying questions if needed\n3. Write analysis code in a sandbox\n4. Present findings with charts\n",
        "is_public": True,
    },
]
