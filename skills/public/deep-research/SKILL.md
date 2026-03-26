---
name: deep-research
description: Use this skill instead of WebSearch for ANY question requiring web research. Trigger on queries like "what is X", "explain X", "compare X and Y", "research X", or before content generation tasks. Provides systematic multi-angle research methodology instead of single superficial searches. Use this proactively when the user's question needs online information.
---

# Deep Research Skill

## Overview

This skill provides a systematic methodology for conducting thorough web research. **Load this skill BEFORE starting any content generation task** to ensure you gather sufficient information from multiple angles, depths, and sources.

## When to Use This Skill

**Always load this skill when:**

### Research Questions
- User asks "what is X", "explain X", "research X", "investigate X"
- User wants to understand a concept, technology, or topic in depth
- The question requires current, comprehensive information from multiple sources
- A single web search would be insufficient to answer properly

### Content Generation (Pre-research)
- Creating presentations (PPT/slides)
- Creating frontend designs or UI mockups
- Writing articles, reports, or documentation
- Producing videos or multimedia content
- Any content that requires real-world information, examples, or current data

## Core Principle

**Never generate content based solely on general knowledge.** The quality of your output directly depends on the quality and quantity of research conducted beforehand. A single search query is NEVER enough.

## ⛔ MANDATORY: Research Depth Negotiation

**Before starting ANY research, you MUST ask the user to choose a research depth level.** Do NOT skip this step. Do NOT assume a level.

Use `ask_clarification` to present the following options:

```
question: "请选择调研深度（Research Depth）："
clarification_type: "approach_choice"
context: "不同深度对应不同的搜索轮数和每轮搜索次数，直接影响调研质量和耗时。"
options:
  - "⚡ 快速 (Quick) — 1轮, 每轮3-5次搜索, 预计1-2分钟"
  - "📊 标准 (Standard) — 2轮, 每轮5-8次搜索, 预计3-5分钟"
  - "🔬 深度 (Deep) — 3轮, 每轮8-12次搜索, 预计8-15分钟"
```

**If the user explicitly specifies depth in their original request** (e.g., "简单查一下", "深度调研", "详细分析"), you may infer the level without asking — but MUST announce the chosen level and its budget before starting.

### Research Depth Levels

| Level | Rounds | Searches/Round | web_fetch Total | Est. Time | Description |
|-------|--------|---------------|-----------------|-----------|-------------|
| ⚡ Quick | 1 | 3-5 | 2 | 1-2 min | Fast overview, key facts only. Broad Exploration only. |
| 📊 Standard | 2 | 5-8 | 5 | 3-5 min | Solid coverage with targeted deep dives. Broad + Deep Dive. |
| 🔬 Deep | 3 | 8-12 | 8 | 8-15 min | Comprehensive multi-angle analysis. All 4 phases. |

### Budget Definitions (HARD LIMITS per level)

**⚡ Quick:**
- Max `web_search`: **5**
- Max `web_fetch`: **2**
- Max rounds: **1** (Broad Exploration only, skip Phase 2-3)
- Synthesis: Summarize from search snippets, minimal full-text reading

**📊 Standard:**
- Max `web_search`: **12**
- Max `web_fetch`: **5**
- Max rounds: **2** (Phase 1 + Phase 2, light Phase 3)
- Synthesis: Cover 3-4 angles, fetch top 3-5 authoritative sources

**🔬 Deep:**
- Max `web_search`: **20**
- Max `web_fetch`: **8**
- Max rounds: **3** (All 4 phases)
- Synthesis: Full multi-angle coverage with validation

### ⛔ HARD STOP RULES (apply to ALL levels)

1. **When you reach the max search count for your level, STOP.** Do NOT do "one more search."
2. **When you reach the max fetch count, use search snippets for remaining gaps.**
3. **When you finish the max rounds for your level, proceed to content generation immediately.**
4. **Track your usage.** Before each search/fetch, mentally count: "This is search N of M." If N >= M, stop.
5. **"Good enough" research delivered on time is ALWAYS better than "perfect" research that never finishes.**

## Research Methodology

### Phase 1: Broad Exploration (ALL levels)

Start with broad searches to understand the landscape:

1. **Initial Survey**: Search for the main topic to understand the overall context
2. **Identify Dimensions**: From initial results, identify key subtopics, themes, angles, or aspects that need deeper exploration
3. **Map the Territory**: Note different perspectives, stakeholders, or viewpoints that exist

Example:
```
Topic: "AI in healthcare"
Initial searches:
- "AI healthcare applications 2024"
- "artificial intelligence medical diagnosis"
- "healthcare AI market trends"

Identified dimensions:
- Diagnostic AI (radiology, pathology)
- Treatment recommendation systems
- Administrative automation
- Patient monitoring
- Regulatory landscape
- Ethical considerations
```

**⚡ Quick level: STOP HERE.** Summarize findings and proceed to content generation.

### Phase 2: Deep Dive (Standard + Deep only)

For each important dimension identified, conduct targeted research:

1. **Specific Queries**: Search with precise keywords for each subtopic
2. **Multiple Phrasings**: Try different keyword combinations and phrasings
3. **Fetch Full Content**: Use `web_fetch` to read important sources in full, not just snippets
4. **Follow References**: When sources mention other important resources, search for those too

Example:
```
Dimension: "Diagnostic AI in radiology"
Targeted searches:
- "AI radiology FDA approved systems"
- "chest X-ray AI detection accuracy"
- "radiology AI clinical trials results"

Then fetch and read:
- Key research papers or summaries
- Industry reports
- Real-world case studies
```

**📊 Standard level: Do a light pass of Phase 3 (pick 2-3 most relevant information types), then STOP and proceed to synthesis.**

