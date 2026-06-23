---
name: to-tex
stage: 工具/渲染
when: 已组织好的中文内容渲染成可编译教科书 .tex
reads: 已组织好的内容
writes: .tex（预导言/TikZ/编译自检）
description: 通用「已组织好的中文内容 → 教科书式 .tex」的渲染层规范：可直接复制的预导言（ctexbook + XeLaTeX + 一套固定 TikZ 样式）、画图避坑、编译自检，以及通用「教科书味」写作标准。输入来源无关——既可来自笔记编辑层（note_to_textbook.md），也可来自预习编辑层（prereq_to_textbook.md），或任何其它已组织好的 markdown 内容。当用户要把一份已组织好的内容渲染成 .tex 教材/导读、或新增/重绘 TikZ 图时使用。本文件是工具 prompt 模板（非 skill），需要时手动整份贴给 Claude 当上下文——目标是「只读本文件即可拿到全部样式与渲染规范」，无需再去读样例 .tex 文件。
---

# 渲染层：已组织好的内容 → 教科书式 .tex（统一规范）

> **定位**：这是工作流的**通用渲染层**（工具 prompt）。它**只负责把一份已经按教科书逻辑组织好的中文内容渲染成可编译、有教科书味的 .tex**，不关心这内容来自笔记、预习还是别处。
> **输入契约**：调用方（如 `note_to_textbook.md` / `prereq_to_textbook.md`）已经把素材组织成内容；本文件提供预导言、TikZ 样式、画图/编译规范，以及 §6 的通用「教科书味」写作标准。
> 适用现状：作者为自动驾驶预测算法工程师实习生（百度白犀牛 / Apollo），现阶段不写代码，文档目标是「看懂数据、理解算法」。正文用中文，公式/代码规范可编译。
> **用法：把本文件整份作为上下文。下面「§1 预导言」可原样复制到文件头；§2–§6 是必须遵守的写作、绘图、编译规范。**

---

## 0. 硬性要求（逐条对照，不要遗漏）

1. 生成**完整、可直接编译**的 LaTeX 源码（不是片段）。
2. 中文用 `ctex`；A4 纸张 + 合理边距；含 `\tableofcontents`。
3. 风格类似**计算机科学教科书 / 优秀技术教程**：每节**先给整体图景，再逐步展开细节**，逻辑链清楚。
4. 公式完整、规范、可编译。
5. **图一律用 TikZ**（不要把 Mermaid 直接塞进 LaTeX）；TikZ 样式用 §1 里那套（`msg/ibox/obox/aux/flow/gnode/gedge/uedge`）。
6. **每章从新页开始**（`ctexbook` 的 `\chapter` 自带换页；见 §4 关于空白页的处理）。
7. 编译优先 **XeLaTeX，连跑两遍**；之后检查是否生成 PDF，关注 `! 错误`、未定义引用、Overfull 警告（见 §5）。

---

## 1. 预导言（复制即用，已内含全部样式）

> 这段是 `ctexbook` + XeLaTeX 的完整 preamble，已包含配色、三类提示框、固定 TikZ 样式、以及（可选的）proto/C++ 代码高亮。**直接复制到 `\begin{document}` 之前即可，不需要再去读任何样例文件。**

