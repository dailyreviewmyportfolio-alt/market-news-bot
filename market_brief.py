"""Morning Market Brief.

Every morning:
  1. collects index prices, FII/DII cash data and market headlines
  2. sends the full brief to Telegram (and WhatsApp if configured)
  3. makes an Instagram story image + a YouTube Community post text and sends both to Telegram
  4. (separate step, --publish-ig) publishes the story image to Instagram

Run:  python market_brief.py              build + send
      python market_brief.py --dry-run    build only (prints text, saves image)
      python market_brief.py --publish-ig publish today's story image to Instagram
Free sources only: Google News RSS (headlines), Yahoo Finance (prices), NSE (FII/DII).
"""
import datetime as dt
import email.utils
import html
import http.cookiejar
import json
import os
import re
import sys
import textwrap
import time
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
TODAY = dt.datetime.now(IST)
UA = {"User-Agent": "Mozilla/5.0 (MorningMarketBrief)"}
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
CHANNEL = "@DailyReviewMyPortfolio"
STORY_PATH = f"stories/brief-{TODAY:%Y-%m-%d}.jpg"
IG_API = "https://graph.instagram.com/v27.0"
# quote/listing pages that are not real news
JUNK = re.compile(r"share price( today|, stock price| live|$)|stock price today", re.I)

INDIA = [("Nifty 50", "^NSEI"), ("Sensex", "^BSESN"), ("Bank Nifty", "^NSEBANK")]
WORLD = [("Dow", "^DJI"), ("S&P 500", "^GSPC"), ("Nasdaq", "^IXIC"),
         ("Nikkei", "^N225"), ("Hang Seng", "^HSI")]
OTHERS = [("Brent", "BZ=F"), ("Gold", "GC=F"), ("USD/INR", "INR=X")]


