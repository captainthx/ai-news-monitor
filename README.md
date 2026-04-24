# 📈 AI Stock News Monitor

Automated daily stock news analysis powered by **Gemini 2.5 Flash**, delivered straight to **Telegram** — running entirely on **GitHub Actions** (zero infrastructure).

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  yfinance    │────▶│  Gemini 2.5  │────▶│  Telegram    │
│  (fetch news)│     │  Flash (AI)  │     │  (send report)│
└─────────────┘     └──────────────┘     └──────────────┘
```

1. **Fetch** — Retrieves the latest 3 news articles per stock ticker via `yfinance`.
2. **Analyse** — Sends the news to Gemini 2.2 Flash with a Thai-language prompt focused on:
   - 📊 Market Impact
   - 💰 Earnings & Capacity
   - 🔮 Future Outlook
3. **Deliver** — Formats a clean Markdown report and sends it to your Telegram chat/channel.

---

## Monitored Stocks (default)

| Ticker | Company   |
| ------ | --------- |
| MSFT   | Microsoft |
| NVDA   | NVIDIA    |
| GOOGL  | Alphabet  |
| AAPL   | Apple     |
| AMZN   | Amazon    |
| TSLA   | Tesla     |

> Edit the `TICKERS` list in `monitor_news.py` to customise.

---

## 🔧 Setup Guide

### Prerequisites

- A GitHub repository (public or private)
- Python 3.10+
- A Google AI Studio API key ([get one here](https://aistudio.google.com/app/apikey))
- A Telegram Bot token + Chat ID

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/ai-news-monitor.git
cd ai-news-monitor
```

### 2. Configure GitHub Secrets

Navigate to your repository:

**Settings → Secrets and variables → Actions → New repository secret**

Add the following three secrets:

| Secret Name          | Description              | How to Get It                                                              |
| -------------------- | ------------------------ | -------------------------------------------------------------------------- |
| `GEMINI_API_KEY`     | Google AI Studio API key | Go to [AI Studio](https://aistudio.google.com/app/apikey) → Create API Key |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token   | Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token  |
| `TELEGRAM_CHAT_ID`   | Target chat/channel ID   | Message [@userinfobot](https://t.me/userinfobot) or use the method below   |

#### How to Find Your Telegram Chat ID

1. Start a conversation with your bot (send any message).
2. Open this URL in your browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Look for `"chat":{"id": 123456789}` in the JSON response — that number is your Chat ID.
4. For **channels**, the Chat ID is typically a negative number like `-1001234567890`.

### 3. Enable the Workflow

The workflow is already defined in `.github/workflows/daily_news.yml`.

- **Automatic**: Runs every day at **08:00 UTC** (15:00 ICT).
- **Manual**: Go to **Actions** tab → **Daily Stock News Report** → **Run workflow**.

---

## 🖥️ Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-gemini-api-key"
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Run
python monitor_news.py
```

---

## 📁 Project Structure

```
ai-news-monitor/
├── .github/
│   └── workflows/
│       └── daily_news.yml      # GitHub Actions cron workflow
├── monitor_news.py             # Core script (fetch → analyse → send)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🛠️ Customisation

| What                   | Where                                      |
| ---------------------- | ------------------------------------------ |
| Add/remove tickers     | `TICKERS` list in `monitor_news.py`        |
| Change schedule        | `cron` field in `daily_news.yml`           |
| Adjust news count      | `MAX_NEWS_PER_TICKER` in `monitor_news.py` |
| Modify analysis prompt | `build_prompt()` in `monitor_news.py`      |
| Switch Gemini model    | `GEMINI_MODEL` in `monitor_news.py`        |

---

## License

MIT — feel free to fork and adapt.
