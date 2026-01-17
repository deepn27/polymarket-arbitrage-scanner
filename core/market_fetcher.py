import httpx
import asyncio
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class MarketFetcher:
    def __init__(self):
        self.gamma_url = settings.GAMMA_API_URL
        self.clob_url = settings.CLOB_API_URL
        self.timeout = httpx.Timeout(30.0)
    
    async def _request_with_retry(self, client: httpx.AsyncClient, url: str, params: dict = None, retries: int = 3) -> dict:
        for attempt in range(retries):
            try:
                await asyncio.sleep(0.1)
                response = await client.get(url, params=params, timeout=self.timeout)
                
                if response.status_code == 429:
                    logger.warning("Rate limited, waiting 60 seconds...")
                    await asyncio.sleep(60)
                    continue
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        return {}
    
    async def fetch_all_events(self) -> List[dict]:
        events = []
        offset = 0
        limit = 100
        
        async with httpx.AsyncClient() as client:
            while True:
                params = {
                    "closed": "false",
                    "archived": "false",
                    "limit": limit,
                    "offset": offset
                }
                data = await self._request_with_retry(
                    client, 
                    f"{self.gamma_url}/events",
                    params
                )
                
                if not data or (isinstance(data, list) and len(data) == 0):
                    break
                
                if isinstance(data, list):
                    events.extend(data)
                    if len(data) < limit:
                        break
                    offset += limit
                else:
                    break
        
        logger.info(f"Fetched {len(events)} events")
        return events
    
    async def fetch_all_markets(self) -> List[dict]:
        markets = []
        offset = 0
        limit = 100
        
        async with httpx.AsyncClient() as client:
            while True:
                params = {
                    "closed": "false",
                    "archived": "false",
                    "limit": limit,
                    "offset": offset
                }
                data = await self._request_with_retry(
                    client,
                    f"{self.gamma_url}/markets",
                    params
                )
                
                if not data or (isinstance(data, list) and len(data) == 0):
                    break
                
                if isinstance(data, list):
                    markets.extend(data)
                    if len(data) < limit:
                        break
                    offset += limit
                else:
                    break
        
        logger.info(f"Fetched {len(markets)} markets")
        return markets
    
    async def fetch_prices(self, token_ids: List[str]) -> Dict[str, Any]:
        if not token_ids:
            return {}
        
        prices = {}
        chunk_size = 100
        
        async with httpx.AsyncClient() as client:
            for i in range(0, len(token_ids), chunk_size):
                chunk = token_ids[i:i + chunk_size]
                params = {"token_ids": ",".join(chunk)}
                
                data = await self._request_with_retry(
                    client,
                    f"{self.clob_url}/prices",
                    params
                )
                
                if isinstance(data, dict):
                    prices.update(data)
        
        return prices
    
    async def fetch_orderbook(self, token_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            data = await self._request_with_retry(
                client,
                f"{self.clob_url}/book",
                {"token_id": token_id}
            )
            return data if isinstance(data, dict) else {}

market_fetcher = MarketFetcher()
