"""
AI Stock News Monitor
=====================
Fetches latest stock news via yfinance, summarises with Gemini 2.5 Flash,
and delivers a formatted Markdown report to Telegram.

Environment Variables (required):
    GEMINI_API_KEY      – Google AI Studio API key
    TELEGRAM_BOT_TOKEN  – Telegram Bot token from @BotFather
    TELEGRAM_CHAT_ID    – Target Telegram chat / channel ID
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime, timezone

import yfinance as yf
from google import genai
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Stock tickers to monitor – edit this list to your preference
TICKERS: list[str] = ["MSFT", "NVDA", "GOOGL", "AAPL", "AMZN", "TSLA", "V", "EOSE"]

# Maximum news items to fetch per ticker
MAX_NEWS_PER_TICKER: int = 3

# Gemini model
GEMINI_MODEL: str = "gemini-2.5-flash"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: load required environment variables
# ---------------------------------------------------------------------------


def _env(name: str) -> str:
    """Return an environment variable or abort with a clear message."""
    value = os.environ.get(name)
    if not value:
        logger.error("Missing required environment variable: %s", name)
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# 1. Fetch news
# ---------------------------------------------------------------------------


def fetch_news(
    tickers: list[str], max_items: int = MAX_NEWS_PER_TICKER
) -> dict[str, list[dict]]:
    """
    Fetch the latest news articles for each ticker using yfinance.

    Returns a dict mapping ticker -> list of news dicts (title, publisher, link).
    Tickers with no news are included with an empty list.
    """
    all_news: dict[str, list[dict]] = {}

    for ticker in tickers:
        logger.info("Fetching news for %s …", ticker)
        try:
            stock = yf.Ticker(ticker)
            raw_news = stock.news or []

            items: list[dict] = []
            for article in raw_news[:max_items]:
                # Handle newer yfinance format where data is nested under 'content'
                content = article.get("content", article)
                
                title = content.get("title", "N/A")
                
                # Publisher could be a string or a dict
                provider = content.get("provider", {})
                if isinstance(provider, dict):
                    publisher = provider.get("displayName", "Unknown")
                else:
                    publisher = content.get("publisher", "Unknown")
                
                # Link could be in clickThroughUrl, canonicalUrl, or direct link
                link = ""
                if "clickThroughUrl" in content and isinstance(content["clickThroughUrl"], dict) and content["clickThroughUrl"].get("url"):
                    link = content["clickThroughUrl"].get("url", "")
                elif "canonicalUrl" in content and isinstance(content["canonicalUrl"], dict):
                    link = content["canonicalUrl"].get("url", "")
                elif "link" in content:
                    link = content.get("link", "")
                    
                items.append(
                    {
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                    }
                )

            all_news[ticker] = items
            logger.info("  → %d article(s) found for %s", len(items), ticker)

        except Exception as exc:
            logger.warning("Failed to fetch news for %s: %s", ticker, exc)
            all_news[ticker] = []

    return all_news


# ---------------------------------------------------------------------------
# 2. Build the Gemini prompt
# ---------------------------------------------------------------------------


def build_prompt(news_data: dict[str, list[dict]]) -> str:
    """
    Construct an optimised prompt for Gemini that requests a Thai-language
    stock-analysis summary with a professional analyst tone.
    """
    # Flatten news into a structured text block
    news_block_parts: list[str] = []

    for ticker, articles in news_data.items():
        if not articles:
            news_block_parts.append(f"### {ticker}\nไม่พบข่าวล่าสุด\n")
            continue

        lines = [f"### {ticker}"]
        for idx, art in enumerate(articles, 1):
            lines.append(f"{idx}. **{art['title']}** — _{art['publisher']}_")
            if art["link"]:
                lines.append(f"   🔗 {art['link']}")
        news_block_parts.append("\n".join(lines))

    news_block = "\n\n".join(news_block_parts)

    prompt = f"""\
คุณคือนักวิเคราะห์หุ้นระดับมืออาชีพ (Senior Equity Analyst) ที่มีความเชี่ยวชาญในตลาดหุ้นสหรัฐฯ

จากข่าวหุ้นล่าสุดด้านล่าง ให้วิเคราะห์และสรุปเป็นภาษาไทย โดยใช้โทนของนักวิเคราะห์มืออาชีพ \
ที่นำเสนอข้อมูลอย่างกระชับ ชัดเจน และมีเหตุผลรองรับ

