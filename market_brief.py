"""Morning Market Brief -> Telegram and/or WhatsApp (via CallMeBot).

Free sources only: Google News RSS (headlines) + Yahoo Finance (prices).
Run:  python market_brief.py            (sends if CALLMEBOT_* env vars are set)
      python market_brief.py --dry-run  (only prints the message)
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
UA = {"User-Agent": "Mozilla/5.0 (MorningMarketBrief)"}
MAX_CHUNK = 1500  # keep each WhatsApp message short enough for CallMeBot
# quote/listing pages that are not real news
JUNK = re.compile(r"share price( today|, stock price| live|$)|stock price today", re.I)

INDICES = [
    ("Nifty 50", "^NSEI"), ("Sensex", "^BSESN"), ("Bank Nifty", "^NSEBANK"),
]
WORLD = [
    ("Dow", "^DJI"), ("S&P 500", "^GSPC"), ("Nasdaq", "^IXIC"),
    ("Nikkei", "^N225"), ("Hang Seng", "^HSI"),
]
OTHERS = [
    ("Brent crude", "BZ=F"), ("Gold", "GC=F"), ("USD/INR", "INR=X"),
]


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------- prices ----------
def quote(ticker):
    """Return (last, pct_change) using the last two daily closes, or None."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(ticker) + "?range=5d&interval=1d")
    try:
        data = json.loads(fetch(url))
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            return None
        last, prev = closes[-1], closes[-2]
        return last, (last - prev) / prev * 100
    except Exception:
        return None


def fmt_quote(label, ticker):
    q = quote(ticker)
    if not q:
        return f"• {label}: n/a"
    last, pct = q
    arrow = "🟢" if pct >= 0 else "🔴"
    return f"{arrow} {label}: {last:,.2f} ({pct:+.2f}%)"


# ---------- headlines ----------
def headlines(query, n, hours=24, seen=None, must_match=None):
    """Recent Google News headlines. must_match: regex the headline must contain."""
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
        headline = title.rsplit(" - ", 1)[0]
        key = headline.lower()[:80]
        if len(headline.strip(" -")) < 20 or key in seen:
            continue
        if must_match and not re.search(must_match, headline, re.I):
            continue
        if JUNK.search(headline):
            continue
        seen.add(key)
        out.append(title)
        if len(out) >= n:
            break
    return out


# ---------- message ----------
def build_message():
    stocks = json.load(open(os.path.join(HERE, "stocks.json"), encoding="utf-8"))
    today = dt.datetime.now(IST).strftime("%a, %d %b %Y")
    seen = set()
    L = [f"🌅 *Morning Market Brief*", f"_{today}_", ""]

    L.append("*🇮🇳 INDIA (last close)*")
    L += [fmt_quote(a, b) for a, b in INDICES]
    L.append("")
    L.append("*🌍 WORLD*")
    L += [fmt_quote(a, b) for a, b in WORLD]
    L += [fmt_quote(a, b) for a, b in OTHERS]
    L.append("")

    L.append("*📰 India market news*")
    L += [f"• {h}" for h in headlines("Sensex Nifty stock market", 5, seen=seen)]
    L.append("")
    L.append("*👀 Stocks to watch today*")
    L += [f"• {h}" for h in headlines('"stocks to watch"', 3, seen=seen)]
    L.append("")
    L.append("*🌐 Global market news*")
    L += [f"• {h}" for h in headlines("Wall Street OR global markets stocks", 4, seen=seen)]
    L.append("")

    L.append("*💼 MY PORTFOLIO*")
    quiet = []
    for s in stocks:
        q = quote(s["symbol"] + ".NS")
        price = ""
        if q:
            price = f" ₹{q[0]:,.1f} ({q[1]:+.2f}%)"
        kws = s["keywords"]
        query = " OR ".join(f'"{k}"' for k in kws) + " share"
        pattern = "|".join(r"\b" + re.escape(k) + r"\b" for k in kws)
        news = headlines(query, 2, seen=seen, must_match=pattern)
        if news:
            L.append(f"*{s['symbol']}*{price}")
            L += [f"  • {h}" for h in news]
        else:
            quiet.append(f"{s['symbol']}{price}")
        time.sleep(0.5)
    if quiet:
        L.append("")
        L.append("_No news:_ " + " | ".join(quiet))
    return "\n".join(L)


def split_chunks(text, limit=MAX_CHUNK):
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit and cur:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks


def to_telegram_html(text):
    """Turn the WhatsApp-style *bold* / _italic_ markers into Telegram HTML."""
    t = html.escape(text, quote=False)
    t = re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"<i>\1</i>", t)
    return t


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return None  # not configured
    token, chat = token.strip(), chat.strip()
    try:  # show which bot/chat is used (safe: no secret values)
        me = json.loads(fetch(f"https://api.telegram.org/bot{token}/getMe"))["result"]
        print(f"telegram: bot @{me['username']}, chat id ends with ...{chat[-3:]} ({len(chat)} digits)")
    except Exception as e:
        print(f"telegram: token check failed: {e}")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ok = True
    for i, chunk in enumerate(split_chunks(text, 3800)):
        for parse_mode in ("HTML", None):  # fall back to plain text if HTML fails
            body = {"chat_id": chat, "disable_web_page_preview": "true",
                    "text": to_telegram_html(chunk) if parse_mode else chunk}
            if parse_mode:
                body["parse_mode"] = parse_mode
            req = urllib.request.Request(
                url, data=urllib.parse.urlencode(body).encode(), headers=UA)
            try:
                with urllib.request.urlopen(req, timeout=30):
                    pass
                print(f"telegram part {i + 1}: sent")
                break
            except Exception as e:
                detail = ""
                if hasattr(e, "read"):  # Telegram explains the error in the body
                    try:
                        detail = json.loads(e.read()).get("description", "")
                    except Exception:
                        pass
                print(f"telegram part {i + 1} ({parse_mode or 'plain'}): FAILED {e} {detail}")
                if getattr(e, "code", None) in (401, 403, 404):
                    return False  # token/chat problem: retrying won't help
        else:
            ok = False
    return ok


def send_whatsapp(text):
    phone = os.environ.get("CALLMEBOT_PHONE")
    key = os.environ.get("CALLMEBOT_APIKEY")
    if not phone or not key:
        return None  # not configured
    ok = True
    for i, chunk in enumerate(split_chunks(text)):
        url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
            {"phone": phone, "text": chunk, "apikey": key})
        try:
            resp = fetch(url, timeout=30).decode("utf-8", "ignore")
            print(f"part {i + 1}: sent ({resp[:80].strip()!r})")
        except Exception as e:
            ok = False
            print(f"part {i + 1}: FAILED {e}")
        time.sleep(5)  # CallMeBot rate limit
    return ok


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    msg = build_message()
    print(msg)
    print(f"\n--- {len(msg)} chars, {len(split_chunks(msg))} WhatsApp message(s) ---")
    if "--dry-run" not in sys.argv:
        results = [r for r in (send_telegram(msg), send_whatsapp(msg)) if r is not None]
        if not results:
            print("No channel configured: set TELEGRAM_* and/or CALLMEBOT_* secrets.")
        sys.exit(0 if results and all(results) else 1)
