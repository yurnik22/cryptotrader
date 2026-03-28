# Web/api/bot_control.py
from fastapi import APIRouter, Depends
from Web.auth import get_current_user
from Engine.bot_manager import pause_all_buying, resume_all_buying  # функция из Engine

router = APIRouter()

@router.post("/pause_buying")
async def pause_buying(current_user = Depends(get_current_user)):
    pause_all_buying()
    return {"status": "ok"}

@router.post("/resume_buying")
async def resume(user=Depends(get_current_user)):
    resume_all_buying()
    return {"status": "buying resumed"}