```latex
% !TEX program = xelatex
% openany + oneside：去掉 book 类章节强制跳奇数页产生的空白页
\documentclass[12pt,a4paper,openany,oneside]{ctexbook}

% ---------- 数学 / 页面 / 表格 ----------
\usepackage{amsmath,amssymb,amsfonts,mathtools,bm}
\usepackage{geometry}
\geometry{left=2.5cm,right=2.5cm,top=3cm,bottom=3cm}
\usepackage{graphicx}            % 提供 \resizebox（宽图缩放用）
\usepackage{booktabs,tabularx,array,multirow}
\usepackage{caption,subcaption}
\usepackage{enumitem}
\usepackage{float}               % 图表 [H] 就地放置

% ---------- 颜色 ----------
\usepackage{xcolor}
\definecolor{myblue}{RGB}{0,102,153}
\definecolor{myred}{RGB}{204,0,0}
\definecolor{mygreen}{RGB}{0,128,0}
\definecolor{myorange}{RGB}{230,130,0}
\definecolor{mygray}{RGB}{128,128,128}
\definecolor{mypurple}{RGB}{128,0,128}
\definecolor{lightblue}{RGB}{220,235,250}
\definecolor{lightred}{RGB}{255,230,230}
\definecolor{lightgreen}{RGB}{230,255,230}
\definecolor{accent}{RGB}{0,90,160}

% ---------- TikZ ----------
\usepackage{tikz}
\usetikzlibrary{arrows.meta, positioning, calc, fit, backgrounds,
                shapes.geometric, shapes.misc, decorations.pathreplacing,
                angles, quotes, patterns}

% ===== 固定 TikZ 样式（这就是「day1 风格」，不必再去读 day1 文件）=====
%   msg/obox/ibox/aux  : 流程框（蓝=消息/输出、橙=处理、绿=输入、灰=辅助）
%   flow               : 流程箭头
%   gnode/gedge/uedge  : 图节点 / 有向边 / 无向边（画 GNN、消息传递、关系图）
\tikzset{
  nbox/.style={draw, rounded corners=3pt, align=center, font=\small,
               minimum height=0.85cm, inner sep=4pt},
  msg/.style={nbox, fill=blue!8,   draw=blue!55!black},
  obox/.style={nbox, fill=orange!12, draw=orange!65!black},
  ibox/.style={nbox, fill=green!9,  draw=green!55!black},
  aux/.style={nbox, fill=gray!10,  draw=gray!60},
  flow/.style={-{Stealth[length=2.4mm]}, thick, gray!55!black},
  gnode/.style={draw, circle, minimum size=0.9cm, font=\small,
                fill=blue!8, draw=blue!55!black, inner sep=1pt},
  gedge/.style={-{Stealth[length=2.2mm]}, semithick, gray!55!black},
  uedge/.style={thick, gray!55!black},
}

% ---------- 提示框（tcolorbox）----------
\usepackage{tcolorbox}
\tcbuselibrary{skins, breakable, theorems}
% keybox 关键概念 / notebox 补充说明 / warnbox 注意（带自动编号标题）
\newtcolorbox[auto counter]{keybox}[1][]{colback=lightblue, colframe=myblue,
  fonttitle=\bfseries, title={关键概念~\thetcbcounter}, breakable, enhanced, #1}
\newtcolorbox[auto counter]{notebox}[1][]{colback=lightgreen, colframe=mygreen,
  fonttitle=\bfseries, title={补充说明~\thetcbcounter}, breakable, enhanced, #1}
\newtcolorbox[auto counter]{warnbox}[1][]{colback=lightred, colframe=myred,
  fonttitle=\bfseries, title={注意~\thetcbcounter}, breakable, enhanced, #1}
% tbox：带自定义标题的轻量提示框，\begin{tbox}[teal]{标题} ... \end{tbox}
\newtcolorbox{tbox}[2][accent]{breakable, enhanced, boxrule=0.6pt,
  left=2.5mm, right=2.5mm, top=1mm, bottom=1mm,
  colback=#1!4, colframe=#1!60!black, coltitle=white,
  fonttitle=\bfseries\small, title={#2},
  sharp corners=downhill, rounded corners=northwest}

% ---------- 超链接（放在大多数宏包之后）----------
\usepackage{hyperref}
\hypersetup{colorlinks=true, linkcolor=myblue, citecolor=myblue, urlcolor=myblue}

% ====== 可选：proto / C++ 代码高亮（只有要贴源码时才需要，否则可整段删）======
% \usepackage{listings}
% \definecolor{codebg}{RGB}{248,249,250}
% \definecolor{kwmsg}{RGB}{170,13,145}\definecolor{kwmod}{RGB}{0,90,160}
% \definecolor{kwtyp}{RGB}{0,128,0}\definecolor{kwopt}{RGB}{150,90,0}
% \definecolor{cmtcol}{RGB}{120,120,120}\definecolor{strcol}{RGB}{196,26,22}
% \lstdefinelanguage{protobuf}{morekeywords={syntax,package,import,message,enum,
%   option,service,rpc,reserved,oneof,map}, morekeywords=[2]{repeated,optional,
%   required}, morekeywords=[3]{double,float,int32,int64,uint32,uint64,sint32,
%   sint64,fixed32,fixed64,bool,string,bytes}, morekeywords=[4]{default,deprecated,
%   true,false}, sensitive=true, morecomment=[l]{//}, morecomment=[s]{/*}{*/},
%   morestring=[b]"}
% \lstdefinestyle{proto}{language=protobuf, basicstyle=\ttfamily\small,
%   keywordstyle=\color{kwmsg}\bfseries, keywordstyle=[2]\color{kwmod}\bfseries,
%   keywordstyle=[3]\color{kwtyp}, keywordstyle=[4]\color{kwopt}\itshape,
%   commentstyle=\color{cmtcol}, stringstyle=\color{strcol},
%   numbers=left, numberstyle=\tiny\color{gray}, numbersep=7pt,
%   showstringspaces=false, breaklines=true, columns=fullflexible, keepspaces=true,
%   tabsize=2, frame=single, framerule=0.3pt, rulecolor=\color{gray!45},
%   backgroundcolor=\color{codebg}, xleftmargin=1.6em, xrightmargin=0.4em}
% \renewcommand{\lstlistingname}{代码}
```

