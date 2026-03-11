"""
APEX — Economic Calendar Service
Fetches upcoming high-impact news events from ForexFactory
Warns the risk manager before major events
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from config.settings import settings


class CalendarService:
    """
    Scrapes economic calendar from ForexFactory.
    Provides upcoming event warnings to the risk manager.
    """

    FOREX_FACTORY_URL = "https://www.forexfactory.com/calendar"
    CACHE_DURATION_MINUTES = 60

    # Currency → instruments that care about this currency
    CURRENCY_INSTRUMENT_MAP = {
        "USD": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "XAU_USD", "US500"],
        "EUR": ["EUR_USD"],
        "GBP": ["GBP_USD"],
        "JPY": ["USD_JPY"],
        "AUD": ["AUD_USD"],
        "CAD": ["USD_CAD"],
    }

    def __init__(self):
        self._events_cache: List[Dict] = []
        self._cache_time: Optional[datetime] = None

    async def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        min_impact: str = "LOW",   # LOW | MEDIUM | HIGH
    ) -> List[Dict]:
        """
        Get upcoming economic events.
        
        Returns list of events with:
        - title, currency, impact, event_time, forecast, previous
        - minutes_away: how many minutes until the event
        """
        await self._refresh_cache_if_needed()

        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)

        impact_levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        min_level = impact_levels.get(min_impact.upper(), 0)

        upcoming = []
        for event in self._events_cache:
            event_time = event.get("event_time")
            if not event_time:
                continue

            if now <= event_time <= cutoff:
                event_impact = impact_levels.get(event.get("impact", "LOW"), 0)
                if event_impact >= min_level:
                    event_copy = {**event}
                    event_copy["minutes_away"] = int((event_time - now).total_seconds() / 60)
                    upcoming.append(event_copy)

        upcoming.sort(key=lambda x: x.get("event_time", now))
        return upcoming

    async def get_events_for_instrument(self, instrument: str, hours_ahead: int = 24) -> List[Dict]:
        """Get only events relevant to a specific instrument."""
        all_events = await self.get_upcoming_events(hours_ahead=hours_ahead)
        relevant_currencies = self._get_instrument_currencies(instrument)

        return [
            event for event in all_events
            if event.get("currency") in relevant_currencies
        ]

    def _get_instrument_currencies(self, instrument: str) -> List[str]:
        """Extract currencies from instrument string (e.g. EUR_USD → [EUR, USD])"""
        parts = instrument.split("_")
        if len(parts) == 2:
            return parts
        # Special cases
        if instrument in ["XAU_USD", "XAG_USD", "BCO_USD"]:
            return ["USD"]
        return []

    async def _refresh_cache_if_needed(self):
        """Refresh event cache if it's stale."""
        if (
            self._cache_time is None
            or (datetime.utcnow() - self._cache_time).total_seconds() > self.CACHE_DURATION_MINUTES * 60
        ):
            await self._fetch_events()

    async def _fetch_events(self):
        """Fetch and parse economic calendar."""
        try:
            events = await self._fetch_from_forexfactory()
            if events:
                self._events_cache = events
                self._cache_time = datetime.utcnow()
                high_impact = [e for e in events if e.get("impact") == "HIGH"]
                logger.info(f"Calendar refreshed: {len(events)} events ({len(high_impact)} high-impact)")
        except Exception as e:
            logger.error(f"Calendar fetch error: {e}")
            # Keep old cache if fetch fails

    async def _fetch_from_forexfactory(self) -> List[Dict]:
        """
        Scrape ForexFactory calendar.
        Note: ForexFactory may require headers to avoid blocking.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        events = []

        try:
            async with httpx.AsyncClient(timeout=30, headers=headers) as client:
                response = await client.get(self.FOREX_FACTORY_URL)
                if response.status_code != 200:
                    logger.warning(f"ForexFactory returned {response.status_code}")
                    return self._get_mock_events()

                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.find("table", {"class": "calendar__table"})

                if not table:
                    return self._get_mock_events()

                current_date = datetime.utcnow().date()
                for row in table.find_all("tr", {"class": "calendar__row"}):
                    event = self._parse_row(row, current_date)
                    if event:
                        events.append(event)

        except Exception as e:
            logger.warning(f"ForexFactory scrape error: {e}")
            return self._get_mock_events()

        return events

    def _parse_row(self, row, current_date) -> Optional[Dict]:
        """Parse a single calendar row."""
        try:
            # Impact
            impact_cell = row.find("td", {"class": "calendar__impact"})
            if not impact_cell:
                return None

            impact_icon = impact_cell.find("span")
            if not impact_icon:
                return None

            impact_class = impact_icon.get("class", [""])[0]
            if "red" in impact_class:
                impact = "HIGH"
            elif "orange" in impact_class:
                impact = "MEDIUM"
            else:
                impact = "LOW"

            # Currency
            currency_cell = row.find("td", {"class": "calendar__currency"})
            currency = currency_cell.get_text(strip=True) if currency_cell else ""

            # Event name
            event_cell = row.find("td", {"class": "calendar__event"})
            title = event_cell.get_text(strip=True) if event_cell else ""

            # Time
            time_cell = row.find("td", {"class": "calendar__time"})
            time_str = time_cell.get_text(strip=True) if time_cell else ""

            event_time = None
            if time_str and ":" in time_str:
                try:
                    hour, minute = map(int, time_str.replace("am", "").replace("pm", "").split(":"))
                    if "pm" in time_str.lower() and hour != 12:
                        hour += 12
                    event_time = datetime.combine(current_date, datetime.min.time()).replace(
                        hour=hour, minute=minute
                    )
                except Exception:
                    pass

            # Forecast / Previous
            forecast_cell = row.find("td", {"class": "calendar__forecast"})
            previous_cell = row.find("td", {"class": "calendar__previous"})

            return {
                "title": title,
                "currency": currency,
                "impact": impact,
                "event_time": event_time,
                "forecast": forecast_cell.get_text(strip=True) if forecast_cell else "",
                "previous": previous_cell.get_text(strip=True) if previous_cell else "",
                "actual": None,
            }
        except Exception:
            return None

    def _get_mock_events(self) -> List[Dict]:
        """Return mock events when scraping fails (for development)."""
        now = datetime.utcnow()
        return [
            {
                "title": "Non-Farm Payrolls",
                "currency": "USD",
                "impact": "HIGH",
                "event_time": now + timedelta(hours=6),
                "forecast": "200K",
                "previous": "187K",
                "actual": None,
            },
            {
                "title": "ECB Rate Decision",
                "currency": "EUR",
                "impact": "HIGH",
                "event_time": now + timedelta(hours=18),
                "forecast": "4.50%",
                "previous": "4.50%",
                "actual": None,
            },
        ]


# Singleton
_service: Optional[CalendarService] = None

def get_calendar_service() -> CalendarService:
    global _service
    if _service is None:
        _service = CalendarService()
    return _service
