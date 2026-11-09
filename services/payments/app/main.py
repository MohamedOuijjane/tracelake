"""Payments service: charges an order and asks notification to tell the customer."""

import asyncio
import os
import random
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://localhost:8004")
FAILURE_RATE = float(os.getenv("PAYMENT_FAILURE_RATE", "0.05"))

app = FastAPI(title="payments")


class PaymentRequest(BaseModel):
    order_id: int
    amount: float = Field(gt=0)
    currency: str = "EUR"


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: int
    status: str


@app.get("/health")
async def health() -> dict:
    return {"status": "UP"}


@app.post("/payments", response_model=PaymentResponse, status_code=201)
async def pay(request: PaymentRequest) -> PaymentResponse:
    # Simulate the card processor: variable latency and a small failure rate.
    await asyncio.sleep(random.uniform(0.02, 0.15))
    if random.random() < FAILURE_RATE:
        raise HTTPException(status_code=502, detail="card processor declined")

    payment_id = str(uuid.uuid4())
    async with httpx.AsyncClient(base_url=NOTIFICATION_URL, timeout=2.0) as client:
        try:
            await client.post(
                "/notifications",
                json={"order_id": request.order_id, "channel": "email", "event": "payment_ok"},
            )
        except httpx.HTTPError:
            # Notification is best effort. The payment still succeeds.
            pass

    return PaymentResponse(payment_id=payment_id, order_id=request.order_id, status="PAID")
