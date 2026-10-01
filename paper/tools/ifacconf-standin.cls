% Stand-in for ifacconf.cls, ONLY for local checks (LaTeX errors, references, approximate page count) where the
% official IFAC template is unavailable. It mimics the IFAC conference layout: A4, 10 pt Times, two columns,
% 17.4 cm text width. Submit with the official ifacconf.cls / ifacconf.bst (e.g. the IFAC template on Overleaf).
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ifacconf-standin}[2026/10/01 local stand-in for the IFAC conference class]
\LoadClass[10pt,twocolumn,a4paper]{article}
\RequirePackage[a4paper,textwidth=17.4cm,textheight=24.2cm,top=2.4cm,columnsep=0.6cm]{geometry}
\RequirePackage{mathptmx}
\RequirePackage{natbib}
\bibliographystyle{plainnat}
\setcitestyle{authoryear,round}
\newcommand{\@ifacaddress}{}
\newcommand{\@ifacauthors}{}
\renewcommand{\author}[2][]{\g@addto@macro\@ifacauthors{#2\quad}}
\newcommand{\address}[2][]{\renewcommand{\@ifacaddress}{#2}}
\newenvironment{frontmatter}{}{%
  \twocolumn[{\centering{\Large\bfseries\@title\par}\vspace{6pt}{\@ifacauthors\par}\vspace{2pt}{\small\itshape\@ifacaddress\par}%
  \vspace{8pt}\noindent\begin{minipage}{0.92\textwidth}\small\textbf{Abstract:} \ifacabstract\par\vspace{4pt}
  \textit{Keywords:} \ifackeywords\end{minipage}\vspace{14pt}}]}
\RequirePackage{environ}
\newcommand{\ifacabstract}{}
\newcommand{\ifackeywords}{}
\RenewEnviron{abstract}{\xdef\ifacabstract{\unexpanded\expandafter{\BODY}}}
\NewEnviron{keyword}{\xdef\ifackeywords{\unexpanded\expandafter{\BODY}}}
\newenvironment{ack}{\section*{Acknowledgements}}{}
