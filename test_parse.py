import yfinance as yf

raw_news = yf.Ticker('AAPL').news or []
items = []
for article in raw_news[:3]:
    content = article.get("content", article)
    title = content.get("title", "N/A")
    provider = content.get("provider", {})
    if isinstance(provider, dict):
        publisher = provider.get("displayName", "Unknown")
    else:
        publisher = content.get("publisher", "Unknown")
    link = ""
    if "clickThroughUrl" in content and isinstance(content["clickThroughUrl"], dict) and content["clickThroughUrl"].get("url"):
        link = content["clickThroughUrl"].get("url", "")
    elif "canonicalUrl" in content and isinstance(content["canonicalUrl"], dict):
        link = content["canonicalUrl"].get("url", "")
    elif "link" in content:
        link = content.get("link", "")
    items.append({"title": title, "publisher": publisher, "link": link})

print(items)
