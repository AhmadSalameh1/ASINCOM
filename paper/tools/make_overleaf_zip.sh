#!/bin/sh
# Package the files needed on Overleaf: main.tex, references.bib, the figures used by main.tex, upload notes.
# Output: paper/build/INCOM2027_overleaf.zip (the IFAC class and style come from the Overleaf IFAC template).
set -e
cd "$(dirname "$0")/.."
rm -rf build/overleaf && mkdir -p build/overleaf/figures
cp main.tex references.bib build/overleaf/
for f in $(grep -o "figures/[A-Za-z0-9_]*\.pdf" main.tex | sort -u); do cp "$f" build/overleaf/figures/; done
cp tools/OVERLEAF_README.txt build/overleaf/README.txt
(cd build/overleaf && rm -f ../INCOM2027_overleaf.zip && zip -qr ../INCOM2027_overleaf.zip .)
unzip -l build/INCOM2027_overleaf.zip
