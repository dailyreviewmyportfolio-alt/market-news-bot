# 🌅 Morning Market Brief: Telegram / WhatsApp ಬಾಟ್

ಈ ಬಾಟ್ ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ~9:00ಕ್ಕೆ ನಿಮಗೆ ಒಂದು ಮೆಸೇಜ್ ಕಳಿಸುತ್ತೆ. ಅದರಲ್ಲಿ ಇರುವುದು:
- Nifty, Sensex, Bank Nifty
- US, Japan, Hong Kong markets, ಜೊತೆಗೆ Crude, Gold, USD/INR
- India ಮತ್ತು world market ಸುದ್ದಿ, "Stocks to watch"
- ನಿಮ್ಮ portfolio stocks ಬೆಲೆ ಮತ್ತು ಅವುಗಳ ಸುದ್ದಿ

ಖರ್ಚು: **₹0**. ಮೆಸೇಜ್ Telegram‌ಗೆ, WhatsApp‌ಗೆ, ಅಥವಾ ಎರಡಕ್ಕೂ ಬರಬಹುದು. ಯಾವುದರ secrets ಹಾಕಿದ್ದೀರೋ ಅದಕ್ಕೆ ಮಾತ್ರ ಬರುತ್ತೆ.

---

## ಹಂತ 1: Telegram bot ಮಾಡುವುದು (5 ನಿಮಿಷ)
1. Telegram‌ನಲ್ಲಿ **@BotFather** ಹುಡುಕಿ (ನೀಲಿ ✔️ ಇರೋದನ್ನೇ ಆರಿಸಿ). ನಂತರ **Start** ಒತ್ತಿ.
2. `/newbot` ಕಳಿಸಿ.
3. ಹೆಸರು ಕೇಳಿದಾಗ ಏನಾದರೂ ಕೊಡಿ, ಉದಾ: `Eshwar Market Brief`
4. Username ಕೇಳಿದಾಗ ಕೊನೆಯಲ್ಲಿ `bot` ಇರಬೇಕು, ಉದಾ: `eshwar_market_brief_bot`
5. BotFather ಒಂದು **token** ಕೊಡುತ್ತೆ (`123456789:AAH...` ತರಹ ಇರುತ್ತೆ). ಇದನ್ನು ಸೇವ್ ಮಾಡಿಕೊಳ್ಳಿ. **ಯಾರಿಗೂ ಕೊಡಬೇಡಿ.**
6. BotFather ಕೊಟ್ಟ ಲಿಂಕ್ ಒತ್ತಿ ನಿಮ್ಮ ಹೊಸ bot ತೆರೆಯಿರಿ. **Start** ಒತ್ತಿ. (ಇದು ಮಾಡದಿದ್ದರೆ bot ನಿಮಗೆ ಮೆಸೇಜ್ ಕಳಿಸೋಕೆ ಆಗಲ್ಲ!)

## ಹಂತ 2: ನಿಮ್ಮ Chat ID ಪಡೆಯುವುದು (1 ನಿಮಿಷ)
1. Telegram‌ನಲ್ಲಿ **@userinfobot** ಹುಡುಕಿ, **Start** ಒತ್ತಿ.
2. ಅದು `Id: 123456789` ತರಹ ಒಂದು ಸಂಖ್ಯೆ ಕೊಡುತ್ತೆ. ಅದೇ ನಿಮ್ಮ **Chat ID**. ಸೇವ್ ಮಾಡಿಕೊಳ್ಳಿ.

## ಹಂತ 3: GitHub‌ಗೆ ಹಾಕಿ (10 ನಿಮಿಷ)
1. https://github.com ನಲ್ಲಿ account ಮಾಡಿ (ಫ್ರೀ).
2. **New repository** ಒತ್ತಿ. ಹೆಸರು `market-news-bot` ಕೊಡಿ, **Private** ಆರಿಸಿ, ನಂತರ **Create** ಒತ್ತಿ.
3. **uploading an existing file** ಲಿಂಕ್ ಒತ್ತಿ. ಈ ಫೋಲ್ಡರ್‌ನ ಎಲ್ಲಾ ಫೈಲ್‌ಗಳನ್ನು drag ಮಾಡಿ ಹಾಕಿ:
   `market_brief.py`, `stocks.json`, `README.md`, ಮತ್ತು **`.github` ಫೋಲ್ಡರ್** (ಇದು ಮುಖ್ಯ!)
   ಕೊನೆಗೆ **Commit changes** ಒತ್ತಿ.
