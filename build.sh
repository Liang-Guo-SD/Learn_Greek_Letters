#!/usr/bin/env bash
# ================================================================
#  Learn_Greek_Letter — 一键构建
#
#  用法:
#     ./build.sh
#
#  依赖:
#     python3     (>= 3.8,仅标准库,无第三方依赖)
#     tectonic    或 xelatex
# ================================================================
set -eu
cd "$(dirname "$0")"

# ---- 探测 Python ----
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "错误: 找不到 python3。请先安装 Python 3.8+。" >&2
  exit 1
fi

# ---- 探测 LaTeX 引擎 ----
# 注意:在部分 shell / 沙箱环境下 PATH 会被裁剪,Homebrew 的 bin 目录
# 可能不在其中,所以显式补上常见的两个位置。
for d in /opt/homebrew/bin /usr/local/bin; do
  case ":$PATH:" in
    *":$d:"*) ;;
    *) PATH="$PATH:$d" ;;
  esac
done
export PATH

ENGINE=""
for c in tectonic xelatex lualatex pdflatex; do
  if command -v "$c" >/dev/null 2>&1; then ENGINE="$c"; break; fi
done
if [ -z "$ENGINE" ]; then
  echo "错误: 找不到 LaTeX 引擎(tectonic / xelatex)。" >&2
  echo "  macOS:   brew install tectonic         (最轻量,推荐)" >&2
  echo "  完整版:   brew install --cask mactex" >&2
  exit 1
fi

echo "[1/2] 生成 greek_copybook.tex  (python: $PY)"
"$PY" build_copybook.py

echo "[2/2] 编译 PDF  (engine: $ENGINE)"
rm -f greek_copybook.aux greek_copybook.log

if [ "$ENGINE" = "tectonic" ]; then
  "$ENGINE" -X compile greek_copybook.tex
else
  # 传统引擎需跑两遍才能稳定交叉引用
  "$ENGINE" -interaction=nonstopmode -halt-on-error greek_copybook.tex >/dev/null
  "$ENGINE" -interaction=nonstopmode -halt-on-error greek_copybook.tex >/dev/null
  rm -f greek_copybook.aux greek_copybook.log
fi

echo ""
echo "完成: $(pwd)/greek_copybook.pdf"
echo '打印时请选择 A4 纵向、缩放 100%(不要勾选"适合页面")。'
