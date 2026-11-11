"""Evening Reel uploader.

Eshwar sends the day's video to the Telegram bot (the video's caption becomes the Instagram caption).
At 7:00 PM IST on weekdays this script:
  1. finds the newest video he sent (Telegram getUpdates)
  2. downloads it (Telegram bots can only download files up to 20 MB)
  3. uploads it to Instagram as a Reel
  4. tells him on Telegram whether it worked

Run:  python reel_upload.py --wait      wait until 7:00 PM IST, look for the video until 7:15 PM, post it
      python reel_upload.py --now       look for the video and post it immediately
      python reel_upload.py --dry-run   only look for the video (nothing is downloaded or posted)
Uses the same secrets as market_brief.py: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IG_ACCESS_TOKEN, IG_USER_ID.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from market_brief import HERE, IST, UA, fetch, ig_call, tg_creds, tg_text

POST_AT = (19, 0)             # the Reel goes out at 7:00 PM IST
GIVE_UP_AT = (19, 15)         # stop waiting for the video at 7:15 PM IST
MAX_AGE_HOURS = 30            # ignore videos sent longer ago than this
TG_LIMIT = 20 * 1024 * 1024   # Telegram bot download limit
API = "https://graph.facebook.com/v27.0"
DEFAULT_CAPTION = ("Daily portfolio update 📈\n\n"
                   "Follow @portfolio.daily for daily updates 🔔\n"
                   "Full videos 👉 YouTube: DailyReviewMyPortfolio\n\n"
                   "⚠️ Not SEBI registered. Education purpose only.\n\n"
                   "#kannadastockmarket #sharemarketkannada #portfolioreview #swingtrading #kannadareels")


def now_ist():
    return dt.datetime.now(IST)


def at(hm):
    return now_ist().replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)


def scrub(text):
    """Never let a secret reach the Telegram chat or the logs."""
    for name in ("TELEGRAM_BOT_TOKEN", "IG_ACCESS_TOKEN"):
        secret = (os.environ.get(name) or "").strip()
        if secret:
            text = text.replace(secret, "***")
    return text


# ---------------------------------------------------------------- telegram
def tg_api(method, params=None):
    token, _ = tg_creds()
    data = urllib.parse.urlencode(params).encode() if params else None
    return json.loads(fetch(f"https://api.telegram.org/bot{token}/{method}", timeout=60, data=data))["result"]


def find_video():
    """Newest video Eshwar sent to the bot. Returns (video or None, last update id)."""
    chat = tg_creds()[1]
    found, last_id = None, None
    for u in tg_api("getUpdates", {"allowed_updates": json.dumps(["message"])}):
        last_id = max(last_id or 0, u["update_id"])
        m = u.get("message") or {}
        if str(m.get("chat", {}).get("id")) != chat:
            continue
        v = m.get("video") or m.get("document")
        if not v or not (m.get("video") or str(v.get("mime_type", "")).startswith("video/")):
            continue
        if time.time() - m["date"] > MAX_AGE_HOURS * 3600:
            continue
        found = {"file_id": v["file_id"], "size": v.get("file_size") or 0, "caption": m.get("caption") or ""}
    return found, last_id


def confirm(last_id):
    """Tell Telegram everything up to last_id is handled, so the video is never posted twice."""
    try:
        tg_api("getUpdates", {"offset": last_id + 1, "limit": 1})
    except Exception as e:
        print("could not confirm the Telegram updates:", scrub(str(e)))


def download(video):
    if video["size"] > TG_LIMIT:
        raise RuntimeError("the video is bigger than 20 MB (Telegram bot limit); send a smaller file")
    token, _ = tg_creds()
    info = tg_api("getFile", {"file_id": video["file_id"]})
    data = fetch(f"https://api.telegram.org/file/bot{token}/{info['file_path']}", timeout=180)
    os.makedirs(os.path.join(HERE, "reels"), exist_ok=True)
    path = os.path.join(HERE, "reels", f"{now_ist():%Y-%m-%d}.mp4")
    with open(path, "wb") as fh:
        fh.write(data)
    print(f"video downloaded: {len(data) / 1e6:.1f} MB")
    return path


# ---------------------------------------------------------------- instagram
def clean_caption(text):
    """Use his caption; keep only the first 5 hashtags (Instagram drops the # of the rest)."""
    text = (text or "").strip() or DEFAULT_CAPTION
    seen = 0

    def keep(m):
        nonlocal seen
        seen += 1
        return m.group(0) if seen <= 5 else ""
    return re.sub(r"#\w+", keep, text)[:2200].rstrip()


def instagram_target():
    token = (os.environ.get("IG_ACCESS_TOKEN") or "").strip()
    ig_id = (os.environ.get("IG_USER_ID") or "").strip()
    if not token or not ig_id:
        raise RuntimeError("IG_ACCESS_TOKEN / IG_USER_ID secrets are missing")
    return token, ig_id


def wait_container(cid, token):
    for _ in range(60):  # up to 5 minutes
        st = ig_call(cid, {"fields": "status_code", "access_token": token}, post=False, api=API)
        code = st.get("status_code")
        print("instagram video status:", code)
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram could not process the video (status {code})")
        time.sleep(5)
    raise RuntimeError("Instagram is still processing the video after 5 minutes")


def upload_resumable(ig_id, token, path, caption):
    """Send the file bytes straight to Instagram (no public link needed)."""
    c = ig_call(f"{ig_id}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": caption,
                                   "share_to_feed": "true", "access_token": token}, api=API)
    cid = c["id"]
    uri = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v27.0/{cid}"
    with open(path, "rb") as fh:
        body = fh.read()
    req = urllib.request.Request(uri, data=body, method="POST", headers=dict(UA, **{
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(body))}))
    try:
        urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"upload rejected: {e} {e.read()[:300]!r}") from None
    return cid


