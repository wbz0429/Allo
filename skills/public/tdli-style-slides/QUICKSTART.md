# Quick Start Guide

## 1. Generate a New Slide Deck (30 seconds)

```bash
bash /mnt/skills/public/tdli-style-slides/scripts/create_tdli_slides.sh ~/Desktop my-talk
```

## 2. Edit Metadata (2 minutes)

Open `~/Desktop/my-talk/presentation.tex` and search for `=== EDIT`:

```latex
\newcommand{\PresentationTitle}{Your Talk Title}
\newcommand{\PresentationDate}{March 15, 2026}
\newcommand{\CoverLineOne}{First summary line}
\newcommand{\CoverLineTwo}{Second summary line}
\newcommand{\CoverLineThree}{Third summary line}
```

## 3. Add Content (10-30 minutes)

Duplicate one of the 3 layout templates and fill in your content:

**Layout A** (Text + Figure):
```latex
\begin{frame}{Your Slide Title}
\begin{columns}[T,totalwidth=\textwidth]
\begin{column}{0.48\textwidth}
  \begin{block}{Key Points}
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

**Layout B** (Full Width):
```latex
\begin{frame}{Your Slide Title}
\begin{block}{Main Content}
  \begin{itemize}
    \item Point 1
    \item Point 2
  \end{itemize}
\end{block}
\end{frame}
```

**Layout C** (Two Columns):
```latex
\begin{frame}{Your Slide Title}
\begin{columns}[T,totalwidth=\textwidth]
\begin{column}{0.49\textwidth}
  \begin{block}{Left}
    \begin{itemize}
      \item Point 1
    \end{itemize}
  \end{block}
\end{column}
\begin{column}{0.49\textwidth}
  \begin{block}{Right}
    \begin{itemize}
      \item Point 1
    \end{itemize}
  \end{block}
\end{column}
\end{columns}
\end{frame}
```

## 4. Add Figures (5 minutes)

```bash
cp ~/your/figures/*.png ~/Desktop/my-talk/figures/
```

## 5. Compile (1 minute)

```bash
cd ~/Desktop/my-talk
make
```

## 6. Done!

Open `presentation.pdf` and review your slides.

---

## Using with Allo

Simply invoke:
```
/skill tdli_style_slides
```

Allo will guide you through the entire process.

---

## Useful Commands

| Command | Description |
|---------|-------------|
| `\highlight{text}` | Blue bold text |
| `\metric{value}` | Gold box for metrics |
| `\tagitem{tag}` | Blue tag for keywords |

---

## Tips

- Keep 1 main message per slide
- Use Layout A for results (text + figure)
- Use Layout B for methodology
- Use Layout C for comparisons
- Compile frequently to catch errors early
