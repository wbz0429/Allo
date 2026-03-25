#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  create_tdli_slides.sh <output-dir> [project-name]

Example:
  create_tdli_slides.sh ~/Desktop my-tdli-talk

This creates <output-dir>/<project-name>/ with:
  - presentation.tex  (ready-to-edit Beamer template)
  - assets/           (branded images: cover, header, footer, logo, photo)
  - figures/          (place your own figures here)
  - Makefile          (run `make` to compile)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

OUTPUT_DIR="$1"
PROJECT_NAME="${2:-tdli-slides}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ASSETS_DIR="${SKILL_DIR}/assets"
IMAGES_DIR="${ASSETS_DIR}/images"
TEMPLATE_FILE="${ASSETS_DIR}/templates/tdli_slides_template.tex"

# Validate required files
if [[ ! -f "${TEMPLATE_FILE}" ]]; then
  echo "Error: Missing template: ${TEMPLATE_FILE}" >&2
  exit 1
fi

for f in "封面.png" "页眉.png" "页眉newstyle.png" "页脚.png" "校标-标志中英文横版.png" "me.jpg"; do
  if [[ ! -f "${IMAGES_DIR}/${f}" ]]; then
    echo "Error: Missing image: ${IMAGES_DIR}/${f}" >&2
    exit 1
  fi
done

PROJECT_DIR="${OUTPUT_DIR%/}/${PROJECT_NAME}"
if [[ -e "${PROJECT_DIR}" ]]; then
  echo "Error: Target already exists: ${PROJECT_DIR}" >&2
  exit 1
fi

# Create project structure
mkdir -p "${PROJECT_DIR}/assets"
mkdir -p "${PROJECT_DIR}/figures"

# Copy template
cp "${TEMPLATE_FILE}" "${PROJECT_DIR}/presentation.tex"

# Copy branded assets
cp "${IMAGES_DIR}/封面.png"              "${PROJECT_DIR}/assets/"
cp "${IMAGES_DIR}/页眉.png"              "${PROJECT_DIR}/assets/"
cp "${IMAGES_DIR}/页眉newstyle.png"      "${PROJECT_DIR}/assets/"
cp "${IMAGES_DIR}/页脚.png"              "${PROJECT_DIR}/assets/"
cp "${IMAGES_DIR}/校标-标志中英文横版.png" "${PROJECT_DIR}/assets/"
cp "${IMAGES_DIR}/me.jpg"               "${PROJECT_DIR}/assets/"

# Create placeholder figure
cat > "${PROJECT_DIR}/figures/README.txt" <<'EOF'
Place your custom figures in this directory.
Then update figure paths in presentation.tex accordingly.
EOF

# Create Makefile
cat > "${PROJECT_DIR}/Makefile" <<'MAKEFILE'
TEX = presentation.tex

all:
	xelatex $(TEX) && xelatex $(TEX)

quick:
	xelatex $(TEX)

clean:
	rm -f *.aux *.log *.nav *.out *.snm *.toc *.vrb

.PHONY: all quick clean
MAKEFILE

echo "Created: ${PROJECT_DIR}"
echo ""
echo "Next steps:"
echo "  1) Edit ${PROJECT_DIR}/presentation.tex"
echo "     - Search for '=== EDIT' to find all placeholder sections"
echo "  2) Add your figures to ${PROJECT_DIR}/figures/"
echo "  3) Compile: cd ${PROJECT_DIR} && make"
