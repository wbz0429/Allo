# Example: Creating a Research Talk

This example shows how to create a complete academic presentation using the TDLI Style Slides skill.

## Scenario

You need to prepare a 15-minute talk for a group meeting about your recent work on "Machine Learning for High Energy Physics Event Classification".

## Step 1: Generate the Project

```bash
bash /mnt/skills/public/tdli-style-slides/scripts/create_tdli_slides.sh ~/Desktop ml-hep-talk
```

Output:
```
Created: ~/Desktop/ml-hep-talk

Next steps:
  1) Edit ~/Desktop/ml-hep-talk/presentation.tex
     - Search for '=== EDIT' to find all placeholder sections
  2) Add your figures to ~/Desktop/ml-hep-talk/figures/
  3) Compile: cd ~/Desktop/ml-hep-talk && make
```

## Step 2: Customize Metadata

Open `~/Desktop/ml-hep-talk/presentation.tex` and edit the top section:

```latex
% ============================================================
% === EDIT ZONE: Global Metadata (modify these variables) ===
% ============================================================
\newcommand{\PresenterName}{Your Name}
\newcommand{\PresentationTitle}{Machine Learning for HEP Event Classification}
\newcommand{\PresentationSubtitle}{Your Role or Research Area}
\newcommand{\Affiliation}{Shanghai Jiao Tong University \textperiodcentered{} Tsung-Dao Lee Institute}
\newcommand{\PresentationDate}{March 15, 2026}
\newcommand{\Email}{your@email.com}
\newcommand{\Phone}{your-phone}
\newcommand{\GitHub}{your-github}

% === EDIT: Cover page summary lines ===
\newcommand{\CoverLineOne}{Deep learning models for particle collision event classification}
\newcommand{\CoverLineTwo}{Achieved 95\% accuracy on signal-background separation}
\newcommand{\CoverLineThree}{Deployed on CEPC simulation framework with 10x speedup}
```

## Step 3: Add Your Figures

Copy your figures to the `figures/` directory:

```bash
cp ~/research/plots/roc_curve.png ~/Desktop/ml-hep-talk/figures/
cp ~/research/plots/confusion_matrix.png ~/Desktop/ml-hep-talk/figures/
cp ~/research/plots/architecture.png ~/Desktop/ml-hep-talk/figures/
```

## Step 4: Edit Content Slides

### Slide 1: Motivation (Layout B - Full Width)

```latex
\begin{frame}{Motivation: Why ML for HEP?}

\begin{block}{Challenge in Modern HEP Experiments}
\begin{itemize}
    \item CEPC will produce $10^{12}$ collision events per year
    \item Traditional cut-based methods: low efficiency ($\sim$60\%)
    \item Need intelligent algorithms to identify rare signals
\end{itemize}
\end{block}

\vspace{0.25em}
\begin{block}{Our Approach}
\begin{itemize}
    \item Graph Neural Networks (GNN) for event topology
    \item Attention mechanism for feature importance
    \item End-to-end training on simulated data
\end{itemize}
\end{block}

\end{frame}
```

### Slide 2: Model Architecture (Layout A - Text + Figure)

```latex
\begin{frame}{Model Architecture}
\begin{columns}[T,totalwidth=\textwidth]
\begin{column}{0.48\textwidth}

\begin{block}{Key Components}
\tagitem{GNN} \tagitem{Attention} \tagitem{PyTorch}
\vspace{0.2em}
\begin{itemize}
    \item Input: particle 4-momenta + detector hits
    \item Graph construction: k-NN in $\eta$-$\phi$ space
    \item 3-layer EdgeConv + global pooling
    \item Output: signal probability
\end{itemize}
\end{block}

\vspace{0.2em}
\begin{block}{Training Details}
\begin{itemize}
    \item Dataset: 1M signal + 10M background
    \item Optimizer: AdamW, lr=1e-3
    \item Training time: \metric{2 hours on 8 GPUs}
\end{itemize}
\end{block}

\end{column}

\begin{column}{0.49\textwidth}
\centering
\includegraphics[width=\textwidth]{figures/architecture.png}

\vspace{0.3em}
{\scriptsize GNN architecture with attention mechanism.}
\end{column}
\end{columns}
\end{frame}
```

### Slide 3: Results (Layout A - Text + Figure)

