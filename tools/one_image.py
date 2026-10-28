"""
单张补图工具（临时用）。

用法：
    python tools/one_image.py beauty 14 "shampoo"
    python tools/one_image.py computer 12 "computer monitor"
"""

import sys

from fix_images import OUT_DIR, fetch_into


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        return
    slug, idx, term = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    dest = OUT_DIR / slug / f"{idx:02d}.jpg"
    print(f"用 '{term}' 抓取 -> {slug}/{idx:02d}.jpg")
    if fetch_into(term, dest):
        print("成功")
    else:
        print("失败（没有合适的图）")


if __name__ == "__main__":
    main()
