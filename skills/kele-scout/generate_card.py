#!/usr/bin/env python3
"""
KeleClaw 球探 — 球星撞型卡渲染器。

在 Hermes pod 内由 agent 调用：agent 看图判断撞型球星/特征/锐评后，
传文字参数进来，本脚本调 gpt-image-2 出「神似致敬」卡面 + PIL 叠精确文字，
渲染一张 FIFA 风格球员卡，最后一行打印卡片绝对路径（供 agent 输出 MEDIA:）。

不接收、不渲染用户原始照片 —— 卡面是 AI 生成的通用形象，天然不泄露真脸。

环境依赖（pod 已具备）：python3 + PIL；keleclaw 凭据在 env
(OPENAI_API_KEY / OPENAI_BASE_URL)。思源黑体首次运行自动下载缓存到 PVC。
"""
import os, sys, json, base64, time, argparse, urllib.request, urllib.error

FONT_URLS = {
    "Heavy": "https://cdn.jsdelivr.net/gh/adobe-fonts/source-han-sans@release/OTF/SimplifiedChinese/SourceHanSansSC-Heavy.otf",
    "Bold":  "https://cdn.jsdelivr.net/gh/adobe-fonts/source-han-sans@release/OTF/SimplifiedChinese/SourceHanSansSC-Bold.otf",
}
FALLBACK_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
FONT_CACHE = os.path.expanduser("~/.cache/kele-scout/fonts")  # ~ = /opt/data (PVC) in pod
CARD_DIR = os.path.expanduser("~/.cache/kele-scout/cards")

# 卡片比例固定 2:3 竖版（gpt-image-2 原生支持的竖版尺寸，无裁剪/无黑边；勿改）
CARD_SIZE = "1024x1536"
MATCH_MIN, MATCH_MAX = 50, 99
RUPING_MAX_CHARS = 44   # 软上限：超出截断，防卡面越界
RUPING_MAX_LINES = 3

GOLD = (247, 206, 88)
WHITE = (248, 250, 248)
GRAY = (188, 198, 193)
INK = (8, 20, 14)


def log(*a):
    print(*a, file=sys.stderr)


def ensure_fonts():
    """返回 (heavy_path, bold_path)；任一下载失败则整体回退 wqy。"""
    os.makedirs(FONT_CACHE, exist_ok=True)
    paths = {}
    for weight, url in FONT_URLS.items():
        dst = os.path.join(FONT_CACHE, f"SourceHanSansSC-{weight}.otf")
        if not (os.path.exists(dst) and os.path.getsize(dst) > 1_000_000):
            try:
                log(f"[font] downloading {weight} ...")
                req = urllib.request.Request(url, headers={"User-Agent": "kele-scout"})
                tmp = dst + ".part"  # 先写临时文件再 rename，避免半截文件
                with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                    f.write(r.read())
                os.replace(tmp, dst)
            except Exception as e:
                log(f"[font] {weight} download failed: {e} -> fallback wqy")
                return FALLBACK_FONT, FALLBACK_FONT
        paths[weight] = dst
    return paths["Heavy"], paths["Bold"]


