"""
生成商品卡图片（本地渲染，不联网）。

为什么不用网上抓的图：
    之前从 Wikimedia Commons 按分类抓了 120 张，问题是
        1. 一个分类 15 张，而分类里有十来个品类（手机/耳机/手表/音箱…）
        2. 食品分类 15 张全是米粒和咖啡豆，根本没有牛奶鸡蛋
    结果就是"洗衣机配手机"，无论怎么分配都对不上。

现在改成：每个商品一张专属图，图上写它自己的名字，绝对不会错配。

输出：
    web/images/gen/{分类ID}_{款式序号}_{规格序号}.jpg     共 400 张

用法：
    python tools/gen_images.py
"""

import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 复用商品数据的定义，保证"图上的名字"和"数据库里的名字"一致
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_products import BASE, CATEGORIES, TYPE_WORDS, VARIANTS_LEN  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "images" / "gen"
SIZE = 500
PER_CATEGORY = 50

# 每个分类一套配色（主色，亮），同一个分类里靠轻微亮度差区分商品
PALETTE = {
    1: (236, 90, 70),      # 手机数码 橙红
    2: (58, 132, 214),     # 家用电器 蓝
    3: (228, 140, 50),     # 服饰鞋包 橙
    4: (74, 162, 96),      # 食品生鲜 绿
    5: (124, 108, 210),    # 图书文娱 紫
    6: (42, 158, 152),     # 运动户外 青
    7: (214, 96, 140),     # 美妆个护 粉
    8: (72, 112, 172),     # 电脑办公 深蓝
}

# Windows 自带字体，按优先级找
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑 粗体
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",   # 黑体
    r"C:\Windows\Fonts\arialbd.ttf",
]


def find_font() -> str:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit("找不到可用的中文字体，请检查 C:\\Windows\\Fonts")


FONT_PATH = None


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def shift(color: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    """把颜色整体调亮或调暗，用来在同一分类里做出层次。"""
    return tuple(max(0, min(255, c + delta)) for c in color)


def make_background(base: tuple[int, int, int]) -> Image.Image:
    """
    竖向渐变背景：上方亮、下方暗。

    一次性按行画，比逐像素快得多。
    """
    img = Image.new("RGB", (SIZE, SIZE), base)
    draw = ImageDraw.Draw(img)
    top = shift(base, 26)
    bottom = shift(base, -34)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (SIZE, y)], fill=color)
    return img


def wrap_text(draw: ImageDraw.ImageDraw, text: str, f, max_width: int, max_lines: int = 3):
    """
    折行：优先按空格断词，单个词太长才按字符硬切。

    按字符硬切会把 "8+128G" 切成 "8+128" / "G"，最后一行剩一个字母很难看，
    所以先按空格试，放不下才退回逐字切。
    """
    lines: list[str] = []
    cur = ""

    def fits(s: str) -> bool:
        return draw.textlength(s, font=f) <= max_width

    for word in text.split(" "):
        cand = (cur + " " + word).strip()
        if fits(cand):
            cur = cand
            continue

        # 这一行放不下了，先把当前行收掉
        if cur:
            lines.append(cur)
            cur = ""
            if len(lines) == max_lines:
                break

        # 新词自己就超宽，只能按字符切
        while not fits(word) and len(word) > 1:
            cut = len(word)
            while cut > 1 and not fits(word[:cut]):
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
            if len(lines) == max_lines:
                break
        if len(lines) == max_lines:
            break
        cur = word

    else:
        if cur:
            lines.append(cur)
        return lines

    # 行数用完了还有剩余内容，补省略号
    if lines:
        lines[-1] = lines[-1][:-1] + "…"
    return lines


