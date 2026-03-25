---
name: tdli_style_slides
description: Generate TDLI-style academic presentation slides using LaTeX Beamer with optional speaker notes. Creates a ready-to-edit slide deck with branded cover page, header/footer overlays, 3 content layout templates, thank-you page, and bilingual (English/Chinese) speaker notes support. All content in English.
---

# TDLI Style Slides Generator

Generate a TDLI-branded academic Beamer slide deck for group meetings, seminars, or conference talks.

## What This Skill Does

1. Runs the bundled scaffold script to create a new slide project with all branded assets
2. Optionally customizes the template based on user-provided topic/title
3. Compiles the slides to PDF

## Workflow

### Step 1: Gather Info

Ask the user (if not already provided):
- **Output directory**: Where to create the project (default: current working directory)
- **Project name**: Folder name for the project (default: `tdli-slides`)
- **Presentation title**: The talk title
- **Date**: Presentation date (default: today)

### Step 2: Create Project

Run the scaffold script:

```bash
bash /mnt/skills/public/tdli-style-slides/scripts/create_tdli_slides.sh "<output-dir>" "<project-name>"
```

### Step 3: Customize Template

Open `<project-dir>/presentation.tex` and update the `=== EDIT` sections:

- `\PresentationTitle` — the talk title
- `\PresentationSubtitle` — subtitle or role description
- `\PresentationDate` — date of the talk
- `\CoverLineOne/Two/Three` — cover page summary lines

If the user provided a topic, generate appropriate content for the 3 example content slides using the 3 layout templates (Layout A: left text + right figure, Layout B: full-width blocks, Layout C: two-column blocks).

### Step 3.5: Generate Speaker Notes

For each slide, generate bilingual (English + Chinese) speaker notes and embed them in the corresponding `\note{}` block. Follow this format:

```latex
\note{\scriptsize English speaking notes for this slide. (Xmin)

\medskip\textbf{---中文---}\newline
中文演讲稿。(X分钟)}
```

Guidelines:
- English notes first, then Chinese after the separator
- Include estimated speaking time for each slide
- Notes should be conversational — what you would actually say, not a repeat of bullet points
- Keep each note within `\scriptsize` to fit the notes panel
- IMPORTANT: Use `\newline` (not `\\`) before Chinese text to avoid `\\[中文]` being parsed as `\\[length]` by LaTeX's calc package
- Do NOT wrap note content in `\parbox` — it causes bracket parsing issues with pgfpages

### Step 4: Compile

```bash
cd "<project-dir>" && make
```

This runs `xelatex` twice to ensure correct navigation and cross-references.

## Template Structure

The generated `presentation.tex` contains:

1. **Cover Page** (fixed): 封面.png background + university logo + name + title + date + contact info
2. **Layout A**: Left text column (block + metrics) + Right figure column — best for presenting a single result with visualization
3. **Layout B**: Full-width stacked blocks with optional table — best for methodology or comparison slides
4. **Layout C**: Two equal-width block columns — best for pros/cons, before/after, or parallel topics
5. **Thank You Page** (fixed): 封面.png background + centered thank you text + contact info

Users can duplicate any layout frame as many times as needed.

## Editing Guide

All editable sections are marked with `% === EDIT: ... ===` comments. Key variables at the top of the file:

| Variable | Purpose |
|---|---|
| `\PresenterName` | Your name |
| `\PresentationTitle` | Talk title |
| `\PresentationSubtitle` | Role / research area |
| `\Affiliation` | University / institute |
| `\PresentationDate` | Date |
| `\Email`, `\Phone`, `\GitHub` | Contact info |
| `\CoverLineOne/Two/Three` | Cover summary |

## Resources

All skill resources are in `/mnt/skills/public/tdli-style-slides/`:
- `assets/images/` — branded images (cover, header, footer, logo, photo)
- `assets/templates/` — LaTeX template
- `scripts/` — project generator script

## Speaker Notes

The template includes built-in support for bilingual speaker notes (English + Chinese).

### Enabling Notes

In `presentation.tex`, uncomment these two lines near the top of the file:

```latex
\usepackage{pgfpages}
\setbeameroption{show notes on second screen=right}
```

Then recompile with `xelatex`. The output PDF will be double-width: slides on the left, notes on the right.

### Presenting with Notes

For online meetings or dual-screen setups, use `pdfpc`:

```bash
pdfpc --notes=right --windowed=both presentation.pdf
```

This opens two windows: one for the audience (slides only) and one for the presenter (notes + next slide preview). Share the audience window in your video call.

For single-screen use (e.g., sharing your whole screen), you can also open the double-width PDF directly and crop/zoom as needed.

### Disabling Notes

Comment out the two lines again and recompile. The PDF returns to normal single-page format.

## Important Notes

- Compile with `xelatex` (required for fontawesome5 icons and xeCJK)
- Place custom figures in the `figures/` directory of the generated project
- The cover page and thank-you page layouts are fixed — only edit text content, not structure
- Header and footer overlays appear on ALL slides automatically
- Header/footer use native Beamer templates (not TikZ overlay) for pgfpages compatibility
