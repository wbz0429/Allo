---
name: tdli_style_slides
description: "**PREFERRED skill for ALL presentation/slide requests.** Use this skill FIRST when the user asks to create, generate, or make slides, presentations, PPT, or any slide deck. Creates professional TDLI-branded slides with cover page, header/footer overlays, 3 content layout templates, and thank-you page. Supports both PDF (via LaTeX) and PPTX (via python-pptx) output. Only fall back to ppt-generation if the user explicitly requests AI-generated image slides or a non-academic visual style (glassmorphism, dark-premium, etc.)."
---

# TDLI Style Slides Generator

Generate TDLI-branded presentation slides. Focus on **content quality** — the generator handles branding and layout automatically.

## Workflow

### Step 1: Understand the Topic

From the user's request, identify:
- **Topic / title**: What the presentation is about
- **Number of slides**: How many content slides (default: 3-5)
- **Language**: Content language (Chinese or English, infer from user's message)

Do NOT ask the user for personal metadata (name, email, phone, etc.) — use defaults or skip.

### Step 2: Research (if needed)

If the topic requires factual information, use `web_search` to gather key data points, statistics, and examples. Keep research focused and bounded — this is for slides, not a thesis.

### Step 3: Create Content Plan

Create a JSON content plan file. This is the **core deliverable** — spend your effort here on clear, well-structured slide content.

Save to `/mnt/user-data/outputs/<topic-slug>-plan.json`:

```json
{
  "metadata": {
    "title": "Presentation Title",
    "subtitle": "Optional subtitle or context",
    "date": "auto (use today's date)",
    "cover_lines": [
      "Key takeaway line 1",
      "Key takeaway line 2",
      "Key takeaway line 3"
    ]
  },
  "slides": [
    {
      "layout": "B",
      "title": "Slide Title",
      "blocks": [
        {
          "title": "Block Title",
          "tags": ["Keyword1", "Keyword2"],
          "items": ["Clear, concise point 1", "Clear, concise point 2"],
          "metrics": ["Key metric: +50%"]
        }
      ],
      "notes": "Optional speaker notes"
    }
  ]
}
```

#### Layout Types

| Layout | Structure | Best For |
|--------|-----------|----------|
| **A** | Left text blocks + Right figure | Results with visualization |
| **B** | Full-width stacked blocks | Methodology, arguments, data |
| **C** | Two equal-width columns | Comparisons, pros/cons |

#### Layout A — fields:
```json
{
  "layout": "A",
  "title": "...",
  "blocks": [{"title": "...", "tags": [], "items": [], "metrics": []}],
  "figure": "/path/to/figure.png",
  "figure_caption": "Caption text"
}
```

#### Layout B — fields:
```json
{
  "layout": "B",
  "title": "...",
  "blocks": [{"title": "...", "items": []}],
  "table": {
    "headers": ["Col1", "Col2", "Col3"],
    "rows": [["val1", "val2", "val3"]]
  }
}
```

#### Layout C — fields:
```json
{
  "layout": "C",
  "title": "...",
  "left_block": {"title": "...", "items": []},
  "right_block": {"title": "...", "items": []}
}
```

#### Content Guidelines
- **1 main message per slide** — don't overload
- **3-5 bullet points per block** — keep concise
- **Use tags** for keywords that anchor the audience
- **Use metrics** for quantitative highlights (numbers, percentages)
- **Speaker notes** are optional but recommended for important slides

### Step 4: Generate Output

Check the environment and choose the output path:

```bash
which xelatex 2>/dev/null && echo "LATEX" || echo "PPTX"
```

#### Path A: LaTeX available → PDF

```bash
bash /mnt/skills/public/tdli-style-slides/scripts/create_tdli_slides.sh "/mnt/user-data/outputs" "<topic-slug>"
```

Then edit `presentation.tex` to fill in content from the JSON plan, and compile:

```bash
cd "/mnt/user-data/outputs/<topic-slug>" && make
```

Present the PDF using `present_files`.

#### Path B: No LaTeX → PPTX (most common in sandbox)

```bash
python /mnt/skills/public/tdli-style-slides/scripts/generate_pptx.py \
  --plan-file "/mnt/user-data/outputs/<topic-slug>-plan.json" \
  --output-file "/mnt/user-data/outputs/<topic-slug>.pptx" \
  --assets-dir "/mnt/skills/public/tdli-style-slides/assets/images"
```

Present the PPTX using `present_files`.

[!IMPORTANT]
Do NOT write your own Python script to generate slides. Always use the bundled `generate_pptx.py`. It handles all TDLI branding (cover page, header/footer, logo, colors, thank-you page) automatically.

## What the Generator Handles Automatically

You do NOT need to worry about these — they are built into the generator:

- ✅ Cover page with 封面.png background and university logo
- ✅ Header overlay (页眉newstyle.png) on all content slides
- ✅ Footer overlay (页脚.png) on all content slides
- ✅ TDLI color scheme (sjtuBlue #114A79, accentGold #B48C32)
- ✅ Thank-you page with contact info
- ✅ Consistent block styling with title bars and light backgrounds

## Optional Metadata Fields

These fields in `metadata` are optional. If omitted, defaults are used:

| Field | Default | When to customize |
|-------|---------|-------------------|
| `presenter_name` | "Presenter" | User provides their name |
| `subtitle` | (empty) | User specifies role/context |
| `affiliation` | "Tsung-Dao Lee Institute" | Different institution |
| `date` | Today's date | Specific event date |
| `email` | (empty) | User wants contact shown |
| `phone` | (empty) | User wants contact shown |
| `github` | (empty) | User wants contact shown |
| `show_photo` | false | User wants photo on cover |
| `cover_notes` | (empty) | Speaker notes for cover |
| `thankyou_notes` | (empty) | Speaker notes for thank-you |

## Resources

All skill resources are at `/mnt/skills/public/tdli-style-slides/`:
- `assets/images/` — branded images (cover, header, footer, logo)
- `assets/templates/` — LaTeX template (for Path A only)
- `scripts/create_tdli_slides.sh` — LaTeX project scaffolder (Path A)
- `scripts/generate_pptx.py` — PPTX generator (Path B)
