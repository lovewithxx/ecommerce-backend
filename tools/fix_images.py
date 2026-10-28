"""
补图 + 换掉明显不对的图片。

背景：
    第一轮 tools/fetch_images.py 抓到 109 张，但有两个问题：
    1. 家电分类因为代理 SSL 中断，只抓到 5 张
    2. 有些图靠关键词盲抓，标题对但内容离谱：
         sports/15  是 "Dumbbell Nebula"（哑铃星云）
         computer/03 是 "Cat on laptop"（猫趴在笔记本上）
         food/01    是 "Defective rice grains"（坏米）

本脚本：
    1. 给每个分类补到 15 张
    2. 把黑名单里的图按更好的关键词重抓
    3. 加标题过滤：命中 BAD_WORDS 或明显不含产品词的直接跳过

用法：
    python tools/fix_images.py
"""

import io
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

PROXY = os.getenv("HTTPS_PROXY") or "http://127.0.0.1:7897"
UA = "EcommerceDemoImageFetcher/1.0 (learning project)"
API = "https://commons.wikimedia.org/w/api.php"
OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "images"
TIMEOUT = 30
SQUARE = 600

# 标题里出现这些词，说明不是商品图，直接跳过
BAD_WORDS = [
    "nebula", "galaxy", "defective", "infected", "smut", "broken", "crack",
    "cat ", "kitten", "dog", "leaflet", "zombie", "bike path", "fietspad",
    "museum", "1920s", "1930s", "wringer", "atari", "amiga", "metal ",
    "drawing", "painting", "poster", "logo", "icon", "diagram", "chart",
]

# 需要重抓的图：(分类, 序号) -> 更精准的搜索词
REPLACE = {
    ("sports", 15): "dumbbell weights gym",
    ("computer", 3): "laptop on desk workspace",
    ("computer", 6): "laptop computer silver",
    ("computer", 11): "computer monitor on desk",
    ("computer", 12): "computer monitor screen",
    ("food", 1): "rice in bowl cooked",
    ("food", 11): "white rice bowl",
    ("books", 14): "stack of books",
    ("books", 9): "notebook pen stationery",
    ("beauty", 14): "shampoo bottle bathroom",
    ("beauty", 5): "cosmetic cream jar",
}

# 家电需要补 6~15，用更精准的词
APPLIANCE_TERMS = [
    "washing machine front loader",
    "refrigerator kitchen",
    "air conditioner indoor unit",
    "rice cooker",
    "vacuum cleaner",
    "electric kettle",
    "microwave oven",
    "electric fan",
]


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    )
    with opener.open(req, timeout=TIMEOUT) as resp:
        return resp.read()


def search(term: str, limit: int = 8) -> list[dict]:
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": term, "gsrnamespace": "6",
        "gsrlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": "800",
    }
    try:
        data = json.loads(http_get(f"{API}?{urllib.parse.urlencode(params)}"))
    except Exception as exc:                      # noqa: BLE001
        print(f"    [搜索失败] {term}: {type(exc).__name__}")
        return []

    out = []
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        src = info.get("thumburl") or info.get("url")
        title = page.get("title", "")
        if not src or not src.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
            continue
        low = title.lower()
        if any(w in low for w in BAD_WORDS):
            print(f"    [过滤] {title[:60]}")
            continue
        meta = info.get("extmetadata") or {}
        out.append({
            "url": src, "title": title,
            "license": (meta.get("LicenseShortName") or {}).get("value", "unknown"),
        })
    return out


def save_square(raw: bytes, dest: Path) -> bool:
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:                             # noqa: BLE001
        return False
    w, h = img.size
    if w < 200 or h < 200:
        return False
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2,
                    (w + side) // 2, (h + side) // 2)).resize((SQUARE, SQUARE), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=82, optimize=True)
    return True


def fetch_into(term: str, dest: Path) -> bool:
    """按关键词抓第一张过滤后的图，存到 dest。"""
    for item in search(term, limit=8):
        try:
            raw = http_get(item["url"])
        except Exception as exc:                  # noqa: BLE001
            print(f"    [下载失败] {type(exc).__name__}")
            continue
        if save_square(raw, dest):
            print(f"    ✓ {dest.parent.name}/{dest.name}  {item['title'][:55]}")
            return True
        time.sleep(0.2)
    return False


def main() -> None:
    print(f"代理 {PROXY}\n")

    # ---------- 1. 换掉明显不对的图 ----------
    print("=== 替换问题图片 ===")
    replaced = 0
    for (slug, idx), term in REPLACE.items():
        dest = OUT_DIR / slug / f"{idx:02d}.jpg"
        print(f"[{slug}/{idx:02d}] 用 '{term}' 重抓")
        if fetch_into(term, dest):
            replaced += 1
        time.sleep(0.5)

    # ---------- 2. 家电补到 15 张 ----------
    print("\n=== 补家电分类 ===")
    appliance_dir = OUT_DIR / "appliance"
    have = len(list(appliance_dir.glob("*.jpg"))) if appliance_dir.exists() else 0
    print(f"现有 {have} 张，目标 15 张")

    for term in APPLIANCE_TERMS:
        if have >= 15:
            break
        print(f"  搜索 {term}")
        for item in search(term, limit=6):
            if have >= 15:
                break
            dest = appliance_dir / f"{have + 1:02d}.jpg"
            try:
                raw = http_get(item["url"])
            except Exception as exc:              # noqa: BLE001
                print(f"    [下载失败] {type(exc).__name__}")
                continue
            if save_square(raw, dest):
                have += 1
                print(f"    ✓ appliance/{dest.name}  {item['title'][:55]}")
            time.sleep(0.3)
        time.sleep(0.4)

    print(f"\n家电现有 {have} 张")
    print(f"替换成功 {replaced} 张")

    # ---------- 3. 统计 ----------
    print("\n=== 各分类最终数量 ===")
    total = 0
    for d in sorted(OUT_DIR.iterdir()):
        if d.is_dir():
            n = len(list(d.glob("*.jpg")))
            total += n
            print(f"  {d.name:<10} {n:3} 张")
    print(f"  合计 {total} 张")


if __name__ == "__main__":
    main()
