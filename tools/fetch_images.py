"""
从维基共享资源（Wikimedia Commons）抓真实商品图片。

为什么用它：
    1. 都是真实商品照（Bose 耳机、Adidas 球鞋、戴尔显示器…），不是随机风景
    2. 授权是 CC / 公有领域，非商业项目可以直接用（manifest.json 里记录了来源和协议）
    3. 有搜索 API，能按关键词找图；图片 CDN 也能访问

用法（需要能访问外网，脚本走系统代理）：
    python tools/fetch_images.py

产出：
    web/images/<分类slug>/01.jpg … 15.jpg     统一裁成正方形，方便商品卡片显示
    web/images/manifest.json                  每张图的来源标题 / 授权 / 原始链接
"""

import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

# ---------------- 配置 ----------------
PROXY = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or "http://127.0.0.1:7897"
UA = "EcommerceDemoImageFetcher/1.0 (learning project; contact: local)"
PER_CATEGORY = 15          # 每个分类下多少张图
API = "https://commons.wikimedia.org/w/api.php"
OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "images"

# 分类：slug（用作目录名）、中文名、搜索关键词（英文命中率更高）
CATEGORIES = [
    ("phone", "手机数码", ["smartphone", "headphones", "bluetooth speaker", "tablet computer", "power bank"]),
    ("appliance", "家用电器", ["washing machine", "refrigerator", "air conditioner", "rice cooker", "vacuum cleaner"]),
    ("clothing", "服饰鞋包", ["sneakers", "down jacket", "jeans", "backpack", "leather handbag"]),
    ("food", "食品生鲜", ["rice grains", "coffee beans", "milk carton", "apples fruit", "eggs carton"]),
    ("books", "图书文娱", ["book cover", "ukulele", "board game", "jigsaw puzzle", "notebook stationery"]),
    ("sports", "运动户外", ["yoga mat", "dumbbell", "camping tent", "hiking backpack", "bicycle helmet"]),
    ("beauty", "美妆个护", ["cosmetics bottles", "shampoo bottle", "toothbrush", "perfume bottle", "face cream"]),
    ("computer", "电脑办公", ["laptop computer", "computer monitor", "mechanical keyboard", "computer mouse", "office chair"]),
]

TIMEOUT = 30
SQUARE = 600               # 统一裁成 600x600


def build_opener() -> urllib.request.OpenerDirector:
    handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    return urllib.request.build_opener(handler)


OPENER = build_opener()


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with OPENER.open(req, timeout=TIMEOUT) as resp:
        return resp.read()


def search_images(term: str, limit: int) -> list[dict]:
    """
    调 Commons 搜索 API，返回图片信息列表。

    参数说明：
        gsrnamespace=6   只在"文件"命名空间里搜
        iiurlwidth=800   让它返回 800px 宽的缩略图地址（原图可能几十 MB）
        extmetadata     带上授权信息，方便记录来源
    """
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": term,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "800",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"

    try:
        data = json.loads(http_get(url))
    except Exception as exc:                      # noqa: BLE001
        print(f"    [警告] 搜索失败 {term}: {exc}")
        return []

    pages = (data.get("query") or {}).get("pages") or {}
    items = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        src = info.get("thumburl") or info.get("url")
        if not src:
            continue
        # 只保留常见位图格式，跳过 svg（Pillow 打不开）和超大文件
        if not src.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
            continue
        meta = info.get("extmetadata") or {}
        items.append({
            "url": src,
            "title": page.get("title", ""),
            "license": (meta.get("LicenseShortName") or {}).get("value", "unknown"),
            "artist": (meta.get("Artist") or {}).get("value", "")[:120],
        })
    return items


def to_square_jpeg(raw: bytes, dest: Path) -> bool:
    """居中裁成正方形再缩放到 600x600，存 JPEG。返回是否成功。"""
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:                      # noqa: BLE001
        print(f"    [跳过] 图片无法解析: {exc}")
        return False

    w, h = img.size
    if w < 200 or h < 200:                        # 太小的图不要，放大后模糊
        print(f"    [跳过] 尺寸太小 {w}x{h}")
        return False

    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((SQUARE, SQUARE), Image.LANCZOS)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=82, optimize=True)
    return True


def main() -> None:
    print(f"代理：{PROXY}")
    print(f"输出目录：{OUT_DIR}")
    print(f"每个分类 {PER_CATEGORY} 张\n")

    manifest: dict[str, list[dict]] = {}
    total_ok = 0

    for slug, cn_name, terms in CATEGORIES:
        print(f"[{cn_name}] {slug}")
        bucket: list[dict] = []
        index = 0

        for term in terms:
            if len(bucket) >= PER_CATEGORY:
                break

            need = PER_CATEGORY - len(bucket)
            print(f"  搜索: {term}（还差 {need} 张）")
            found = search_images(term, limit=min(need + 3, 12))
            time.sleep(0.6)                        # 对 API 友好一点

            for item in found:
                if len(bucket) >= PER_CATEGORY:
                    break
                index += 1
                dest = OUT_DIR / slug / f"{len(bucket) + 1:02d}.jpg"
                try:
                    raw = http_get(item["url"])
                except Exception as exc:           # noqa: BLE001
                    print(f"    [失败] 下载出错: {exc}")
                    continue

                if to_square_jpeg(raw, dest):
                    bucket.append({
                        "file": f"{slug}/{dest.name}",
                        "title": item["title"],
                        "license": item["license"],
                        "source": item["url"].split("?")[0],
                    })
                    print(f"    ✓ {dest.name}  ({len(raw)//1024} KB)  {item['title'][:50]}")
                time.sleep(0.3)

        manifest[slug] = bucket
        total_ok += len(bucket)
        print(f"  小计：{len(bucket)}/{PER_CATEGORY}\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 50)
    print(f"完成：共 {total_ok} 张，分布在 {len(CATEGORIES)} 个分类")
    print(f"来源与授权记录：{OUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    sys.exit(main())