```latex
\begin{frame}{Results: Performance Metrics}
\begin{columns}[T,totalwidth=\textwidth]
\begin{column}{0.48\textwidth}

\begin{block}{Classification Performance}
\tagitem{AUC=0.98} \tagitem{Accuracy=95\%}
\vspace{0.2em}
\begin{itemize}
    \item Signal efficiency: \metric{95\%} at 1\% FPR
    \item \metric{35\% improvement} over baseline
    \item Robust across different energy ranges
\end{itemize}
\end{block}

\vspace{0.2em}
\begin{block}{Computational Efficiency}
\begin{itemize}
    \item Inference time: \metric{0.5 ms/event}
    \item \metric{10x faster} than traditional methods
    \item Deployed on CEPC simulation pipeline
\end{itemize}
\end{block}

\end{column}

\begin{column}{0.49\textwidth}
\centering
\includegraphics[width=\textwidth]{figures/roc_curve.png}

\vspace{0.3em}
{\scriptsize ROC curve comparing GNN vs. baseline methods.}
\end{column}
\end{columns}
\end{frame}
```

### Slide 4: Comparison (Layout C - Two Columns)

```latex
\begin{frame}{Comparison: GNN vs. Traditional Methods}
\begin{columns}[T,totalwidth=\textwidth]

\begin{column}{0.49\textwidth}
\begin{block}{Traditional Cut-Based}
\begin{itemize}
    \item Manual feature engineering
    \item Fixed decision boundaries
    \item Efficiency: 60\%
    \item Interpretable but limited
\end{itemize}
\end{block}
\end{column}

\begin{column}{0.49\textwidth}
\begin{block}{Our GNN Approach}
\begin{itemize}
    \item Automatic feature learning
    \item Adaptive decision boundaries
    \item Efficiency: 95\%
    \item Black-box but powerful
\end{itemize}
\end{block}
\end{column}

\end{columns}
\end{frame}
```

## Step 5: Compile

```bash
cd ~/Desktop/ml-hep-talk
make
```

Output:
```
xelatex presentation.tex && xelatex presentation.tex
...
Output written on presentation.pdf (6 pages).
```

## Step 6: Review and Iterate

Open `presentation.pdf` and review:
- Cover page: Check name, title, summary lines
- Content slides: Verify figures are correctly placed
- Thank you page: Confirm contact info

If you need to add more slides, simply duplicate any layout frame and modify the content.

## Final Structure

```
ml-hep-talk/
├── presentation.tex       # 6 slides total
├── presentation.pdf       # Final output
├── Makefile
├── assets/
│   ├── 封面.png
│   ├── 页眉.png
│   ├── 页脚.png
│   └── 校标-标志中英文横版.png
└── figures/
    ├── architecture.png
    ├── roc_curve.png
    └── confusion_matrix.png
```

## Tips for Academic Talks

1. **Keep it simple**: 1 main message per slide
2. **Use metrics**: Highlight quantitative results with `\metric{}`
3. **Tag keywords**: Use `\tagitem{}` for technical terms
4. **Balance text and figures**: Layout A is great for results slides
5. **Duplicate layouts**: Don't create new layouts, reuse the 3 provided templates
6. **Test compilation early**: Compile after every 2-3 slides to catch errors

## Common Customizations

### Change slide order
Just cut and paste entire `\begin{frame}...\end{frame}` blocks.

### Add more slides
Duplicate any layout frame:
```latex
% Copy this entire block
\begin{frame}{Original Title}
...
\end{frame}

% Paste and modify
\begin{frame}{New Title}
...
\end{frame}
```

### Adjust figure size
```latex
% Make figure larger
\includegraphics[width=1.1\textwidth]{figures/your_figure.png}

% Make figure smaller
\includegraphics[width=0.8\textwidth]{figures/your_figure.png}
```

### Add equations
```latex
\begin{block}{Mathematical Formulation}
The loss function is defined as:
\[
\mathcal{L} = -\sum_{i=1}^{N} y_i \log(\hat{y}_i) + (1-y_i) \log(1-\hat{y}_i)
\]
\end{block}
```

### Add code snippets
```latex
\begin{block}{Implementation}
{\small
\begin{verbatim}
model = GNN(input_dim=4, hidden_dim=128)
optimizer = torch.optim.AdamW(model.parameters())
\end{verbatim}
}
\end{block}
```

## Time Estimate

- Initial setup: 5 minutes
- Content editing: 30-60 minutes (depending on complexity)
- Figure preparation: 15-30 minutes
- Compilation and review: 10 minutes

**Total**: ~1-2 hours for a complete 15-minute talk.
