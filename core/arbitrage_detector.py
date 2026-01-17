import hashlib
from typing import Optional, List
from datetime import datetime
from models.market import Market, Token
from models.opportunity import Opportunity, TradeLeg, ArbitrageType
from config import settings

def calculate_price_sum(tokens: List[Token]) -> float:
    return sum(token.price for token in tokens)

def generate_opportunity_id(market: Market) -> str:
    data = f"{market.condition_id or market.id}"
    return hashlib.md5(data.encode()).hexdigest()[:16]

def generate_trade_legs(market: Market) -> List[TradeLeg]:
    legs = []
    for token in market.tokens:
        legs.append(TradeLeg(
            token_id=token.token_id,
            outcome=token.outcome,
            side="BUY",
            price=token.price,
            suggested_size=1.0
        ))
    return legs

def detect_arbitrage(market: Market) -> Optional[Opportunity]:
    if not market.tokens or len(market.tokens) < 2:
        return None
    
    valid_tokens = [t for t in market.tokens if t.price > 0]
    if len(valid_tokens) < 2:
        return None
    
    price_sum = calculate_price_sum(valid_tokens)
    
    if price_sum >= 1.0:
        return None
    
    total_cost = price_sum
    guaranteed_payout = 1.0
    gross_profit = guaranteed_payout - total_cost
    gross_profit_percent = (gross_profit / total_cost) * 100 if total_cost > 0 else 0
    
    estimated_fees = guaranteed_payout * settings.POLYMARKET_FEE_PERCENT
    net_profit = gross_profit - estimated_fees
    net_profit_percent = (net_profit / total_cost) * 100 if total_cost > 0 else 0
    
    if net_profit_percent < settings.MIN_ARBITRAGE_PERCENT:
        return None
    
    arb_type = ArbitrageType.BINARY_MISPRICING if len(valid_tokens) == 2 else ArbitrageType.DUTCH_BOOK_UNDER
    
    return Opportunity(
        id=generate_opportunity_id(market),
        detected_at=datetime.utcnow(),
        arbitrage_type=arb_type,
        event_title=market.event_title,
        market_question=market.question,
        markets_involved=[market.condition_id or market.id],
        total_cost=round(total_cost, 4),
        guaranteed_payout=guaranteed_payout,
        gross_profit=round(gross_profit, 4),
        gross_profit_percent=round(gross_profit_percent, 2),
        estimated_fees=round(estimated_fees, 4),
        net_profit=round(net_profit, 4),
        net_profit_percent=round(net_profit_percent, 2),
        trade_legs=generate_trade_legs(market),
        min_liquidity=market.liquidity,
        slug=market.slug
    )