文档骨架：

```latex
\title{\textbf{<标题>}\\[8pt]\large <副标题>}
\author{}\date{\today}
\begin{document}
\maketitle
\tableofcontents
% \listoffigures   % 图多时可加，非空白页
\chapter{...}
% ... 正文 ...
\end{document}
```

---

## 2. TikZ 样式速查（什么时候用哪个）

| 样式 | 用途 | 典型场景 |
|---|---|---|
| `ibox` | 输入框（绿） | 历史轨迹、地图等输入 |
| `obox` | 处理框（橙） | 编码、融合、解码等处理阶段 |
| `msg` | 消息/输出框（蓝） | 模型输出、消息体 |
| `aux` | 辅助框（灰） | 兜底、注释性节点、输出清单 |
| `flow` | 流程箭头 | 框与框之间的数据流 |
| `gnode` | 图节点（圆，蓝；高亮目标用 `fill=orange!18,draw=orange!70!black`） | GNN/消息传递/关系图的实体 |
| `gedge` | 有向边 | 消息传递方向、依赖、successor |
| `uedge` | 无向边 | 对称交互、actor–actor 关系 |

**最小示例（流程图）：**
```latex
\begin{figure}[H]\centering
\begin{tikzpicture}[node distance=0.5cm and 0.95cm]
  \node[ibox] (a) {输入};
  \node[obox, right=of a] (b) {处理};
  \node[msg,  right=of b] (c) {输出};
  \draw[flow] (a) -- (b);  \draw[flow] (b) -- (c);
\end{tikzpicture}
\caption{...}\label{fig:demo}
\end{figure}
```

**最小示例（消息传递 / 关系图）：**
```latex
\begin{tikzpicture}
  \node[gnode,fill=orange!18,draw=orange!70!black] (i) at (0,0) {$v_i$};
  \node[gnode] (j) at (-2.4,1) {$a_1$};
  \node[gnode,fill=green!12,draw=green!55!black] (m) at (2.4,1) {$m_1$};
  \draw[gedge] (j) -- node[above,font=\scriptsize]{$\mathbf{e}_{1i}$} (i);
  \draw[gedge] (m) -- (i);
  \draw[uedge] (j) -- node[below,font=\scriptsize]{交互} (m);
\end{tikzpicture}
```

---

## 3. 画图避坑清单（这些是真踩过的坑）