def gen_card_art(features, tone, key, base):
    """调 gpt-image-2 出卡面底图，返回 PNG bytes。仅对 429/5xx 重试。"""
    vibe = ("youthful cheerful teenage athlete, bright sunny happy energy"
            if tone == "minor" else "fierce confident heroic energy")
    prompt = (
        f"Premium soccer trading card character art: {features}, {vibe}, "
        "dynamic action pose, semi-realistic stylized illustration, dramatic rim "
        "lighting, emerald-green and gold premium card-frame aesthetic, upper-body "
        "composition, dark gradient stadium background, highly detailed, clean edges, "
        "leave upper area and lower third relatively clear for text overlay, "
        "NO text, NO logos, NO watermark, a generic non-identifiable person"
    )
    payload = json.dumps({"model": "gpt-image-2", "prompt": prompt,
                          "size": CARD_SIZE, "n": 1}).encode()
    last = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                base.rstrip("/") + "/images/generations", data=payload,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read().decode())
            item = (body.get("data") or [{}])[0]
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"])
            url = item.get("url", "") or ""
            if url.startswith("https://"):   # 只信任 https，避免任意 URL 请求
                with urllib.request.urlopen(url, timeout=120) as r:
                    return r.read()
            raise RuntimeError(f"unexpected image response: {json.dumps(body)[:300]}")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            last = RuntimeError(f"HTTP {e.code}: {detail}")
            log(f"[imggen] attempt {attempt}/3 HTTP {e.code}: {detail}")
            if e.code != 429 and 400 <= e.code < 500:
                break  # 客户端错误(非限流)重试无意义
            ra = e.headers.get("Retry-After") if e.headers else None
            wait = int(ra) if (ra and ra.isdigit()) else min(20, 5 * 2 ** attempt)
            if attempt < 3:
                time.sleep(wait)
        except Exception as e:
            last = e
            log(f"[imggen] attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                time.sleep(min(20, 5 * attempt))
    raise RuntimeError(f"gpt-image-2 failed: {last}")


def compose(card_bytes, star, position, match, ruping, heavy, bold, out_path):
    from PIL import Image, ImageDraw, ImageFont
    import io

    def fh(sz): return ImageFont.truetype(heavy, sz)
    def fb(sz): return ImageFont.truetype(bold, sz)

    base = Image.open(io.BytesIO(card_bytes)).convert("RGBA")
    W, H = base.size
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def tw(t, f): return d.textlength(t, font=f)
    def center(t, f, y, fill):
        d.text(((W - tw(t, f)) / 2, y), t, font=f, fill=fill)
    def wrap(text, f, maxw, max_lines):
        lines, cur = [], ""
        for ch in text:
            if tw(cur + ch, f) <= maxw:
                cur += ch
            else:
                lines.append(cur); cur = ch
                if len(lines) == max_lines:
                    return lines  # 封顶，余下丢弃（已被 main 软截断兜底）
        if cur and len(lines) < max_lines:
            lines.append(cur)
        return lines
    def fit_font(text, factory, start, max_w, min_size=46):
        """在 max_w 宽度内自动缩放字号；缩到最小仍放不下则省略号截断。
        返回 (font, size, 实际要画的文本) —— 保证画出来不越界。"""
        sz = start
        f = factory(sz)
        while sz > min_size and tw(text, f) > max_w:
            sz -= 4
            f = factory(sz)
        if tw(text, f) <= max_w:
            return f, sz, text
        t = text
        while t and tw(t + "…", f) > max_w:
            t = t[:-1]
        return f, sz, (t + "…")

    # 顶部品牌标牌
    pf = fb(40); title = "KeleClaw 球探 · 球星撞型"; pw = tw(title, pf)
    d.rounded_rectangle([(W-pw)/2-44, 34, (W+pw)/2+44, 106], radius=36,
                        fill=(6, 16, 12, 215), outline=GOLD, width=3)
    center(title, pf, 48, GOLD)

    # 底部渐变信息面板
    ptop = int(H * 0.58)
    for y in range(ptop, H):
        a = int(238 * (y - ptop) / (H - ptop))
        d.line([0, y, W, y], fill=(4, 12, 9, min(a, 238)))

    MARGIN = 72
    x = MARGIN; y = ptop + 56
    d.text((x, y), "你的撞型球星", font=fb(34), fill=GRAY)
    y += 48

    # 右侧「撞型指数」块：靠右对齐到右边距，先排好以算出左边界给名字让位
    idx_lab_f, num_f, pct_f = fb(34), fh(104), fh(44)
    num_s = str(match)
    num_w, pct_w = tw(num_s, num_f), tw("%", pct_f)
    idx_w = max(tw("撞型指数", idx_lab_f), num_w + 6 + pct_w)
    idx_x = W - MARGIN - idx_w
    d.text((idx_x, y + 8),  "撞型指数", font=idx_lab_f, fill=GRAY)
    d.text((idx_x, y + 44), num_s, font=num_f, fill=GOLD, stroke_width=2, stroke_fill=(90, 60, 6))
    d.text((idx_x + num_w + 6, y + 100), "%", font=pct_f, fill=GOLD)

    # 球星名：在「左边距 → 指数块左侧」可用宽度内自动缩放，永不顶进指数区
    name_max_w = idx_x - x - 36
    name_f, name_sz, name_text = fit_font(star, fh, 118, name_max_w, min_size=46)
    d.text((x - 2, y), name_text, font=name_f, fill=WHITE, stroke_width=3, stroke_fill=(140, 96, 12))

    # 位置 chip：贴在名字实际底部下方（随字号自适应，不再写死偏移）
    name_bottom = y + int(name_sz * 1.18)
    cf = fb(36); cw = tw(position, cf)
    chip_top = name_bottom + 12
    d.rounded_rectangle([x, chip_top, x + cw + 48, chip_top + 62], radius=31, fill=GOLD)
    d.text((x + 24, chip_top + 9), position, font=cf, fill=INK)

    # 球探锐评（位置随 chip 底部走，避免和上方挤）
    ry = chip_top + 62 + 34
    d.text((x, ry), "★ 球探锐评", font=fb(40), fill=GOLD)
    d.line([x, ry + 58, W - MARGIN, ry + 58], fill=(247, 206, 88, 130), width=2)
    by = ry + 80; bf = fb(42)
    for ln in wrap(ruping, bf, W - 2 * MARGIN, RUPING_MAX_LINES):
        d.text((x, by), ln, font=bf, fill=WHITE, stroke_width=1, stroke_fill=(0, 0, 0))
        by += 60
    center("KeleClaw 球探  ·  AI 球星撞型锐评", fb(30), H - 78, GRAY)

    out = Image.alpha_composite(base, ov).convert("RGB")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out.save(out_path, "PNG")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--star", required=True)
    ap.add_argument("--position", required=True)
    ap.add_argument("--match", required=True, type=int)
    ap.add_argument("--features", required=True)
    ap.add_argument("--ruping", required=True)
    ap.add_argument("--tone", default="adult", choices=["adult", "minor"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("KELECLAW_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL") or os.environ.get("KELECLAW_BASE_URL")
    if not key or not base:
        log("ERROR: keleclaw credentials not in env (OPENAI_API_KEY/OPENAI_BASE_URL)")
        sys.exit(2)

    # 入参兜底：撞型指数 clamp、锐评软截断（防卡面越界）
    match = max(MATCH_MIN, min(MATCH_MAX, a.match))
    ruping = a.ruping.strip()
    if len(ruping) > RUPING_MAX_CHARS:
        ruping = ruping[:RUPING_MAX_CHARS - 1] + "…"

    out_path = a.out or os.path.join(CARD_DIR, f"card-{os.getpid()}-{int(time.time())}.png")
    heavy, bold = ensure_fonts()
    card_bytes = gen_card_art(a.features, a.tone, key, base)
    path = compose(card_bytes, a.star, a.position, match, ruping, heavy, bold, out_path)
    # 末行打印绝对路径，供 agent 输出 MEDIA:
    print(os.path.abspath(path))


if __name__ == "__main__":
    main()