สำหรับ **แต่ละหุ้น** ให้วิเคราะห์ใน 3 มิติ:
1. 📊 **ผลกระทบต่อตลาด (Market Impact)** — ข่าวนี้ส่งผลกระทบต่อราคาหุ้นและตลาดโดยรวมอย่างไร
2. 💰 **กำไร/กำลังการผลิต (Earnings & Capacity)** — มีผลต่อรายได้ กำไร หรือศักยภาพการผลิตอย่างไร
3. 🔮 **แนวโน้มอนาคต (Future Outlook)** — ประเมินทิศทางในอนาคตระยะสั้น-กลาง

กฎสำคัญ:
- ตอบเป็น **ภาษาไทย** ทั้งหมด
- ใช้ **Markdown** ในการจัดรูปแบบ ให้อ่านง่ายบน Telegram
- หุ้นที่ไม่มีข่าว ให้ระบุสั้นๆ ว่า "ไม่มีข่าวอัพเดต"
- ลงท้ายด้วย **สรุปภาพรวมตลาด** 1 ย่อหน้า

---

## ข่าวหุ้นล่าสุด

{news_block}

---

กรุณาเริ่มวิเคราะห์:
"""
    return prompt


# ---------------------------------------------------------------------------
# 3. Summarise with Gemini
# ---------------------------------------------------------------------------


def summarise_with_gemini(prompt: str, api_key: str) -> str:
    """
    Send the prompt to Gemini 2.5 Flash and return the generated summary.
    """
    logger.info("Sending prompt to Gemini (%s) …", GEMINI_MODEL)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        if not response or not response.text:
            logger.error("Gemini returned an empty response.")
            return "⚠️ ไม่สามารถสร้างสรุปข่าวได้ — Gemini ไม่ตอบกลับ"

        logger.info("Gemini response received (%d chars).", len(response.text))
        return response.text

    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        return f"⚠️ เกิดข้อผิดพลาดจาก Gemini API: {exc}"


# ---------------------------------------------------------------------------
# 4. Send to Telegram
# ---------------------------------------------------------------------------


def send_telegram_message(
    text: str,
    bot_token: str,
    chat_id: str,
    *,
    parse_mode: str = "Markdown",
) -> bool:
    """
    Send a Markdown-formatted message to Telegram.

    Long messages (>4096 chars) are automatically split into chunks.
    Returns True if all chunks were sent successfully.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Telegram message limit
    max_len = 4096
    chunks = [text[i : i + max_len] for i in range(0, len(text), max_len)]

    success = True
    for idx, chunk in enumerate(chunks, 1):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": parse_mode,
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                logger.info("Telegram chunk %d/%d sent ✓", idx, len(chunks))
            else:
                logger.error(
                    "Telegram API error (HTTP %d): %s",
                    resp.status_code,
                    resp.text,
                )
                success = False
        except requests.RequestException as exc:
            logger.error("Telegram request failed: %s", exc)
            success = False

    return success


# ---------------------------------------------------------------------------
# 5. Build the final report
# ---------------------------------------------------------------------------


def build_report(summary: str) -> str:
    """Wrap the Gemini summary in a timestamped header for Telegram."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = f"📈 *AI Stock News Monitor*\n🗓 {now_utc}\n{'—' * 30}\n\n"
    return header + summary


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    """Orchestrate the full pipeline: fetch → summarise → send."""
    logger.info("=" * 50)
    logger.info("AI Stock News Monitor — starting run")
    logger.info("=" * 50)

    # Load secrets
    gemini_key = _env("GEMINI_API_KEY")
    bot_token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")

    # Step 1 — Fetch news
    news_data = fetch_news(TICKERS)

    total_articles = sum(len(v) for v in news_data.values())
    if total_articles == 0:
        logger.warning("No news articles found for any ticker. Sending notice.")
        send_telegram_message(
            "📈 *AI Stock News Monitor*\n\nไม่พบข่าวหุ้นในรอบนี้",
            bot_token,
            chat_id,
        )
        return

    # Step 2 — Summarise with Gemini
    prompt = build_prompt(news_data)
    summary = summarise_with_gemini(prompt, gemini_key)

    # Step 3 — Build & send report
    report = build_report(summary)
    ok = send_telegram_message(report, bot_token, chat_id)

    if ok:
        logger.info("✅ Report sent successfully!")
    else:
        logger.error("❌ Some messages failed to send.")
        sys.exit(1)


if __name__ == "__main__":
    main()
