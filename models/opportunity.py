from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class ArbitrageType(str, Enum):
    BINARY_MISPRICING = "BINARY_MISPRICING"
    DUTCH_BOOK_UNDER = "DUTCH_BOOK_UNDER"
    MULTI_MARKET_INCONSISTENCY = "MULTI_MARKET_INCONSISTENCY"

class TradeLeg(BaseModel):
    token_id: str
    outcome: str
    side: str = "BUY"
    price: float
    suggested_size: float = 1.0

class Opportunity(BaseModel):
    id: str
    detected_at: datetime
    arbitrage_type: ArbitrageType
    event_title: Optional[str] = None
    market_question: str
    markets_involved: List[str]
    total_cost: float
    guaranteed_payout: float = 1.0
    gross_profit: float
    gross_profit_percent: float
    estimated_fees: float
    net_profit: float
    net_profit_percent: float
    trade_legs: List[TradeLeg]
    min_liquidity: float
    slug: str = ""
    is_active: bool = True
    last_seen_at: Optional[datetime] = None
    times_detected: int = 1
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "detected_at": self.detected_at.isoformat(),
            "arbitrage_type": self.arbitrage_type.value,
            "event_title": self.event_title,
            "market_question": self.market_question,
            "markets_involved": self.markets_involved,
            "total_cost": self.total_cost,
            "guaranteed_payout": self.guaranteed_payout,
            "gross_profit": self.gross_profit,
            "gross_profit_percent": self.gross_profit_percent,
            "estimated_fees": self.estimated_fees,
            "net_profit": self.net_profit,
            "net_profit_percent": self.net_profit_percent,
            "trade_legs": [leg.model_dump() for leg in self.trade_legs],
            "min_liquidity": self.min_liquidity,
            "slug": self.slug,
            "is_active": self.is_active,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "times_detected": self.times_detected
        }