### Phase 3: Diversity & Validation (Deep only — full pass)

Ensure comprehensive coverage by seeking diverse information types:

| Information Type | Purpose | Example Searches |
|-----------------|---------|------------------|
| **Facts & Data** | Concrete evidence | "statistics", "data", "numbers", "market size" |
| **Examples & Cases** | Real-world applications | "case study", "example", "implementation" |
| **Expert Opinions** | Authority perspectives | "expert analysis", "interview", "commentary" |
| **Trends & Predictions** | Future direction | "trends 2024", "forecast", "future of" |
| **Comparisons** | Context and alternatives | "vs", "comparison", "alternatives" |
| **Challenges & Criticisms** | Balanced view | "challenges", "limitations", "criticism" |

**🔬 Deep level: Cover at least 4 of the 6 information types above, then proceed to synthesis.**

### Phase 4: Synthesis Check (ALL levels — adapted)

Before proceeding to content generation, verify based on your level:

**⚡ Quick:**
- [ ] Do I have a basic understanding of the topic?
- [ ] Do I have at least 2-3 key facts or data points?
→ If yes, proceed. If no, you may do 1-2 more searches (within budget).

**📊 Standard:**
- [ ] Have I searched from at least 3-4 different angles?
- [ ] Have I read 2-3 important sources in full?
- [ ] Do I have concrete data and examples?
→ If yes, proceed. If no but budget remains, do one more targeted round.

**🔬 Deep:**
- [ ] Have I searched from at least 5+ different angles?
- [ ] Have I fetched and read the most important sources in full?
- [ ] Do I have concrete data, examples, and expert perspectives?
- [ ] Have I explored both positive aspects and challenges/limitations?
- [ ] Is my information current and from authoritative sources?
→ If most answers are yes (4/5+), proceed. Do NOT chase 100% completion.

**CRITICAL: At this phase, if you have exhausted your budget, you MUST proceed to content generation regardless of checklist status. Use what you have.**

## Search Strategy Tips

### Effective Query Patterns

```
# Be specific with context
❌ "AI trends"
✅ "enterprise AI adoption trends 2024"

# Include authoritative source hints
"[topic] research paper"
"[topic] McKinsey report"
"[topic] industry analysis"

# Search for specific content types
"[topic] case study"
"[topic] statistics"
"[topic] expert interview"

# Use temporal qualifiers — always use the ACTUAL current year from <current_date>
"[topic] 2026"   # ← replace with real current year, never hardcode a past year
"[topic] latest"
"[topic] recent developments"
```

### Temporal Awareness

**Always check `<current_date>` in your context before forming ANY search query.**

`<current_date>` gives you the full date: year, month, day, and weekday (e.g. `2026-02-28, Saturday`). Use the right level of precision depending on what the user is asking:

| User intent | Temporal precision needed | Example query |
|---|---|---|
| "today / this morning / just released" | **Month + Day** | `"tech news February 28 2026"` |
| "this week" | **Week range** | `"technology releases week of Feb 24 2026"` |
| "recently / latest / new" | **Month** | `"AI breakthroughs February 2026"` |
| "this year / trends" | **Year** | `"software trends 2026"` |

**Rules:**
- When the user asks about "today" or "just released", use **month + day + year** in your search queries to get same-day results
- Never drop to year-only when day-level precision is needed — `"tech news 2026"` will NOT surface today's news
- Try multiple phrasings: numeric form (`2026-02-28`), written form (`February 28 2026`), and relative terms (`today`, `this week`) across different queries

❌ User asks "what's new in tech today" → searching `"new technology 2026"` → misses today's news
✅ User asks "what's new in tech today" → searching `"new technology February 28 2026"` + `"tech news today Feb 28"` → gets today's results

### When to Use web_fetch

Use `web_fetch` to read full content when:
- A search result looks highly relevant and authoritative
- You need detailed information beyond the snippet
- The source contains data, case studies, or expert analysis
- You want to understand the full context of a finding

**Remember: web_fetch is expensive. Always check your remaining fetch budget before using it.**

### Iterative Refinement

Research is iterative, but **bounded by your chosen level's round limit**. Within each round:
1. Review what you've learned
2. Identify the most critical gaps (not ALL gaps)
3. Formulate new, more targeted queries
4. Execute within remaining budget

**Do NOT start a new round if you have exhausted your search/fetch budget.**

## Quality Bar

Your research is sufficient when you can confidently answer (scaled by level):

**All levels:**
- What are the key facts and data points?
- What makes this topic relevant or important now?

**Standard + Deep:**
- What are 2-3 concrete real-world examples?
- What do experts say about this topic?

**Deep only:**
- What are the current trends and future directions?
- What are the challenges or limitations?

## Common Mistakes to Avoid

- ❌ Stopping after 1-2 searches (for Standard/Deep levels)
- ❌ Relying on search snippets without reading full sources (for Standard/Deep)
- ❌ Searching only one aspect of a multi-faceted topic
- ❌ Ignoring contradicting viewpoints or challenges
- ❌ Using outdated information when current data exists
- ❌ Starting content generation before research is complete
- ❌ **Exceeding your budget — this is the #1 mistake. Respect the limits.**
- ❌ **Not asking the user for depth level — always negotiate first**
- ❌ **Doing "just one more search" after hitting the limit — STOP means STOP**

## Output

After completing research (within your budget), you should have:
1. A solid understanding of the topic (depth varies by level)
2. Key facts, data points, and statistics
3. Real-world examples (for Standard/Deep)
4. Expert perspectives and authoritative sources (for Deep)
5. Current trends and relevant context (for Deep)

**Proceed to content generation immediately**, using the gathered information to create high-quality, well-informed content.