- **横向太宽的流程图**会 Overfull：用 `\resizebox{\textwidth}{!}{\begin{tikzpicture}...\end{tikzpicture}}` 压到版心宽。
- **不要用 `rand`**（非确定性，每次编译图都变、易出丑图）。坐标写死。
- 箭头统一 `>={Stealth[length=2.4mm]}` 或用 `flow/gedge` 样式；曲线转向用 `to[out=,in=]`，注意终点别冲出画布。
- 颜色用预导言里的 `myblue/myred/mygreen/myorange/mypurple/mygray` + 浅色 `lightblue/lightgreen/lightred`，保持全篇一致。

---

## 4. 章节与空白页

- `ctexbook` 的 `\chapter` **自带换页**，每章自然从新页开始——**不要**在 `\chapter` 前手动加 `\newpage`（`book` 类会因此多出一页空白）。
- 若有人要求「每节后换页」而你用的是 **article 类**，才在 `\section` 之间手动 `\newpage`。
- **空白页根因**：`ctexbook` 默认 `openright`，章首强制跳到奇数页 → 插空白页。解决：文档类加 `openany,oneside`（见 §1 已加好）。
- 图表尽量用 `[H]`（需 `float` 宏包）就地放置，减少浮动漂移带来的半空页。

---

## 5. 编译与自检（每次都做）

```powershell
xelatex -interaction=nonstopmode -halt-on-error "<file>.tex"
xelatex -interaction=nonstopmode -halt-on-error "<file>.tex"   # 第二遍：目录与交叉引用
```

自检（看 `<file>.log`，全 0 才算干净）：
- `! ` 开头：致命错误，必须为 0。
- `undefined`：未定义引用/标签，应为 0（跑满两遍后）。
- `Overfull \hbox`：版心溢出；>20pt 的要修（多半是宽图，用 `\resizebox`；或长 `\texttt`/URL）。
- `LaTeX Warning: ... may have changed. Rerun`：再跑一遍即可消除。
- 确认确实生成了 `<file>.pdf`。

**定位某张图在第几页**（CJK 下 `pdftotext` 提取常失败，别靠它）：
- 读 `<file>.aux` 里的 `\newlabel{fig:NAME}{{编号}{页码}...}` ——注意这是**印刷页码**，物理页常差 1（前置页/标题页造成偏移）。
- 要**目检**图渲染对不对：`pdftoppm -png -r 150 -f <物理页> -l <物理页> "<file>.pdf" out`，再看 `out-*.png`。

---

## 6. 「教科书味」写作标准（通用，不许干巴罗列）

> 这是**所有**走本渲染层的内容都要满足的通用写作标准（不分来源）。编辑层（note/prereq 等）只负责"把素材组织成内容"与各自的来源专属取舍；"怎么写得有教科书味"统一看这里。

**四条可执行标准：**
1. **问题驱动，而非定义先行**：每节先抛出「要解决什么/为什么需要它」，制造认知缺口，再引入概念去填补——不要上来甩定义。
2. **有承接与过渡**：节与节、概念与概念之间有逻辑钩子（「上一步得到 X，但 X 还不够，因为……所以需要 Y」）。读起来是一条河，不是一串孤立水洼。
3. **讲「为什么」而不只「是什么」**：点透设计动机、取舍、反直觉处，让读者复习时能**重建推理**，而非死记结论。
4. **误区→澄清式讲解**：把易错点/反直觉处写成「常见误区 → 澄清」，正好命中盲点（放 `warnbox`）。

**配套的组织/排版约定：**
- 每章/节开头先一段「整体图景」：这节要解决什么、在全局的位置，再展开（先整体后细节）。
- 提示框语义统一：关键定义/概念放 `keybox`，补充/直觉放 `notebox`，易错点/反直觉/误区放 `warnbox` 或 `tbox`。
- 多用表格对比、ASCII/TikZ 数据流图让关系一目了然。
- 公式给完整推导链，符号先统一约定再使用；能解析推导的（如朝向=速度方向）就别让读者猜。
- 只写当前真正讲清楚、能编译验证的内容；不堆砌。
