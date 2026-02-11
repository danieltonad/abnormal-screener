from datetime import datetime, timedelta, timezone
from .types import Countries, EventRating
from httpx import AsyncClient


class TdvEventService:
    url = "https://economic-calendar.tradingview.com/events"

    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "origin": "https://www.tradingview.com",
        "referer": "https://www.tradingview.com/",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
    }
    
    def minutes_left(self, target_time_str):
        target_time = datetime.fromisoformat(target_time_str.replace("Z", "+00:00"))
        current_time = datetime.now(timezone.utc)
        time_difference = target_time - current_time
        minutes = int(time_difference.total_seconds() / 60)
        return minutes

    def get_dates(self, days: int = 1):
        current_time = datetime.now(timezone.utc)  # Add a buffer to include imminent events
        next_time = current_time + timedelta(days=days)
        current_date_str = current_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        next_date_str = next_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return current_date_str, next_date_str
    
    async def get_events(self, rating: EventRating = EventRating.THREE_STAR):
        event_info = []
        _from, to = self.get_dates()
        params = {
            "from": _from,
            "to": to,
            "countries": ",".join([country.value for country in Countries])
        }
        # print(f"Fetching TDV events from {params['from']} to {params['to']} for countries: {params['countries']}")
        
        async with AsyncClient() as session:
            response = await session.get(self.url, headers=self.headers, params=params)
            result = response.json()
            if response.status_code == 200 and result.get("status") == 'ok':
                data = result.get("result", [])
                events = [event for event in data if int(event.get("importance")) == rating.value]
                for event in events:
                    date = event.get("date")    
                    ticker = event.get("ticker")
                    # title = event.get("title")
                    # print(title, "====>", ticker)
                    # minutes_left = self.minutes_left(date)
                    if ticker:
                        event_info.append({"date": date})
            return event_info
        


    # async def get_classified_events(self):
    #     event_info = []
    #     _from, to = self.get_dates()
    #     params = {
    #         "from": _from,
    #         "to": to,
    #         "countries": ",".join([country.value for country in Countries])
    #     }
    #     async with AsyncClient() as session:
    #         response = await session.get(self.url, headers=self.headers, params=params)
    #         result = response.json()

    #     data = result.get("result", [])
    #     print("TOTAL TDV EVENTS => ", len(data))
    #     for event in data:
    #         classification = self.classify_event(event)
    #         if classification:
    #             event_info.append({
    #                 "date": event.get("date"),
    #                 "classification": classification
    #             })

    #     return event_info


    
    # def classify_event(self, event):
    #     title = event.get("title", "").lower()
    #     indicator = event.get("indicator", "").lower()
    #     country = event.get("country", "").upper()
        
    #     # -------- FOMC + Powell / Federal Reserve Conferences ----------
    #     if country == "US" and (
    #         "fomc" in title or
    #         "powell" in title or
    #         "fed chair" in title or
    #         "press conference" in title or
    #         "interest rate" in title or
    #         "monetary policy" in indicator
    #     ):
    #         return "FOMC"

    #     # -------------------------- NFP -------------------------------
    #     if country == "US" and (
    #         "nonfarm" in title or
    #         "non farm" in title or
    #         "payroll" in title
    #     ):
    #         return "NFP"

    #     # -------------------------- CPI -------------------------------
    #     if (
    #         "cpi" in title or
    #         "consumer price" in indicator or
    #         "inflation rate" in title
    #     ):
    #         return "CPI"

    #     # -------------------------- PPI -------------------------------
    #     if (
    #         "ppi" in title or
    #         "producer price" in indicator
    #     ):
    #         return "PPI"

    #     # ------------------- Rate Decisions by Country -----------------
    #     if (
    #         "rate decision" in title or
    #         "interest rate" in title or
    #         "policy meeting" in title or
    #         "monetary policy" in title
    #     ):
    #         if country == "US":
    #             return "Federal Rate Decision"
    #         if country == "EU":
    #             return "ECB Decision"
    #         if country == "GB":
    #             return "BOE Decision"
    #         if country == "JP":
    #             return "BOJ Decision"

    #     return None
