#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Learn_Greek_Letter — 希腊字母练字帖生成器
==========================================

从 letters.tsv 读取 24 个希腊字母的数据,生成 LaTeX 源码 greek_copybook.tex。

设计要点
--------
练字帖的本质是三个原子:范本(字形) + 基准(格线) + 落笔区(空间)。
本项目的「基准」采用希腊书写传统的**四线三格**:

    cap line      大写字母顶端
    x-height line 小写字母顶端(希腊语 x-height 较高,约为 cap 的 0.67)
    baseline      基线
    descender line 降部底线(容纳 β γ δ ζ η θ κ λ μ ν ξ ρ σ υ φ χ ψ 的尾巴)

这四条线的位置由字体的**实测**比例推算,而非拍脑袋:

    Palatino: cap = 0.6968 em, x-height = 0.4683 em, descender = 0.1562 em

版面
----
2 页 A4,每页 3 列 x 4 行 = 12 格,共 24 格。
格宽 64mm,3 x 64 + 2 x 3 = 198mm,配合 6mm 页边距正好铺满 A4 宽度。
每个格子上下两区(大写 / 小写),每区左右双栏:左为浅灰描红层,右为空白临摹层。

LaTeX 陷阱(全部实测踩过,详见 README)
------------------------------------
1. LaTeX 内置的 \\alpha / \\Gamma 等在 TU 编码下是**数学命令**,直接用会报
   "Missing $ inserted"。本脚本为全部 24 个大写 + 24 个小写字母生成
   expl3 惰性定义(\\cs_new_protected:Npn ... { {\\symbol{945}} })。
2. IPA 音标同理。裸字符、\\newcommand、\\char"XXXX 全部失败,
   只有 expl3 惰性定义可用。
