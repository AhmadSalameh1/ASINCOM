#!/bin/sh
# Local check build with the stand-in class (errors, references, approximate page count).
# Output: paper/build/main_standin.pdf. The submission must be compiled with the official IFAC class.
set -e
cd "$(dirname "$0")/.."
mkdir -p build
sed 's/\\documentclass{ifacconf}/\\documentclass{ifacconf-standin}/' main.tex > build/main_standin.tex
cp tools/ifacconf-standin.cls references.bib build/
rm -rf build/figures && cp -r figures build/figures
cd build
pdflatex -interaction=nonstopmode main_standin.tex > /dev/null || true
bibtex main_standin > bibtex.log || true
pdflatex -interaction=nonstopmode main_standin.tex > /dev/null || true
pdflatex -interaction=nonstopmode main_standin.tex > pdflatex.log || true
grep -E "^!|Warning: (Citation|Reference)|undefined" main_standin.log | sort -u || true
grep -E "^Output written" main_standin.log || true
