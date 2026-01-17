from typing import List
from models.market import Token

def calculate_price_sum(tokens: List[Token]) -> float:
    return sum(token.price for token in tokens)

def get_best_ask_prices(tokens: List[Token]) -> List[float]:
    return [token.price for token in tokens]