def render(key: str, name: str, subtitle: str, cat_name: str, base_color) -> Path:
    # 同一分类内用 key 的哈希做一点明暗偏移，避免每张图一模一样
    tone = int(hashlib.md5(key.encode()).hexdigest(), 16) % 5
    color = shift(base_color, (tone - 2) * 9)

    img = make_background(color)
    draw = ImageDraw.Draw(img, "RGBA")

    # 右上角装饰圆
    draw.ellipse(
        [SIZE * 0.62, -SIZE * 0.22, SIZE * 1.22, SIZE * 0.38],
        fill=(255, 255, 255, 26),
    )

    # ★ 中间的水印大字要大、要淡、而且要放在文字区上方 ★
    #   一开始放太大又太靠下，结果和商品名叠在一起，字全糊了。
    mono_font = font(200)
    mono = name[0] if name else "?"
    mw = draw.textlength(mono, font=mono_font)
    draw.text(((SIZE - mw) / 2, 78), mono, font=mono_font, fill=(255, 255, 255, 30))

    # ★ 底部遮罩 ★
    #   无论背景什么颜色，文字区加一层由透明到深的黑色，
    #   白色文字永远读得清。
    draw.rectangle([0, SIZE * 0.56, SIZE, SIZE], fill=(0, 0, 0, 0))
    for i in range(int(SIZE * 0.44)):
        alpha = int(120 * (i / (SIZE * 0.44)) ** 1.4)
        y = int(SIZE * 0.56) + i
        draw.line([(0, y), (SIZE, y)], fill=(0, 0, 0, alpha))

    # 左上角分类标签
    tag_font = font(20)
    tag_w = draw.textlength(cat_name, font=tag_font)
    draw.rounded_rectangle(
        [28, 28, 28 + tag_w + 32, 70], radius=21, fill=(255, 255, 255, 60)
    )
    draw.text((28 + 16, 36), cat_name, font=tag_font, fill=(255, 255, 255, 240))

    # 底部文字：副标题在最下，商品名往上排
    sub_font = font(18)
    name_font = font(27)
    line_h = 33

    lines = wrap_text(draw, name, name_font, SIZE - 60, max_lines=3)

    sub_y = SIZE - 38
    name_bottom = sub_y - 26
    y = name_bottom - line_h * len(lines)
    for line in lines:
        draw.text((30, y), line, font=name_font, fill=(255, 255, 255, 252))
        y += line_h

    if subtitle:
        subs = wrap_text(draw, subtitle, sub_font, SIZE - 60, max_lines=1)
        draw.text((30, sub_y), subs[0], font=sub_font, fill=(255, 255, 255, 190))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / f"{key}.jpg"
    img.save(dest, "JPEG", quality=82, optimize=True)
    return dest


def main() -> None:
    global FONT_PATH
    FONT_PATH = find_font()
    print(f"字体：{FONT_PATH}")
    print(f"输出：{OUT_DIR}\n")

    total = 0
    for cid, _slug, cat_name, _icon in CATEGORIES:
        entries = BASE[cid]
        idx = 0
        for _ in range(PER_CATEGORY):
            entry_i = idx % len(entries)
            vpos = (idx // len(entries)) % VARIANTS_LEN
            idx += 1

            brand, line, _price, tagline, _specs, _core, variants = entries[entry_i]
            variant = variants[vpos]
            type_word = TYPE_WORDS.get(cid, [""] * 10)[entry_i]

            # ★ 名称拼法必须和 gen_products.py 完全一致 ★
            name = " ".join(x for x in (brand, line, type_word, variant) if x)
            key = f"{cid}_{entry_i:02d}_{vpos}"

            render(key, name, tagline, cat_name, PALETTE[cid])
            total += 1

        print(f"[{cat_name}] 10 个款式 × 5 规格 = {PER_CATEGORY} 张")

    files = list(OUT_DIR.glob("*.jpg"))
    size_mb = sum(f.stat().st_size for f in files) / 1024 / 1024
    print("=" * 46)
    print(f"共 {total} 张，{size_mb:.1f} MB")
    print(f"目录：{OUT_DIR}")


if __name__ == "__main__":
    main()