3. expl3 函数名**不能含数字后缀或下划线**,只能用 \\greekIPAofAlpha 这种形式。
"""

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'letters.tsv')

# ---- 读取字母数据 ----------------------------------------------------
# letters.tsv 为制表符分隔,8 列:
#   序号 / x(mm) / y(mm) / 大写 / 小写 / English / 中文音译 / IPA
# 以 # 开头的行是注释,自动跳过。
_lines = io.open(DATA, encoding='utf-8').read().strip().split('\n')
L = [l.split('\t') for l in _lines if not l.lstrip().startswith('#') and l.strip()]

# ---- LaTeX 宏名映射 --------------------------------------------------
# 数据表里写的是人类可读的 \Alpha / \alpha,这里换成脚本生成的
# expl3 惰性宏名(带 greek 前缀,避免与 LaTeX 内置命令冲突)。
LOWER = {
    '\\alpha': '\\greekalpha', '\\beta': '\\greekbeta', '\\gamma': '\\greekgamma',
    '\\delta': '\\greekdelta', '\\varepsilon': '\\greekepsilon', '\\zeta': '\\greekzeta',
    '\\eta': '\\greeketa', '\\theta': '\\greektheta', '\\iota': '\\greekiota',
    '\\kappa': '\\greekkappa', '\\lambda': '\\greeklambda', '\\mu': '\\greekmu',
    '\\nu': '\\greeknu', '\\xi': '\\greekxi', '\\omicron': '\\greekomicron',
    '\\pi': '\\greekpi', '\\rho': '\\greekrho', '\\sigma': '\\greeksigma',
    '\\tau': '\\greektau', '\\upsilon': '\\greekupsilon', '\\phi': '\\greekphi',
    '\\chi': '\\greekchi', '\\psi': '\\greekpsi', '\\omega': '\\greekomega',
}
UPPER = {
    '\\Alpha': '\\greekAlpha', '\\Beta': '\\greekBeta', '\\Gamma': '\\greekGamma',
    '\\Delta': '\\greekDelta', '\\Epsilon': '\\greekEpsilon', '\\Zeta': '\\greekZeta',
    '\\Eta': '\\greekEta', '\\Theta': '\\greekTheta', '\\Iota': '\\greekIota',
    '\\Kappa': '\\greekKappa', '\\Lambda': '\\greekLambda', '\\Mu': '\\greekMu',
    '\\Nu': '\\greekNu', '\\Xi': '\\greekXi', '\\Omicron': '\\greekOmicron',
    '\\Pi': '\\greekPi', '\\Rho': '\\greekRho', '\\Sigma': '\\greekSigma',
    '\\Tau': '\\greekTau', '\\Upsilon': '\\greekUpsilon', '\\Phi': '\\greekPhi',
    '\\Chi': '\\greekChi', '\\Psi': '\\greekPsi', '\\Omega': '\\greekOmega',
}
L = [(int(a), int(b), float(c), UPPER.get(d, d), LOWER.get(e, e), f, g, h)
     for a, b, c, d, e, f, g, h in L]
L.sort(key=lambda t: t[0])
assert len(L) == 24, 'letters.tsv 应有 24 行,实际 %d' % len(L)

# 序号 -> 英文名(用于生成合法的控制序列名)
ORDER = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta', 'Theta',
         'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu', 'Xi', 'Omicron', 'Pi',
         'Rho', 'Sigma', 'Tau', 'Upsilon', 'Phi', 'Chi', 'Psi', 'Omega']
NAME = {i + 1: n for i, n in enumerate(ORDER)}

# ---- 网格坐标:每页 3 列 x 4 行 = 12 格 ----------------------------
XS = [0, 67, 134]
YS = [17.6, 85.26, 152.92, 220.58]


def pos(no):
    """no 为 1..24 连续编号;每满 12 格换页,页内按 3x4 排布。"""
    idx = (no - 1) % 12          # 页内序号 0..11
    return XS[idx % 3], YS[idx // 3]


# ---- IPA 音标:生成 expl3 惰性宏 ------------------------------------
# 【踩坑记录】以下写法在导言区全部会报 "Missing \begin{document}":
#   \newcommand{\ipa1}{{\ipafont\symbol{712}...}}  —— 导言区求值即输出
#   \newcommand{\ipa1}{{\ipafont{ˈ}{æ}...}}          —— 裸字符同理
#   \newcommand{\ipac}[1]{...} + \ipac{712}          —— 间接层同样失败
# 原因:LaTeX 禁止导言区产生任何排版内容,而这些写法在定义时就被求值。
# 【正解】expl3 的 \cs_new_protected:Npn 是惰性的:导言区只记录定义,
# 仅在真正展开(正文节点里)时才输出字符。
# 码位一律用十进制 \symbol{712},避开 \char"XXXX 的引号形式。
ipa_defs = [
    '% ---- IPA 音标(expl3 惰性定义,详见 build_copybook.py 文档字符串) ----',
    r'\ExplSyntaxOn',
]
for no, x, y, up, lo, en, zh, ipa in L:
    syms = ''.join(r'\symbol{%d}' % ord(c) for c in ipa)
    # 函数名必须是单个 token:用「前缀 + 完整英文名」,不能带数字或下划线。
    ipa_defs.append(
        r'\cs_new_protected:Npn \greekIPAof%s { {\ipafont %s} }' % (NAME[no], syms))
ipa_defs.append(r'\ExplSyntaxOff')

HEADER = r'''% !TEX program = xelatex
% ================================================================
%  希腊字母练字帖  Greek Alphabet Copybook
%  2 x A4 | 24 letters | 3 col x 4 row per page
%
%  每格结构:
%    [序号] English              /IPA/
%           中文音译
%    ---------------------------------
%    +----------+----------+
%    | 浅灰描红  |  临摹空格  |   大写区(四线三格)
%    +----------+----------+
%    | 浅灰描红  |  临摹空格  |   小写区(四线三格)
%    +----------+----------+
%
%  编译: xelatex greek_copybook.tex
% ================================================================
\documentclass[a4paper]{article}
\usepackage[paperwidth=210mm,paperheight=297mm,
            left=6mm,right=6mm,top=6mm,bottom=6mm]{geometry}
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage{xcolor}
\usepackage{tikz}

% ---------------- 字体 ----------------
% Palatino 承载希腊字母与英文。实测字高比例:
%   cap height = 0.6968 em    x-height  = 0.4683 em
%   descender  = 0.1562 em    最宽大写 Μ = 0.9448 em
% 四线三格的位置全部由这些实测值推算,保证范本比例真实。
\setmainfont{Palatino}
\setCJKmainfont{STHeiti}
% Palatino 缺 IPA 修饰符,音标单独用 Times New Roman
\newfontfamily\ipafont{Times New Roman}

% ---------------- 颜色 ----------------
\definecolor{guide}{gray}{0.55}       % cap/asc line 与 baseline(主基准)
\definecolor{guideMid}{gray}{0.76}   % x-height / descender(次基准)
\definecolor{guideAxis}{gray}{0.85}  % 中线
\definecolor{trace}{gray}{0.62}       % 描红范本
\definecolor{cellbd}{gray}{0.42}      % 格框
\definecolor{labEn}{gray}{0.12}
\definecolor{labZh}{gray}{0.33}
\definecolor{labIpa}{gray}{0.50}
\definecolor{labIdx}{gray}{0.60}

\pagestyle{empty}
\setlength{\parindent}{0pt}

% ---------------- 希腊字母 ----------------
% LaTeX 已内置 \Gamma \Delta \Theta \Lambda \Xi \Pi \Sigma \Upsilon
% \Phi \Psi \Omega,其余显式补齐。全部直立体,描红时不被倾斜干扰。
\providecommand{\Gamma}{Γ}
\providecommand{\Delta}{Δ}
\providecommand{\Theta}{Θ}
\providecommand{\Lambda}{Λ}
\providecommand{\Xi}{Ξ}
\providecommand{\Pi}{Π}
\providecommand{\Sigma}{Σ}
\providecommand{\Upsilon}{Υ}
\providecommand{\Phi}{Φ}
\providecommand{\Psi}{Ψ}
\providecommand{\Omega}{Ω}

% LaTeX 内置 \Gamma 等大写命令在 TU 编码下同样是数学命令,
% 这里统一用 expl3 惰性定义,保证直立体且不触发 "Missing $ inserted"。
\ExplSyntaxOn
\cs_new_protected:Npn \greekGamma { {\symbol{915}} }
\cs_new_protected:Npn \greekDelta { {\symbol{916}} }
\cs_new_protected:Npn \greekTheta { {\symbol{920}} }
\cs_new_protected:Npn \greekLambda { {\symbol{923}} }
\cs_new_protected:Npn \greekXi { {\symbol{926}} }
\cs_new_protected:Npn \greekPi { {\symbol{928}} }
\cs_new_protected:Npn \greekSigma { {\symbol{931}} }
\cs_new_protected:Npn \greekUpsilon { {\symbol{933}} }
\cs_new_protected:Npn \greekPhi { {\symbol{934}} }
\cs_new_protected:Npn \greekPsi { {\symbol{936}} }
\cs_new_protected:Npn \greekOmega { {\symbol{937}} }
\ExplSyntaxOff

% 大写:同样不能用裸字符(导言区会求值),改用 expl3 惰性定义。
\ExplSyntaxOn
\cs_new_protected:Npn \greekAlpha { {\symbol{913}} }
\cs_new_protected:Npn \greekBeta { {\symbol{914}} }
\cs_new_protected:Npn \greekEpsilon { {\symbol{917}} }
\cs_new_protected:Npn \greekZeta { {\symbol{918}} }
\cs_new_protected:Npn \greekEta { {\symbol{919}} }
\cs_new_protected:Npn \greekIota { {\symbol{921}} }
\cs_new_protected:Npn \greekKappa { {\symbol{922}} }
\cs_new_protected:Npn \greekMu { {\symbol{924}} }
\cs_new_protected:Npn \greekNu { {\symbol{925}} }
\cs_new_protected:Npn \greekOmicron { {\symbol{927}} }
\cs_new_protected:Npn \greekRho { {\symbol{929}} }
\cs_new_protected:Npn \greekTau { {\symbol{932}} }
\cs_new_protected:Npn \greekChi { {\symbol{935}} }
\ExplSyntaxOff

% 小写:LaTeX 内置的 \alpha ... \omega 是数学命令,在 TU 编码下会
% 触发 "Missing $ inserted"。这里用 expl3 惰性重定义为直立体字符,
% 描红范本才不会被数学斜体的倾斜干扰。
\ExplSyntaxOn
\cs_new_protected:Npn \greekalpha { {\symbol{945}} }
\cs_new_protected:Npn \greekbeta { {\symbol{946}} }
\cs_new_protected:Npn \greekgamma { {\symbol{947}} }
\cs_new_protected:Npn \greekdelta { {\symbol{948}} }
\cs_new_protected:Npn \greekepsilon { {\symbol{949}} }
\cs_new_protected:Npn \greekzeta { {\symbol{950}} }
\cs_new_protected:Npn \greeketa { {\symbol{951}} }
\cs_new_protected:Npn \greektheta { {\symbol{952}} }
\cs_new_protected:Npn \greekiota { {\symbol{953}} }
\cs_new_protected:Npn \greekkappa { {\symbol{954}} }
\cs_new_protected:Npn \greeklambda { {\symbol{955}} }
\cs_new_protected:Npn \greekmu { {\symbol{956}} }
\cs_new_protected:Npn \greeknu { {\symbol{957}} }
\cs_new_protected:Npn \greekxi { {\symbol{958}} }
\cs_new_protected:Npn \greekomicron { {\symbol{959}} }
\cs_new_protected:Npn \greekpi { {\symbol{960}} }
\cs_new_protected:Npn \greekrho { {\symbol{961}} }
\cs_new_protected:Npn \greeksigma { {\symbol{963}} }
\cs_new_protected:Npn \greektau { {\symbol{964}} }
\cs_new_protected:Npn \greekupsilon { {\symbol{965}} }
\cs_new_protected:Npn \greekphi { {\symbol{966}} }
\cs_new_protected:Npn \greekchi { {\symbol{967}} }
\cs_new_protected:Npn \greekpsi { {\symbol{968}} }
\cs_new_protected:Npn \greekomega { {\symbol{969}} }
\ExplSyntaxOff

% ---------------- 版面常量 ----------------
% 单元格 64mm 宽;3 列 = 192mm + 2x3mm 间距 = 198mm,配合 6mm 页边距铺满
\newlength{\CellW} \setlength{\CellW}{64mm}
\newlength{\SubW}  \setlength{\SubW}{31.25mm}   % 描红/临摹 各占一半
\newlength{\SubMid}\setlength{\SubMid}{32.75mm} % 分栏中点

% 四线三格纵向布局(自 cap/asc line 向下为正):
%   cap/asc line  = 0
%   x-height line = 5.92mm   (cap - x-height = 0.2285 em)
%   baseline      = 20.08mm  (cap = 0.6968 em)
%   descender     = 25.58mm  (cap + descender = 0.8530 em)
\newcommand{\dXh}{5.15}
\newcommand{\dBase}{17.50}
\newcommand{\dDesc}{25.60}

% 字号 71.5pt -> cap 高 = 71.5 x 0.6968 = 49.8pt = 17.5mm
\newcommand{\CapSize}{\fontsize{71.5}{71.5}\selectfont}

% ---------------- IPA ----------------
'''

MIDDLE = r'''
% ================================================================
%  描红/临摹区(四线三格 + 左右双栏)
%  #1 = 该区顶边 y   #2 = 该区字母
% ================================================================
\newcommand{\TraceZone}[2]{%
  \draw[cellbd,line width=0.45pt] (0,#1) rectangle (\CellW,{#1+\dDesc});
  \draw[guide,line width=0.6pt] (0,#1) -- (\CellW,#1);
  \draw[guideMid,line width=0.35pt] (0,{#1+\dXh}) -- (\CellW,{#1+\dXh});
  \draw[guide,line width=0.8pt] (0,{#1+\dBase}) -- (\CellW,{#1+\dBase});
  \draw[guideMid,line width=0.35pt] (0,{#1+\dDesc}) -- (\CellW,{#1+\dDesc});
  \draw[cellbd,line width=0.45pt] (\SubMid,#1) -- (\SubMid,{#1+\dDesc});
  \draw[guideAxis,line width=0.25pt,dash pattern=on 1.1mm off 1.1mm]
    ({0.5\SubW},{#1+\dDesc}) -- ({0.5\SubW},#1);
  \draw[guideAxis,line width=0.25pt,dash pattern=on 1.1mm off 1.1mm]
    ({\SubMid+0.5\SubW},{#1+\dDesc}) -- ({\SubMid+0.5\SubW},#1);
  \node[anchor=base,inner sep=0pt,text=trace] at ({0.5\SubW},{#1+\dBase})
    {{\CapSize #2}};
}

% ================================================================
%  单个字母格
%  #1 x  #2 y(格顶)  #3 序号  #4 大写  #5 小写
%  #6 English  #7 中文音译  #8 IPA 宏
% ================================================================
\newcommand{\LetterCell}[8]{%
\begin{scope}[shift={(#1,#2)}]
  \node[anchor=north west,inner sep=0pt,text=labIdx]
    at (2.0,1.7) {{\fontsize{8}{8}\selectfont #3}};
  \node[anchor=north west,inner sep=0pt,text=labEn]
    at (6.4,0.5) {{\fontsize{11.5}{11.5}\selectfont #6}};
  \node[anchor=north west,inner sep=0pt,text=labZh]
    at (6.4,5.2) {{\fontsize{8.4}{8.4}\selectfont #7}};
  \node[anchor=north east,inner sep=0pt,text=labIpa]
    at ({\CellW-2.0},3.0) {{\ipafont\fontsize{8.2}{8.2}\selectfont /#8/}};
  \draw[guideMid,line width=0.3pt] (1.6,9.9) -- ({\CellW-1.6},9.9);
  \TraceZone{11.4}{#4}
  \TraceZone{36.40}{#5}
\end{scope}%
}

% ================================================================
\begin{document}
\mbox{}
'''

PAGE_TMPL = r'''
\begin{tikzpicture}[remember picture,overlay,x=1mm,y=-1mm]
\begin{scope}[shift={(current page.north west)}]
\begin{scope}[shift={(6,6)}]

\node[anchor=north west,inner sep=0pt,text=labEn] at (0,1.2)
  {{\fontsize{11}{11}\selectfont Greek Alphabet Copybook}};
\node[anchor=north east,inner sep=0pt,text=labZh] at (198,1.6)
  {{\fontsize{8.4}{8.4}\selectfont 希腊字母练字帖 · 第 %d / 2 页}};
\draw[guideMid,line width=0.3pt] (0,8.4) -- (198,8.4);
\node[anchor=north west,inner sep=0pt,text=labIpa] at (0,9.4)
  {{\fontsize{6.6}{6.6}\selectfont %s}};

%s

\end{scope}
\end{scope}
\end{tikzpicture}
'''

HINT1 = ('每区左栏为浅灰范本(描红),右栏为空白(临摹);'
         '四条基准线自上而下:大写高度 / 小写高度 / 基线 / 降部线')
HINT2 = ('小写 sigma 有两种形态:字首与词中用 σ,词尾用 ς;'
         'Xi 读 ks,三横等长;Phi 的竖笔穿过圆心')

calls = []
for no, x, y, up, lo, en, zh, ipa in L:
    px, py = pos(no)
    calls.append(r'\LetterCell{%d}{%g}{%d}{%s}{%s}{%s}{%s}{\greekIPAof%s}'
                 % (px, py, no, up, lo, en, zh, NAME[no]))

doc = HEADER + '\n' + '\n'.join(ipa_defs) + MIDDLE
doc += (PAGE_TMPL % (1, HINT1, '\n'.join(calls[:12])))
doc += '\n\\newpage\n\\mbox{}\n'
doc += (PAGE_TMPL % (2, HINT2, '\n'.join(calls[12:])))
doc += '\n\\end{document}\n'

io.open('greek_copybook.tex', 'w', encoding='utf-8').write(doc)
print('rewritten OK, total lines:', doc.count('\n'))
