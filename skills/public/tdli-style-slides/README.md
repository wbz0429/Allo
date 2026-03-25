# TDLI Style Slides Skill

Generate TDLI-branded academic presentation slides using LaTeX Beamer.

## Quick Start

### Using the Skill in Allo

```bash
/skill tdli_style_slides
```

Allo will guide you through:
1. Choosing output directory
2. Setting project name
3. Customizing title and date
4. Generating and compiling the slides

### Manual Usage

```bash
# Generate a new slide project
bash /mnt/skills/public/tdli-style-slides/scripts/create_tdli_slides.sh <output-dir> <project-name>

# Example
bash /mnt/skills/public/tdli-style-slides/scripts/create_tdli_slides.sh ~/Desktop my-talk

# Compile
cd ~/Desktop/my-talk
make
```

## Project Structure

```
my-talk/
├── presentation.tex       # Main LaTeX file (edit this)
├── Makefile              # Run `make` to compile
├── assets/               # Branded images (don't modify)
│   ├── 封面.png
│   ├── 页眉.png
│   ├── 页脚.png
│   ├── 校标-标志中英文横版.png
│   └── me.jpg
└── figures/              # Put your custom figures here
    ├── example_figure.png
    └── README.txt
```

## Editing the Template

All editable sections are marked with `% === EDIT: ... ===` comments.

### Global Metadata (top of file)

```latex
\newcommand{\PresenterName}{Xinchen Li}
\newcommand{\PresentationTitle}{Your Presentation Title Here}
\newcommand{\PresentationSubtitle}{Ph.D. Candidate | High Energy Physics \& HPC}
\newcommand{\Affiliation}{Shanghai Jiao Tong University \textperiodcentered{} Tsung-Dao Lee Institute}
\newcommand{\PresentationDate}{March 12, 2026}
\newcommand{\Email}{starleetdli@gmail.com}
\newcommand{\Phone}{13153522674}
\newcommand{\GitHub}{StarLee2}

% Cover page summary lines
\newcommand{\CoverLineOne}{Your first summary line about research background}
\newcommand{\CoverLineTwo}{Your second summary line about methods or systems}
\newcommand{\CoverLineThree}{Your third summary line about outcomes or impact}
```

### Content Slides

The template includes 3 layout types:

#### Layout A: Left Text + Right Figure
Best for presenting a single result with visualization.

```latex
\begin{frame}{Layout A: Left Text + Right Figure}
\begin{columns}[T,totalwidth=\textwidth]
\begin{column}{0.48\textwidth}
  \begin{block}{Key Points}
    \tagitem{Tag1} \tagitem{Tag2}
    \begin{itemize}
      \item Point 1
      \item Point 2
    \end{itemize}
  \end{block}
\end{column}
\begin{column}{0.49\textwidth}
  \includegraphics[width=\textwidth]{figures/your_figure.png}
\end{column}
\end{columns}
\end{frame}
```

#### Layout B: Full-Width Content
Best for methodology or comparison slides.

```latex
\begin{frame}{Layout B: Full-Width Content}
\begin{block}{Main Argument}
  \begin{itemize}
    \item Background
    \item Problem
    \item Approach
  \end{itemize}
\end{block}

\begin{block}{Evidence}
  % Tables, figures, or additional content
\end{block}
\end{frame}
```

#### Layout C: Two-Column Blocks
Best for pros/cons, before/after, or parallel topics.

```latex
\begin{frame}{Layout C: Two-Column Blocks}
\begin{columns}[T,totalwidth=\textwidth]
\begin{column}{0.49\textwidth}
  \begin{block}{Left Block Title}
    \begin{itemize}
      \item Point 1
      \item Point 2
    \end{itemize}
  \end{block}
\end{column}
\begin{column}{0.49\textwidth}
  \begin{block}{Right Block Title}
    \begin{itemize}
      \item Point 1
      \item Point 2
    \end{itemize}
  \end{block}
\end{column}
\end{columns}
\end{frame}
```

### Adding More Slides

Simply duplicate any layout frame and modify the content:

```latex
% Copy-paste the entire \begin{frame}...\end{frame} block
% Then edit the title and content
```

## Utility Commands

- `\highlight{text}` — Blue bold text for emphasis
- `\metric{value}` — Gold background box for metrics (e.g., `\metric{+50\%}`)
- `\tagitem{tag}` — Light blue tag for keywords (e.g., `\tagitem{Machine Learning}`)

## Compilation

```bash
# Full compilation (recommended, runs xelatex twice)
make

# Quick compilation (single pass)
make quick

# Clean temporary files
make clean
```

**Important**: Always use `xelatex` (not `pdflatex`) because the template uses fontawesome5 icons.

## Fixed Pages

### Cover Page
- Background: 封面.png
- Layout: Photo + University logo + Name + Title + Summary box + Contact info
- **Do not modify the structure**, only edit the text variables at the top of the file

### Thank You Page
- Background: 封面.png
- Layout: Centered "Thank You" + Contact info
- **Do not modify the structure**

## Customization Tips

1. **Replace your photo**: Replace `assets/me.jpg` with your own photo (keep the filename)
2. **Add figures**: Put all figures in `figures/` directory, then reference them as `figures/your_figure.png`
3. **Adjust colors**: Modify the color definitions at the top of the template:
   ```latex
   \definecolor{sjtuBlue}{RGB}{17,74,121}
   \definecolor{accentGold}{RGB}{180,140,50}
   ```
4. **Change font size**: Modify the document class options:
   ```latex
   \documentclass[aspectratio=169,9pt]{beamer}  % Change 9pt to 10pt or 11pt
   ```

## Troubleshooting

### Compilation fails with "Undefined control sequence"
- Make sure you're using `xelatex`, not `pdflatex`
- Check that fontawesome5 is installed: `kpsewhich fontawesome5.sty`

### Images not found
- Ensure all image paths are relative to the project root
- Check that `assets/` and `figures/` directories exist

### Text overflow
- Reduce text width in blocks
- Use shorter sentences
- Split content across multiple slides

## Directory Structure

```
/mnt/skills/public/tdli-style-slides/
├── SKILL.md                          # Skill prompt for Allo
├── README.md                         # This file
├── assets/
│   ├── images/                       # Branded assets
│   │   ├── 封面.png
│   │   ├── 页眉.png
│   │   ├── 页脚.png
│   │   ├── 校标-标志中英文横版.png
│   │   ├── me.jpg
│   │   └── example_figure.png
│   └── templates/
│       └── tdli_slides_template.tex  # LaTeX template
└── scripts/
    └── create_tdli_slides.sh         # Project generator
```

## License

This skill is for personal and academic use. The TDLI branding assets (logo, cover, header, footer) are property of Shanghai Jiao Tong University and Tsung-Dao Lee Institute.
