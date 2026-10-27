"""Read-only historical analytics, kept separate from live predictions."""
from datetime import date as Date
from typing import Literal, Optional

from fastapi import APIRouter, Path, Query
from app.services import analytics_service as service

router = APIRouter(prefix='/analytics')
Market = Literal['US', 'NSE', 'BSE']


@router.get('/overview')
def overview():
    return service.overview()


@router.get('/rankings')
def rankings(market: Market = 'US', date: Optional[Date] = None,
             limit: int = Query(10, ge=1, le=10),
             run: Optional[str] = Query(None, pattern=r'^[A-Za-z0-9_-]{1,80}$')):
    return service.rankings(market, date, limit, run)


@router.get('/stock/{ticker}')
def stock(ticker: str = Path(..., pattern=r'^[A-Za-z0-9^][A-Za-z0-9.^=-]{0,19}$'),
          market: Market = 'US', start: Optional[Date] = None, end: Optional[Date] = None,
          limit: int = Query(1000, ge=1, le=3000),
          run: Optional[str] = Query(None, pattern=r'^[A-Za-z0-9_-]{1,80}$')):
    return service.stock(ticker.upper(), market, start, end, limit, run)


@router.get('/benchmarks')
def benchmarks(run: Optional[str] = Query(None, pattern=r'^[A-Za-z0-9_-]{1,80}$')):
    return service.benchmarks(run)
