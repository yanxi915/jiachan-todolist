# -*- coding: utf-8 -*-
"""从项目内的 3 张原图裁切「两位角色并排」的整体贴图（不拆开、不重绘、不生成新图）。

原图 1219x708 里两位 Q 版角色并排坐着，保持原图关系整体取景：
  crop = (4, 0, 1210, 706)

输出：
  assets/pair_calm.png / pair_happy.png / pair_worry.png   整体贴图（280x164）
  assets/meta.json                                         贴图尺寸、四只眼睛的位置
  assets/app.ico                                           快捷方式图标（取自原图）
"""
import json
import os
from PIL import Image, ImageDraw

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(SRC, "assets")
DBG = os.path.join(OUT, "_debug")
os.makedirs(OUT, exist_ok=True)
os.makedirs(DBG, exist_ok=True)

FILES = [("平静", "calm"), ("笑颜", "happy"), ("糟糕", "worry")]
CROP = (4, 0, 1210, 706)
TARGET_W = 264

# 四只眼睛在「原图坐标」里的框（实测：左角色两只 + 右角色两只）
EYES_SRC = [
    {"owner": "l", "box": [142, 327, 155, 108]},
    {"owner": "l", "box": [280, 327, 159, 108]},
    {"owner": "r", "box": [762, 327, 134, 103]},
    {"owner": "r", "box": [896, 327, 138, 103]},
]
# 右角色「糟糕」那张是捂脸，看不到眼睛，该表情不参与眨眼
NO_BLINK = {"r": ["worry"]}


def premul_resize(im, size):
    """预乘 alpha 缩放，避免半透明边缘出现白/黑边。"""
    im = im.convert("RGBA")
    data = list(im.getdata())
    pm = [(r * a // 255, g * a // 255, b * a // 255, a) for r, g, b, a in data]
    tmp = Image.new("RGBA", im.size)
    tmp.putdata(pm)
    tmp = tmp.resize(size, Image.LANCZOS)
    out = []
    for r, g, b, a in tmp.getdata():
        if a == 0:
            out.append((0, 0, 0, 0))
        else:
            out.append((min(255, r * 255 // a), min(255, g * 255 // a), min(255, b * 255 // a), a))
    res = Image.new("RGBA", size)
    res.putdata(out)
    return res


def alpha_centroid(im, top_ratio=0.62):
    w, h = im.size
    px = im.getchannel("A").load()
    sx = sy = n = 0
    for y in range(0, int(h * top_ratio), 2):
        for x in range(0, w, 2):
            if px[x, y] > 120:
                sx += x
                sy += y
                n += 1
    return (sx / n, sy / n) if n else (w / 2.0, h / 2.0)


w0 = CROP[2] - CROP[0]
h0 = CROP[3] - CROP[1]
scale = TARGET_W / float(w0)
sw, sh = TARGET_W, int(round(h0 * scale))

base = Image.open(os.path.join(SRC, "平静.PNG")).convert("RGBA").crop(CROP)
bcx, bcy = alpha_centroid(base)

meta = {"crop": list(CROP), "scale": scale, "sprite": [sw, sh],
        "expressions": [], "no_blink": NO_BLINK}

# 原图眼睛框 → 贴图坐标
EYES = []
for e in EYES_SRC:
    x, y, w, h = e["box"]
    EYES.append({"owner": e["owner"], "box": [
        int(round((x - CROP[0]) * scale)),
        int(round((y - CROP[1]) * scale)),
        int(round(w * scale)),
        int(round(h * scale)),
    ]})
meta["eyes"] = EYES

for cn, en in FILES:
    im = Image.open(os.path.join(SRC, cn + ".PNG")).convert("RGBA").crop(CROP)
    cx, cy = alpha_centroid(im)
    dx, dy = int(round(bcx - cx)), int(round(bcy - cy))
    if dx or dy:
        canvas = Image.new("RGBA", im.size, (0, 0, 0, 0))
        canvas.paste(im, (dx, dy))
        im = canvas

    sp = premul_resize(im, (sw, sh))
    name = "pair_%s.png" % en
    sp.save(os.path.join(OUT, name))
    meta["expressions"].append({"id": en, "file": name})

    if en == "calm":
        ov = sp.resize((sw * 3, sh * 3), Image.NEAREST).convert("RGBA")
        d = ImageDraw.Draw(ov)
        for e in EYES:
            x, y, ew, eh = e["box"]
            d.rectangle([x * 3, y * 3, (x + ew) * 3, (y + eh) * 3], outline=(255, 0, 0, 255))
        ov.save(os.path.join(DBG, "grid_pair.png"))

json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# 图标：用整体贴图居中
pair = Image.open(os.path.join(OUT, "pair_calm.png")).convert("RGBA")
side = max(pair.size)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(pair, ((side - pair.size[0]) // 2, (side - pair.size[1]) // 2))
sq.resize((256, 256), Image.LANCZOS).save(
    os.path.join(OUT, "app.ico"),
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

print("done", sw, sh, [e["file"] for e in meta["expressions"]])