def fetch(url, timeout=20, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------- data
def quote(ticker):
    """(last, pct_change) from the last two daily closes, or None."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(ticker) + "?range=5d&interval=1d")
    try:
        data = json.loads(fetch(url))
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            return None
        return closes[-1], (closes[-1] - closes[-2]) / closes[-2] * 100
    except Exception:
        return None


def fii_dii():
    """Latest FII/DII cash-market net values from NSE, or None."""
    h = {"User-Agent": BROWSER_UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
         "Referer": "https://www.nseindia.com/reports/fii-dii"}
    try:
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        opener.open(urllib.request.Request("https://www.nseindia.com/reports/fii-dii",
                                           headers=h), timeout=20).read()
        rows = json.loads(opener.open(urllib.request.Request(
            "https://www.nseindia.com/api/fiidiiTradeReact", headers=h), timeout=20).read())
        out = {"date": rows[0]["date"]}
        for r in rows:
            out["FII" if r["category"].upper().startswith("FII") else "DII"] = float(r["netValue"])
        return out if "FII" in out and "DII" in out else None
    except Exception as e:
        print("FII/DII fetch failed:", e)
        return None


def headlines(query, n, hours=24, seen=None):
    """Recent Google News headlines as (headline, source)."""
    seen = seen if seen is not None else set()
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{query} when:1d", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    try:
        root = ET.fromstring(fetch(url))
    except Exception:
        return []
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        pub = item.findtext("pubDate")
        try:
            if pub and email.utils.parsedate_to_datetime(pub) < cutoff:
                continue
        except Exception:
            pass
        head, _, source = title.rpartition(" - ")
        head = (head or title).strip()
        key = head.lower()[:80]
        if len(head) < 20 or key in seen or JUNK.search(head):
            continue
        seen.add(key)
        out.append((head, source.strip()))
        if len(out) >= n:
            break
    return out


def gather():
    seen = set()
    return {
        "india": [(a, quote(b)) for a, b in INDIA],
        "world": [(a, quote(b)) for a, b in WORLD],
        "others": [(a, quote(b)) for a, b in OTHERS],
        "fii": fii_dii(),
        "india_news": headlines("Sensex Nifty stock market", 5, seen=seen),
        "watch": headlines('"stocks to watch"', 3, seen=seen),
        "global_news": headlines("Wall Street OR global markets stocks", 4, seen=seen),
    }


# ---------------------------------------------------------------- text
def dot(pct):
    return "🟢" if pct >= 0 else "🔴"


def crore(v):
    return ("+" if v >= 0 else "-") + f"₹{abs(v):,.0f} Cr"


def line(label, q, money=""):
    if not q:
        return f"• {label}: n/a"
    return f"{dot(q[1])} {label}: {money}{q[0]:,.2f} ({q[1]:+.2f}%)"


def render_brief(d):
    L = ["🌅 *Morning Market Brief*", f"_{TODAY:%a, %d %b %Y}_", "",
         "*🇮🇳 INDIA (last close)*"]
    L += [line(a, q) for a, q in d["india"]]
    if d["fii"]:
        f = d["fii"]
        L += ["", f"*💰 FII / DII cash ({f['date']})*",
              f"{dot(f['FII'])} FII: {crore(f['FII'])}",
              f"{dot(f['DII'])} DII: {crore(f['DII'])}"]
    L += ["", "*🌍 WORLD*"] + [line(a, q) for a, q in d["world"] + d["others"]]
    for title, key in (("📰 India market news", "india_news"),
                       ("👀 Stocks to watch today", "watch"),
                       ("🌐 Global market news", "global_news")):
        if d[key]:
            L += ["", f"*{title}*"] + [f"• {h} - {s}" if s else f"• {h}" for h, s in d[key]]
    return "\n".join(L)


def render_community(d):
    """Plain text ready to paste into a YouTube Community post."""
    L = [f"🌅 Morning Market Brief | {TODAY:%d %b %Y}", ""]
    for a, q in d["india"]:
        if q:
            L.append(f"{dot(q[1])} {a}: {q[0]:,.0f} ({q[1]:+.2f}%)")
    if d["fii"]:
        f = d["fii"]
        L.append(f"💰 FII: {crore(f['FII'])} | DII: {crore(f['DII'])} ({f['date']})")
    world = [f"{a} {q[1]:+.2f}%" for a, q in d["world"] if q]
    if world:
        L.append("🌍 " + " | ".join(world))
    news = (d["india_news"][:2] + d["global_news"][:1]) or d["watch"][:3]
    if news:
        L += ["", "📰 Top news:"] + [f"• {h}" for h, _ in news]
    L += ["", "Which stock are you watching today? Comment below 👇",
          "⚠️ Not investment advice. For education only.",
          "#StockMarket #Nifty #Sensex"]
    return "\n".join(L)


# ---------------------------------------------------------------- story image
FONTS = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"],
    "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
}
BG_TOP, BG_BOTTOM = (11, 18, 32), (17, 24, 39)
CARD, MUTED, WHITE = (30, 41, 59), (148, 163, 184), (241, 245, 249)
GREEN, RED, ACCENT = (34, 197, 94), (239, 68, 68), (250, 204, 21)


def render_story(d, path):
    from PIL import Image, ImageDraw, ImageFont

    def font(kind, size):
        for p in FONTS[kind]:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default(size)

    W, H, M = 1080, 1920, 70
    img = Image.new("RGB", (W, H))
    dr = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient
        t = y / H
        dr.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))

    f_title, f_date = font("bold", 66), font("regular", 38)
    f_head, f_row, f_val = font("bold", 34), font("regular", 38), font("bold", 38)
    f_news, f_foot = font("regular", 33), font("bold", 34)

    y = 230
    dr.rectangle([M, y, M + 120, y + 10], fill=ACCENT)
    y += 30
    dr.text((M, y), "MORNING MARKET BRIEF", font=f_title, fill=WHITE)
    y += 85
    dr.text((M, y), TODAY.strftime("%A, %d %B %Y"), font=f_date, fill=MUTED)
    y += 75

    def card(title, rows_h):
        nonlocal y
        top = y
        dr.rounded_rectangle([M - 20, top, W - M + 20, top + 62 + rows_h + 18], radius=28, fill=CARD)
        dr.text((M + 10, top + 18), title, font=f_head, fill=ACCENT)
        y = top + 62 + rows_h + 18 + 22
        return top + 72

    def right(text, x_right, yy, fnt, fill):
        dr.text((x_right - dr.textlength(text, font=fnt), yy), text, font=fnt, fill=fill)

    # India
    ry = card("INDIA  (last close)", 3 * 58)
    for label, q in d["india"]:
        dr.text((M + 10, ry), label, font=f_row, fill=WHITE)
        if q:
            right(f"{q[0]:,.0f}   {q[1]:+.2f}%", W - M - 10, ry, f_val, GREEN if q[1] >= 0 else RED)
        ry += 58

    # FII / DII
    if d["fii"]:
        f = d["fii"]
        ry = card(f"FII / DII CASH  ({f['date']})", 2 * 58)
        for k in ("FII", "DII"):
            v = f[k]
            dr.text((M + 10, ry), k, font=f_row, fill=WHITE)
            right(("+" if v >= 0 else "-") + f"Rs {abs(v):,.0f} Cr", W - M - 10, ry, f_val,
                  GREEN if v >= 0 else RED)
            ry += 58

    # Global, two columns
    items = [(a, q, None) for a, q in d["world"]]
    items += [(a, q, f"{q[0]:,.1f}" if q else None) for a, q in d["others"]]
    rows = (len(items) + 1) // 2
    ry = card("GLOBAL  &  COMMODITIES", rows * 58)
    colw = (W - 2 * M) // 2
    for i, (label, q, val) in enumerate(items):
        x = M + 10 + (i % 2) * colw
        yy = ry + (i // 2) * 58
        dr.text((x, yy), label, font=f_row, fill=MUTED)
        if q:
            txt = f"{val}  {q[1]:+.1f}%" if val else f"{q[1]:+.2f}%"
            right(txt, x + colw - 40, yy, f_val, GREEN if q[1] >= 0 else RED)

    # Top news
    news = (d["india_news"][:2] + d["global_news"][:1]) or d["watch"][:3]
    if news:
        wrapped = []
        for h, _ in news[:3]:
            lines = textwrap.wrap(h, 52)[:2]
            if len(textwrap.wrap(h, 52)) > 2:
                lines[-1] = lines[-1].rstrip(".,") + "..."
            wrapped.append(lines)
        ry = card("TOP NEWS", sum(len(w) * 44 + 18 for w in wrapped))
        for lines in wrapped:
            dr.ellipse([M + 12, ry + 14, M + 24, ry + 26], fill=ACCENT)
            for ln in lines:
                dr.text((M + 42, ry), ln, font=f_news, fill=WHITE)
                ry += 44
            ry += 18

    # Footer
    y = max(y, 1650)
    dr.text((M, y), CHANNEL, font=f_foot, fill=WHITE)
    dr.text((M, y + 48), "Not investment advice. For education only.", font=f_news, fill=MUTED)

    os.makedirs(os.path.dirname(os.path.join(HERE, path)), exist_ok=True)
    img.save(os.path.join(HERE, path), "JPEG", quality=90)
    return os.path.join(HERE, path)


# ---------------------------------------------------------------- telegram
def split_chunks(text, limit):
    chunks, cur = [], ""
    for ln in text.split("\n"):
        if len(cur) + len(ln) + 1 > limit and cur:
            chunks.append(cur)
            cur = ""
        cur += ln + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks


def to_telegram_html(text):
    """Turn the WhatsApp-style *bold* / _italic_ markers into Telegram HTML."""
    t = html.escape(text, quote=False)
    t = re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"<i>\1</i>", t)
    return t


def tg_creds():
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    return (token, chat) if token and chat else (None, None)


def tg_call(method, fields, photo_path=None):
    """Call the Telegram Bot API. Returns (ok, error_text)."""
    token, _ = tg_creds()
    url = f"https://api.telegram.org/bot{token}/{method}"
    if photo_path:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        with open(photo_path, "rb") as fh:
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; '
                          f'filename="story.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode()
                         + fh.read() + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers = dict(UA, **{"Content-Type": f"multipart/form-data; boundary={boundary}"})
    else:
        data = urllib.parse.urlencode(fields).encode()
        headers = UA
    try:
        fetch(url, timeout=60, data=data, headers=headers)
        return True, ""
    except Exception as e:
        detail = ""
        if hasattr(e, "read"):
            try:
                detail = json.loads(e.read()).get("description", "")
            except Exception:
                pass
        return False, f"{e} {detail}".strip()


def tg_text(text, html_mode=True):
    _, chat = tg_creds()
    ok_all = True
    for i, chunk in enumerate(split_chunks(text, 3800)):
        fields = {"chat_id": chat, "disable_web_page_preview": "true",
                  "text": to_telegram_html(chunk) if html_mode else chunk}
        if html_mode:
            fields["parse_mode"] = "HTML"
        ok, err = tg_call("sendMessage", fields)
        if not ok and html_mode:  # retry as plain text
            fields = {"chat_id": chat, "disable_web_page_preview": "true", "text": chunk}
            ok, err = tg_call("sendMessage", fields)
        print(f"telegram message part {i + 1}: {'sent' if ok else 'FAILED ' + err}")
        ok_all &= ok
    return ok_all


def send_telegram(brief, community, story_file):
    token, chat = tg_creds()
    if not token:
        return None  # not configured
    try:
        me = json.loads(fetch(f"https://api.telegram.org/bot{token}/getMe"))["result"]
        print(f"telegram: bot @{me['username']}, chat id ends with ...{chat[-3:]} ({len(chat)} digits)")
    except Exception as e:
        print(f"telegram: token check failed: {e}")
    ok = tg_text(brief)
    if story_file:
        sent, err = tg_call("sendPhoto", {"chat_id": chat, "caption": "📸 Instagram story for today"},
                            photo_path=story_file)
        print("telegram story image:", "sent" if sent else "FAILED " + err)
        ok &= sent
    ok &= tg_text("👇 YouTube Community post (copy and paste the next message)", html_mode=False)
    ok &= tg_text(community, html_mode=False)
    return ok


# ---------------------------------------------------------------- whatsapp
def send_whatsapp(text):
    phone = (os.environ.get("CALLMEBOT_PHONE") or "").strip()
    key = (os.environ.get("CALLMEBOT_APIKEY") or "").strip()
    if not phone or not key:
        return None  # not configured
    ok = True
    for i, chunk in enumerate(split_chunks(text, 1500)):
        url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
            {"phone": phone, "text": chunk, "apikey": key})
        try:
            fetch(url, timeout=30)
            print(f"whatsapp part {i + 1}: sent")
        except Exception as e:
            ok = False
            print(f"whatsapp part {i + 1}: FAILED {e}")
        time.sleep(5)  # CallMeBot rate limit
    return ok


# ---------------------------------------------------------------- instagram
def ig_call(path, params, post=True, api=IG_API):
    data = urllib.parse.urlencode(params).encode() if post else None
    url = f"{api}/{path}" if post else f"{api}/{path}?{urllib.parse.urlencode(params)}"
    try:
        return json.loads(fetch(url, timeout=60, data=data))
    except Exception as e:
        body = {}
        if hasattr(e, "read"):
            try:
                body = json.loads(e.read())
            except Exception:
                pass
        msg = (body.get("error") or {}).get("message") or str(e)
        raise RuntimeError(msg) from None


def publish_instagram():
    token = (os.environ.get("IG_ACCESS_TOKEN") or "").strip()
    if not token:
        print("IG_ACCESS_TOKEN not set - skipping Instagram.")
        return None
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    image_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{STORY_PATH}"
    fb_ig_id = (os.environ.get("IG_USER_ID") or "").strip()
    # Facebook-login setup (Page token + IG_USER_ID) uses graph.facebook.com
    api = "https://graph.facebook.com/v27.0" if fb_ig_id else IG_API
    try:
        if fb_ig_id:
            ig_id = fb_ig_id
            print(f"instagram account id ...{ig_id[-4:]} (Facebook login, page token)")
        else:
            # keep the 60-day Instagram-login token alive (failures are harmless)
            try:
                r = json.loads(fetch("https://graph.instagram.com/refresh_access_token?"
                                     + urllib.parse.urlencode({"grant_type": "ig_refresh_token",
                                                               "access_token": token})))
                print(f"instagram token refreshed: valid ~{int(r.get('expires_in', 0)) // 86400} more days")
            except Exception as e:
                print("instagram token refresh skipped:", e)
            me = ig_call("me", {"fields": "user_id,username", "access_token": token}, post=False)
            me = (me.get("data") or [me])[0]
            ig_id = me["user_id"]
            print(f"instagram account: @{me.get('username')}")

        for _ in range(12):  # wait until GitHub serves the freshly pushed image
            try:
                fetch(image_url, timeout=20)
                break
            except Exception:
                time.sleep(5)

        container = ig_call(f"{ig_id}/media", {"image_url": image_url, "media_type": "STORIES",
                                               "access_token": token}, api=api)["id"]
        for _ in range(10):
            st = ig_call(container, {"fields": "status_code", "access_token": token}, post=False, api=api)
            if st.get("status_code") in ("FINISHED", None):
                break
            if st.get("status_code") in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container status {st.get('status_code')}")
            time.sleep(6)
        media = ig_call(f"{ig_id}/media_publish", {"creation_id": container, "access_token": token}, api=api)
        print("instagram story published:", media.get("id"))
        if tg_creds()[0]:
            tg_text("✅ Instagram story posted automatically.", html_mode=False)
        return True
    except Exception as e:
        print("instagram FAILED:", e)
        if tg_creds()[0]:
            tg_text(f"⚠️ Instagram story was NOT posted: {e}\nPlease post today's story image manually.",
                    html_mode=False)
        return False


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if "--publish-ig" in sys.argv:
        sys.exit(0 if publish_instagram() is not False else 1)

    data = gather()
    brief, community = render_brief(data), render_community(data)
    story = None
    try:
        story = render_story(data, STORY_PATH)
        print("story image saved:", story)
    except Exception as e:
        print("story image FAILED:", e)
    print(brief, "\n\n----- community post -----\n" + community)

    if "--dry-run" not in sys.argv:
        results = [r for r in (send_telegram(brief, community, story), send_whatsapp(brief))
                   if r is not None]
        if not results:
            print("No channel configured: set TELEGRAM_* and/or CALLMEBOT_* secrets.")
        sys.exit(0 if results and all(results) else 1)
