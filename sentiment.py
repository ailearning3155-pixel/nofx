"""
APEX — News Sentiment Service
Fetches financial news and scores sentiment using FinBERT or VADER
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from config.settings import settings

# Instrument to currency/keyword mapping
INSTRUMENT_KEYWORDS = {
    "EUR_USD": ["EUR", "euro", "ECB", "eurozone", "European"],
    "GBP_USD": ["GBP", "pound", "sterling", "BOE", "Bank of England", "UK"],
    "USD_JPY": ["JPY", "yen", "BOJ", "Bank of Japan"],
    "AUD_USD": ["AUD", "Australian dollar", "RBA"],
    "USD_CAD": ["CAD", "Canadian dollar", "BOC"],
    "XAU_USD": ["gold", "XAU", "precious metals", "safe haven"],
    "US500":   ["S&P 500", "US stocks", "Wall Street", "Fed", "Federal Reserve"],
    "USD":     ["dollar", "USD", "Federal Reserve", "Fed", "FOMC"],
}


class NewsService:
    """
    Fetches news and scores sentiment for trading instruments.
    Uses FinBERT (best for financial text) or VADER as fallback.
    """

    def __init__(self):
        self.model_name = settings.news.sentiment_model
        self._sentiment_pipeline = None
        self._cache: Dict[str, Dict] = {}   # instrument → {score, label, headlines, fetched_at}
        self._init_model()

    def _init_model(self):
        """Initialize sentiment model."""
        if self.model_name == "finbert":
            try:
                from transformers import pipeline
                self._sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    tokenizer="ProsusAI/finbert",
                    max_length=512,
                    truncation=True,
                )
                logger.info("✅ FinBERT sentiment model loaded")
            except Exception as e:
                logger.warning(f"FinBERT failed to load: {e}. Falling back to VADER")
                self.model_name = "vader"

        if self.model_name == "vader":
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                self._vader = SentimentIntensityAnalyzer()
                logger.info("✅ VADER sentiment initialized")
            except Exception as e:
                logger.error(f"VADER init failed: {e}")

    async def get_sentiment(self, instrument: str) -> Dict:
        """
        Get current sentiment for an instrument.
        Uses cache if data is fresh enough.
        """
        cached = self._cache.get(instrument)
        if cached:
            age = (datetime.utcnow() - cached["fetched_at"]).seconds
            if age < settings.news.update_interval:
                return cached

        try:
            headlines = await self._fetch_headlines(instrument)
            if not headlines:
                return self._empty_sentiment(instrument)

            scores = []
            for headline in headlines[:10]:
                score = self._score_headline(headline)
                scores.append(score)

            avg_score = sum(scores) / len(scores)
            label = "positive" if avg_score > 0.1 else "negative" if avg_score < -0.1 else "neutral"

            result = {
                "instrument": instrument,
                "score": avg_score,
                "label": label,
                "headlines": headlines[:5],
                "article_count": len(headlines),
                "fetched_at": datetime.utcnow(),
            }

            self._cache[instrument] = result
            logger.debug(f"Sentiment {instrument}: {label} ({avg_score:.3f}) from {len(headlines)} articles")
            return result

        except Exception as e:
            logger.error(f"News sentiment error for {instrument}: {e}")
            return self._empty_sentiment(instrument)

    async def _fetch_headlines(self, instrument: str) -> List[str]:
        """Fetch news headlines for an instrument."""
        keywords = INSTRUMENT_KEYWORDS.get(instrument, [instrument.replace("_", "/")])
        headlines = []

        if not settings.news.api_key:
            logger.warning("No NEWS_API_KEY configured — using mock headlines")
            return [f"Market update for {instrument}"]

        try:
            from newsapi import NewsApiClient
            newsapi = NewsApiClient(api_key=settings.news.api_key)

            query = " OR ".join(f'"{kw}"' for kw in keywords[:3])
            result = newsapi.get_everything(
                q=query,
                language="en",
                sort_by="publishedAt",
                from_param=(datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"),
                page_size=20,
            )

            for article in result.get("articles", []):
                title = article.get("title", "")
                description = article.get("description", "")
                if title:
                    headlines.append(f"{title}. {description}" if description else title)

        except Exception as e:
            logger.warning(f"NewsAPI error: {e}")

        return headlines

    def _score_headline(self, text: str) -> float:
        """Score a single headline. Returns -1.0 to 1.0."""
        if self.model_name == "finbert" and self._sentiment_pipeline:
            try:
                result = self._sentiment_pipeline(text[:512])[0]
                label = result["label"].lower()
                score = result["score"]
                if label == "positive":
                    return score
                elif label == "negative":
                    return -score
                else:
                    return 0.0
            except Exception:
                pass

        if hasattr(self, "_vader"):
            scores = self._vader.polarity_scores(text)
            return scores["compound"]

        return 0.0

    def _empty_sentiment(self, instrument: str) -> Dict:
        return {
            "instrument": instrument,
            "score": 0.0,
            "label": "neutral",
            "headlines": [],
            "article_count": 0,
            "fetched_at": datetime.utcnow(),
        }

    async def get_all_sentiments(self, instruments: List[str]) -> Dict[str, Dict]:
        """Fetch sentiments for multiple instruments concurrently."""
        tasks = [self.get_sentiment(instr) for instr in instruments]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            instr: (result if isinstance(result, dict) else self._empty_sentiment(instr))
            for instr, result in zip(instruments, results)
        }


# Singleton
_service: Optional[NewsService] = None

def get_news_service() -> NewsService:
    global _service
    if _service is None:
        _service = NewsService()
    return _service