4. Repository‌ನಲ್ಲಿ **Settings → Secrets and variables → Actions → New repository secret** ಗೆ ಹೋಗಿ ಈ secrets ಸೇರಿಸಿ:
   | Name | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | ಹಂತ 1ರಲ್ಲಿ ಬಂದ token |
   | `TELEGRAM_CHAT_ID` | ಹಂತ 2ರಲ್ಲಿ ಬಂದ Id ಸಂಖ್ಯೆ |

## ಹಂತ 4: ಟೆಸ್ಟ್ ಮಾಡಿ
**Actions** ಟ್ಯಾಬ್‌ನಲ್ಲಿ **Morning Market Brief** ಆರಿಸಿ, **Run workflow** ಒತ್ತಿ.
1–2 ನಿಮಿಷದಲ್ಲಿ Telegram‌ಗೆ ಮೆಸೇಜ್ ಬರಬೇಕು ✅
ಇದು ಆದ ಮೇಲೆ ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ತಾನಾಗಿಯೇ ಬರುತ್ತೆ. ನಿಮ್ಮ PC ಆಫ್ ಇದ್ದರೂ ತೊಂದರೆ ಇಲ್ಲ.

---

## (ಬೇಕಿದ್ದರೆ) WhatsApp ಕೂಡ ಸೇರಿಸುವುದು
1. `+34 644 95 42 75` ನಂಬರ್ ಅನ್ನು contacts‌ಗೆ ಸೇರಿಸಿ. ಅದಕ್ಕೆ WhatsApp‌ನಲ್ಲಿ ಈ ಮೆಸೇಜ್ ಕಳಿಸಿ:
   `I allow callmebot to send me messages`
   (2 ನಿಮಿಷದಲ್ಲಿ key ಬರದಿದ್ದರೆ 24 ಗಂಟೆ ಬಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.)
2. ಬಂದ apikey ಬಳಸಿ ಈ ಎರಡು secrets ಸೇರಿಸಿ:
   `CALLMEBOT_PHONE` (ಉದಾ: `+919876543210`) ಮತ್ತು `CALLMEBOT_APIKEY`

## Stocks ಬದಲಾಯಿಸೋದು ಹೇಗೆ?
GitHub‌ನಲ್ಲಿ `stocks.json` ಫೈಲ್ ತೆರೆದು ✏️ (edit) ಒತ್ತಿ. ಒಂದು ಸಾಲು ಸೇರಿಸಿ ಅಥವಾ ತೆಗೆಯಿರಿ. ಉದಾಹರಣೆ:
```json
{"symbol": "TATAMOTORS", "keywords": ["Tata Motors"]},
```
- `symbol` ಅಂದರೆ NSE symbol (ಬೆಲೆ ತರೋಕೆ ಬಳಸುತ್ತೆ)
- `keywords` ಅಂದರೆ ಸುದ್ದಿಯಲ್ಲಿ ಕಂಪನಿ ಹೆಸರು ಹೇಗೆ ಬರುತ್ತೆ ಅದು (ಈ ಹೆಸರು ಇರುವ ಸುದ್ದಿ ಮಾತ್ರ ತೋರಿಸುತ್ತೆ)

## ಟೈಮ್ ಬದಲಾಯಿಸೋದು ಹೇಗೆ?
`.github/workflows/morning-brief.yml` ಫೈಲ್‌ನಲ್ಲಿ `cron: "15 3 * * *"` ಸಾಲು ಇದೆ. ಇದು UTC ಟೈಮ್ (IST − 5:30).
ಉದಾ: 8:00 AM IST ಬೇಕಾದರೆ `"30 2 * * *"` ಅಂತ ಬದಲಾಯಿಸಿ.

## ನಿಮ್ಮ PC‌ಯಲ್ಲೇ ಟೆಸ್ಟ್ ಮಾಡೋಕೆ (ಮೆಸೇಜ್ ಕಳಿಸದೆ)
```
python market_brief.py --dry-run
```
