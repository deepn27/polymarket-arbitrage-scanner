from typing import List, Optional
from pydantic import BaseModel, Field

class Token(BaseModel):
    token_id: str
    outcome: str
    price: float = 0.0
    
    @classmethod
    def from_api(cls, data: dict) -> "Token":
        return cls(
            token_id=str(data.get("token_id", "")),
            outcome=data.get("outcome", ""),
            price=float(data.get("price", 0) or 0)
        )

class Market(BaseModel):
    id: str
    question: str
    condition_id: str = Field(alias="conditionId", default="")
    slug: str = ""
    tokens: List[Token] = []
    volume_24h: float = Field(alias="volume24hr", default=0)
    liquidity: float = 0
    closed: bool = False
    event_title: Optional[str] = None
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def from_api(cls, data: dict) -> "Market":
        tokens = []
        raw_tokens = data.get("tokens", [])
        if raw_tokens:
            for t in raw_tokens:
                tokens.append(Token.from_api(t))
        
        return cls(
            id=str(data.get("id", "")),
            question=data.get("question", ""),
            condition_id=data.get("conditionId", ""),
            slug=data.get("slug", ""),
            tokens=tokens,
            volume_24h=float(data.get("volume24hr", 0) or 0),
            liquidity=float(data.get("liquidity", 0) or 0),
            closed=data.get("closed", False),
            event_title=data.get("groupItemTitle") or data.get("eventTitle")
        )
