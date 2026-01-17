import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import settings
from core.market_fetcher import market_fetcher
from core.arbitrage_detector import detect_arbitrage
from models.market import Market
from models.opportunity import Opportunity
from models.database import (
    save_opportunity, log_scan_start, log_scan_complete,
    mark_opportunity_inactive, get_active_opportunities
)

logger = logging.getLogger(__name__)

class ArbitrageScanner:
    def __init__(self):
        self.is_running: bool = False
        self.last_scan_at: Optional[datetime] = None
        self.active_opportunities: Dict[str, Opportunity] = {}
        self.scan_count: int = 0
        self.markets_scanned: int = 0
        self._scan_task: Optional[asyncio.Task] = None
        self._websocket_callback = None
    
    def set_websocket_callback(self, callback):
        self._websocket_callback = callback
    
    async def run_single_scan(self) -> List[Opportunity]:
        start_time = time.time()
        scan_id = await log_scan_start()
        opportunities_found: List[Opportunity] = []
        error_msg = None
        
        try:
            logger.info("Starting market scan...")
            
            raw_markets = await market_fetcher.fetch_all_markets()
            
            token_ids = []
            for m in raw_markets:
                tokens = m.get("tokens", [])
                for t in tokens:
                    tid = t.get("token_id")
                    if tid:
                        token_ids.append(str(tid))
            
            prices = {}
            if token_ids:
                prices = await market_fetcher.fetch_prices(token_ids)
            
            current_opp_ids = set()
            
            for raw in raw_markets:
                try:
                    market = Market.from_api(raw)
                    
                    if market.liquidity < settings.MIN_LIQUIDITY_USD:
                        continue
                    
                    if prices:
                        for token in market.tokens:
                            if token.token_id in prices:
                                price_data = prices[token.token_id]
                                if isinstance(price_data, dict):
                                    token.price = float(price_data.get("price", token.price) or token.price)
                                elif isinstance(price_data, (int, float, str)):
                                    token.price = float(price_data)
                    
                    opportunity = detect_arbitrage(market)
                    if opportunity:
                        opportunities_found.append(opportunity)
                        current_opp_ids.add(opportunity.id)
                        
                        await save_opportunity(opportunity.to_dict())
                        
                        self.active_opportunities[opportunity.id] = opportunity
                        
                        if self._websocket_callback:
                            await self._websocket_callback({
                                "type": "new_opportunity",
                                "data": opportunity.to_dict()
                            })
                
                except Exception as e:
                    logger.warning(f"Error processing market: {e}")
                    continue
            
            expired_ids = set(self.active_opportunities.keys()) - current_opp_ids
            for opp_id in expired_ids:
                await mark_opportunity_inactive(opp_id)
                del self.active_opportunities[opp_id]
                if self._websocket_callback:
                    await self._websocket_callback({
                        "type": "opportunity_expired",
                        "opportunity_id": opp_id
                    })
            
            self.markets_scanned = len(raw_markets)
            self.scan_count += 1
            self.last_scan_at = datetime.utcnow()
            
            logger.info(f"Scan complete: {self.markets_scanned} markets, {len(opportunities_found)} opportunities")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Scan failed: {e}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        await log_scan_complete(
            scan_id,
            self.markets_scanned,
            len(opportunities_found),
            duration_ms,
            error_msg
        )
        
        if self._websocket_callback:
            await self._websocket_callback({
                "type": "scan_complete",
                "data": {
                    "markets": self.markets_scanned,
                    "opportunities": len(opportunities_found)
                }
            })
        
        return opportunities_found
    
    async def start_continuous_scanning(self):
        if self.is_running:
            logger.warning("Scanner already running")
            return
        
        self.is_running = True
        logger.info("Starting continuous scanning...")
        
        while self.is_running:
            try:
                await self.run_single_scan()
            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
            
            if self.is_running:
                await asyncio.sleep(settings.SCAN_INTERVAL_SECONDS)
    
    def stop(self):
        self.is_running = False
        if self._scan_task:
            self._scan_task.cancel()
            self._scan_task = None
        logger.info("Scanner stopped")
    
    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "scan_count": self.scan_count,
            "markets_scanned": self.markets_scanned,
            "active_opportunities_count": len(self.active_opportunities)
        }

scanner = ArbitrageScanner()
