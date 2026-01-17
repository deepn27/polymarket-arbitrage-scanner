import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    GAMMA_API_URL: str = "https://gamma-api.polymarket.com"
    CLOB_API_URL: str = "https://clob.polymarket.com"
    SCAN_INTERVAL_SECONDS: int = 10
    MIN_ARBITRAGE_PERCENT: float = 0.5
    MIN_LIQUIDITY_USD: float = 100
    DATABASE_PATH: str = "arbitrage.db"
    DISCORD_WEBHOOK_URL: str = ""
    POLYMARKET_FEE_PERCENT: float = 0.02
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
