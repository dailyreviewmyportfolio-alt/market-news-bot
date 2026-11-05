# 🌅 Morning Market Brief

ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ~8:50–9:05ಕ್ಕೆ ಈ ಬಾಟ್ ತಾನಾಗಿಯೇ ಓಡುತ್ತೆ:
1. **Telegram**‌ಗೆ ಪೂರ್ತಿ brief ಕಳಿಸುತ್ತೆ: Nifty, Sensex, Bank Nifty, **FII/DII**, world markets, Crude/Gold/USD-INR, ಮತ್ತು ಸುದ್ದಿ
2. **Instagram story image** (1080×1920) ಮಾಡಿ Telegram‌ಗೆ ಕಳಿಸುತ್ತೆ, ಮತ್ತು **Instagram‌ಗೆ ತಾನಾಗಿಯೇ story ಹಾಕುತ್ತೆ**
3. **YouTube Community post** text ರೆಡಿ ಮಾಡಿ Telegram‌ಗೆ ಕಳಿಸುತ್ತೆ. YouTube auto-post ಸಾಧ್ಯವಿಲ್ಲ, ಹಾಗಾಗಿ ಇದನ್ನು ನೀವೇ copy-paste ಮಾಡಬೇಕು.

ಖರ್ಚು: ₹0. ಎಲ್ಲವೂ GitHub Actions‌ನಲ್ಲಿ ಓಡುತ್ತೆ, ನಿಮ್ಮ PC ಆನ್ ಇರಬೇಕಾಗಿಲ್ಲ.

## GitHub secrets
| Name | ಏನು |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather ಕೊಟ್ಟ token |
| `TELEGRAM_CHAT_ID` | ನಿಮ್ಮ Telegram ID |
| `IG_ACCESS_TOKEN` | Meta App Dashboard‌ನ **Generate token** ಬಟನ್‌ನಿಂದ ಬಂದ Instagram token |
| `CALLMEBOT_PHONE`, `CALLMEBOT_APIKEY` | (ಬೇಕಿದ್ದರೆ) WhatsApp |

## ಗಮನಿಸಿ
- Instagram‌ಗೆ image ಒಂದು **public link**‌ನಲ್ಲಿ ಇರಬೇಕು. ಅದಕ್ಕೇ ಈ repo **Public** ಆಗಿರಬೇಕು. ಕೊನೆಯ 7 ದಿನಗಳ image ಮಾತ್ರ `stories/` ಫೋಲ್ಡರ್‌ನಲ್ಲಿ ಉಳಿಯುತ್ತೆ. Secrets ಯಾವಾಗಲೂ ರಹಸ್ಯವಾಗಿಯೇ ಇರುತ್ತೆ.
- Instagram token **60 ದಿನ** valid ಇರುತ್ತೆ. ಬಾಟ್ ಅದನ್ನು ಪ್ರತಿದಿನ refresh ಮಾಡಲು ಪ್ರಯತ್ನಿಸುತ್ತೆ. Story post ಆಗದಿದ್ದರೆ Telegram‌ಗೆ ⚠️ ಮೆಸೇಜ್ ಬರುತ್ತೆ. ಆಗ Meta dashboard‌ನಲ್ಲಿ ಹೊಸ token generate ಮಾಡಿ `IG_ACCESS_TOKEN` ಬದಲಾಯಿಸಿ (2 ನಿಮಿಷದ ಕೆಲಸ).
- ಟೈಮ್ ಬದಲಾಯಿಸಬೇಕಾದರೆ `.github/workflows/morning-brief.yml` ನಲ್ಲಿರುವ `cron: "15 3 * * *"` ಬದಲಾಯಿಸಿ. ಇದು UTC ಟೈಮ್ (IST − 5:30).

## PC‌ಯಲ್ಲಿ ಟೆಸ್ಟ್ (ಏನನ್ನೂ ಕಳಿಸದೆ)
```
pip install pillow
python market_brief.py --dry-run
```
Image `stories/` ಫೋಲ್ಡರ್‌ನಲ್ಲಿ ಸೇವ್ ಆಗುತ್ತೆ.
