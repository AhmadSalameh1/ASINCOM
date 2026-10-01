INCOM 2027 paper -- files for Overleaf

Contents
  main.tex          the manuscript (uses \documentclass{ifacconf}; the class sets the ifacconf bibliography style)
  references.bib    the bibliography (all entries verified)
  figures/          the four figures used in the paper (vector PDF)

The IFAC class (ifacconf.cls) and bibliography style (ifacconf.bst) are NOT included: they come from the
official IFAC template.

Recommended way (keeps the official class and style):
  1. On Overleaf: New Project > Templates > search "IFAC" > open the IFAC conference template
     ("Template for IFAC meeting papers") > Open as Template.
  2. Upload main.tex, references.bib and the figures/ folder (Upload button; create a folder named
     "figures" first, or upload the folder directly).
  3. Menu > Main document: select main.tex. You may delete the template's own example .tex file.
  4. Compiler: pdfLaTeX. Recompile.

Alternative: New Project > Upload Project > this zip, then upload ifacconf.cls and ifacconf.bst (from the
IFAC template or the IFAC website) into the project root.

After compiling, check
  - the page count (the paper must fit in 6 pages; if it runs over, drop Fig. 1, the framework figure);
  - the author block (authors marked TODO in main.tex) and the reference list formatting;
  - that \usepackage{natbib} does not clash with the class (if Overleaf reports a natbib option clash,
    delete that line from main.tex: the IFAC class already loads natbib).
