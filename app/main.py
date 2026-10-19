"""FastAPI application with booking endpoint (US-03)."""

from __future__ import annotations

import datetime
import sqlite3

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.clock import get_now
from app.db import get_room, insert_booking_if_free
from app.dependencies import get_current_user, get_db
from app.errors import AppError, RoomNotFoundError
from app.rules.validation import validate_booking

app = FastAPI()


class BookingRequest(BaseModel):
    room_id: int
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    participants: int


class BookingResponse(BaseModel):
    id: int
    room_id: int
    date: datetime.date
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    participants: int


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    err = exc.errors()[0]
    field = err["loc"][-1] if err["loc"] else "richiesta"
    msg = f"Campo '{field}' non valido"
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "INVALID_INPUT", "message": msg}},
    )


@app.post("/bookings", status_code=201, response_model=BookingResponse)
def create_booking(
    body: BookingRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
    now: datetime.datetime = Depends(get_now),
) -> BookingResponse:
    # 1. Check room exists and is active
    room = get_room(conn, body.room_id)
    if room is None or room["active"] != 1:
        raise RoomNotFoundError()

    # 2. Validate booking rules
    validate_booking(
        start_date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
        participants=body.participants,
        capacity=room["capacity"],
        now=now,
    )

    # 3. Insert booking (handles its own transaction)
    booking_id = insert_booking_if_free(
        conn,
        room_id=body.room_id,
        user_email=user["email"],
        booking_date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
        participants=body.participants,
        created_at=now,
    )

    return BookingResponse(
        id=booking_id,
        room_id=body.room_id,
        date=body.date,
        start_time=body.start_time.strftime("%H:%M"),
        end_time=body.end_time.strftime("%H:%M"),
        participants=body.participants,
    )
