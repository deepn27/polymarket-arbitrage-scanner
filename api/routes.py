import asyncio
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional
from models.database import (
    get_active_opportunities, get_opportunity_by_id,
    get_scan_history, get_summary_stats
)
from core.scanner import scanner

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "ok"}

@router.get("/status")
async def get_status():
    return scanner.get_status()

@router.post("/start")
async def start_scanning(background_tasks: BackgroundTasks):
    if scanner.is_running:
        return {"message": "Scanner already running", "status": "running"}
    
    background_tasks.add_task(scanner.start_continuous_scanning)
    return {"message": "Scanner started", "status": "starting"}

@router.post("/stop")
async def stop_scanning():
    scanner.stop()
    return {"message": "Scanner stopped", "status": "stopped"}

@router.post("/scan")
async def trigger_scan():
    if scanner.is_running:
        return {"message": "Scanner is running continuously, skipping manual trigger"}
    
    opportunities = await scanner.run_single_scan()
    return {
        "message": "Scan complete",
        "opportunities_found": len(opportunities),
        "markets_scanned": scanner.markets_scanned
    }

@router.get("/opportunities")
async def list_opportunities(
    min_profit: float = Query(default=0, ge=0),
    sort: str = Query(default="profit", pattern="^(profit|liquidity|recent)$"),
    limit: int = Query(default=100, ge=1, le=500)
):
    opportunities = await get_active_opportunities(limit, min_profit, sort)
    return opportunities

@router.get("/opportunities/{opp_id}")
async def get_opportunity(opp_id: str):
    opportunity = await get_opportunity_by_id(opp_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity

@router.get("/summary")
async def get_summary():
    stats = await get_summary_stats()
    return stats

@router.get("/history")
async def get_history(limit: int = Query(default=50, ge=1, le=200)):
    history = await get_scan_history(limit)
    return history
