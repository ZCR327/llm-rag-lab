# -*- coding: utf-8 -*-
"""
zhipu_ocr.py — 智谱 GLM-4V 多模态 OCR (学生题目截图处理)

替代方案: PaddlePaddle (Intel Iris Xe 崩) / EasyOCR (单字符孤岛) / jina API (国内不通)
新方案: 智谱 GLM-4V 多模态 - 直接读图 + 公式 + 上下文

两种模式:
  --extract 纯 OCR (提取所有文字, 公式用 LaTeX)
  --solve   OCR + 解答 (提取题目 + 给出答案)

用法:
  python scripts/zhipu_ocr.py photo.jpg                  # 默认 extract
  python scripts/zhipu_ocr.py photo.jpg --mode solve     # 解题模式
  python scripts/zhipu_ocr.py photo.jpg --model glm-4v-plus   # 强模型

依赖: zhipuai >= 2.1.5 (pip install zhipuai)
环境: .env 需 ZHIPUAI_KEY
"""
import os
import sys
import base64
import argparse
import mimetypes
from pathlib import Path

from dotenv import load_dotenv

# 找 .env (项目根)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)


def get_mime(path: Path) -> str:
    """根据文件扩展名猜 MIME, 智谱 API 接受 jpeg/png/webp/gif"""
    mime, _ = mimetypes.guess_type(str(path))
    if mime is None:
        # fallback by extension
        ext = path.suffix.lower()
        mime = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
            ".gif": "image/gif", ".bmp": "image/bmp",
        }.get(ext, "image/jpeg")
    return mime


def image_to_data_url(path: Path) -> str:
    """读图 → base64 data URL (智谱 API 格式)"""
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{get_mime(path)};base64,{b64}"


PROMPTS = {
    "extract": (
        "请提取图片中所有文字内容, 数学公式用 LaTeX 格式 (例如 $\\frac{{a}}{{b}}$, $x^2$). "
        "保留题号 (如 1., (1), ①) 和分段. "
        "**直接输出提取的文本, 不要解释, 不要说'以下是提取的内容'这种前缀**. "
        "如果图片不清晰或不是文字内容, 输出 [无法识别]."
    ),
    "solve": (
        "请解答图片中的题目. 步骤:\n"
        "1. **提取题目**: 完整抄写题目的文字, 公式用 LaTeX.\n"
        "2. **分析**: 简短说明解题思路 (1-3 句).\n"
        "3. **解答**: 给出完整步骤 + 最终答案.\n"
        "如果有多个小题, 用 (1), (2), (3) 分别作答."
    ),
}


def ocr_image(path: str, mode: str = "extract", model: str = "glm-4v-flash") -> str:
    """调智谱 GLM-4V 多模态, 单图 OCR 或 解题"""
    api_key = os.environ.get("ZHIPUAI_KEY")
    if not api_key:
        raise RuntimeError("缺 ZHIPUAI_KEY - 检查 .env")

    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)

    img_path = Path(path)
    if not img_path.exists():
        raise FileNotFoundError(f"图片不存在: {path}")
    if mode not in PROMPTS:
        raise ValueError(f"mode 必须是: {list(PROMPTS.keys())}, 收到 {mode!r}")

    prompt = PROMPTS[mode]
    data_url = image_to_data_url(img_path)

    print(f"[zhipu_ocr] 图片: {path} ({img_path.stat().st_size} B, {get_mime(img_path)})")
    print(f"[zhipu_ocr] 模型: {model}, 模式: {mode}")

    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": prompt},
            ],
        }],
        temperature=0.1,  # OCR 要准确, 低 temperature
        max_tokens=1024,   # glm-4v-flash 上限 (glm-4v-plus 可更高)
    )
    return resp.choices[0].message.content


def main():
    p = argparse.ArgumentParser(description="智谱 GLM-4V OCR (学生题目截图)")
    p.add_argument("image", help="图片路径 (jpg/png/webp)")
    p.add_argument("--mode", choices=["extract", "solve"], default="extract",
                   help="extract=纯OCR, solve=OCR+解答")
    p.add_argument("--model", default="glm-4v-flash",
                   choices=["glm-4v-flash", "glm-4v", "glm-4v-plus"],
                   help="flash 最便宜, plus 最强")
    p.add_argument("--out", help="输出到文件 (默认 stdout)")
    args = p.parse_args()

    try:
        result = ocr_image(args.image, mode=args.mode, model=args.model)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    if args.out:
        Path(args.out).write_text(result, encoding="utf-8")
        print(f"[OK] 写入 {args.out} ({len(result)} chars)")
    else:
        print(f"\n{'='*60}\n[RESULT]\n{'='*60}\n{result}")


if __name__ == "__main__":
    main()