def upload_via_repo_url(ig_id, token, path, caption):
    """Fallback: put the video in the public repo for a minute so Instagram can fetch it by URL."""
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    rel = "reels/" + os.path.basename(path)

    def git(*a):
        subprocess.run(["git", *a], cwd=HERE, check=True, capture_output=True, text=True)
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("add", "-f", rel)
    git("commit", "-m", f"Reel video {os.path.basename(path)}")
    git("pull", "--rebase", "origin", branch)
    git("push")
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{rel}"
    try:
        for _ in range(12):  # wait until GitHub serves the pushed file
            try:
                fetch(url, timeout=20, headers=dict(UA, Range="bytes=0-0"))
                break
            except Exception:
                time.sleep(5)
        cid = ig_call(f"{ig_id}/media", {"media_type": "REELS", "video_url": url, "caption": caption,
                                         "share_to_feed": "true", "access_token": token}, api=API)["id"]
        wait_container(cid, token)  # Instagram has fetched the file once this finishes
        return cid
    finally:
        try:
            git("rm", "-q", rel)
            git("commit", "-m", "Remove posted Reel video")
            git("pull", "--rebase", "origin", branch)
            git("push")
        except Exception as e:
            print("could not remove the video from the repo:", scrub(str(e)))


def post_reel(path, caption):
    token, ig_id = instagram_target()
    try:
        cid = upload_resumable(ig_id, token, path, caption)
    except Exception as e:
        print("direct upload failed:", scrub(str(e)))
        if not os.environ.get("GITHUB_ACTIONS"):
            raise
        print("trying the public-link fallback")
        cid = upload_via_repo_url(ig_id, token, path, caption)
    wait_container(cid, token)
    return ig_call(f"{ig_id}/media_publish", {"creation_id": cid, "access_token": token}, api=API)["id"]


# ---------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    wait_mode = "--wait" in args
    if not tg_creds()[0]:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set.")
        return 1
    if wait_mode and now_ist().weekday() >= 5:
        print("Weekend - no Reel today.")
        return 0
    if wait_mode:
        delay = (at(POST_AT) - now_ist()).total_seconds()
        if delay > 0:
            print(f"waiting {delay / 60:.0f} minutes until 7:00 PM IST")
            time.sleep(delay)

    video, last_id = find_video()
    polled = False
    while not video and wait_mode and now_ist() < at(GIVE_UP_AT):
        polled = True
        time.sleep(120)
        video, last_id = find_video()
    if "--dry-run" in args:
        print("video found:" if video else "no video found", video or "")
        return 0
    if not video:
        print("no video from Eshwar - nothing to post")
        if polled or not wait_mode:  # only the run that actually waited sends the reminder
            tg_text("⚠️ ಇವತ್ತಿನ ವಿಡಿಯೋ ಬಂದಿಲ್ಲ, ಹಾಗಾಗಿ Instagram Reel ಪೋಸ್ಟ್ ಮಾಡಿಲ್ಲ.\n"
                    "ಮಾರುಕಟ್ಟೆ ರಜೆ ಆಗಿದ್ದರೆ ಇದನ್ನು ನಿರ್ಲಕ್ಷಿಸಿ.", html_mode=False)
        return 0

    try:
        path = download(video)
        media_id = post_reel(path, clean_caption(video["caption"]))
    except Exception as e:
        msg = scrub(str(e))
        print("Reel FAILED:", msg)
        tg_text(f"⚠️ Instagram Reel ಪೋಸ್ಟ್ ಆಗಲಿಲ್ಲ: {msg}\nದಯವಿಟ್ಟು ಕೈಯಾರೆ ಪೋಸ್ಟ್ ಮಾಡಿ.", html_mode=False)
        return 1
    confirm(last_id)  # right after publishing, so a rerun can never post it twice
    print("reel published:", media_id)
    link = ""
    try:
        token, _ = instagram_target()
        link = ig_call(media_id, {"fields": "permalink", "access_token": token}, post=False, api=API).get("permalink", "")
    except Exception:
        pass
    tg_text(f"✅ Instagram Reel ಪೋಸ್ಟ್ ಆಯ್ತು! 🎬 {link}".strip(), html_mode=False)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
