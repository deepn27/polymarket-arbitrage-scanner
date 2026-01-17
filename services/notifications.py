import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)

async def send_discord_notification(opportunity: dict):
    if not settings.DISCORD_WEBHOOK_URL:
        return
    
    embed = {
        "title": "New Arbitrage Opportunity!",
        "color": 0x22c55e,
        "fields": [
            {"name": "Market", "value": opportunity.get("market_question", "N/A")[:100], "inline": False},
            {"name": "Net Profit", "value": f"${opportunity.get('net_profit', 0):.4f}", "inline": True},
            {"name": "Profit %", "value": f"{opportunity.get('net_profit_percent', 0):.2f}%", "inline": True},
            {"name": "Liquidity", "value": f"${opportunity.get('min_liquidity', 0):,.0f}", "inline": True},
        ]
    }
    
    slug = opportunity.get("slug", "")
    if slug:
        embed["url"] = f"https://polymarket.com/event/{slug}"
    
    payload = {"embeds": [embed]}
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(settings.DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
