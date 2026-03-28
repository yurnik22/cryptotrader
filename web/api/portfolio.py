# Web/api/portfolio.py
from fastapi import APIRouter, Depends
from Database.portfolio import get_portfolio_for_user
from Web.auth import get_current_user

router = APIRouter()

"""@router.get("/portfolio")
async def portfolio(current_user = Depends(get_current_user)):
    portfolio_data = get_portfolio_for_user(current_user.id)
    return portfolio_data"""

@router.get("/portfolio")
async def portfolio(user=Depends(get_current_user)):
    # пока mock — позже подключим Database
    return {
        "BTC": 0.42,
        "ETH": 1.8,
        "USDT": 1200
    }