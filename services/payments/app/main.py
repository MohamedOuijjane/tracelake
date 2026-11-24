"""Payments service: charges an order through a simulated card processor."""

import asyncio
import os
import random
import uuid

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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


@app.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=201,
    responses={402: {"description": "Card declined (business outcome, not an error)"}},
)
async def pay(request: PaymentRequest) -> PaymentResponse | JSONResponse:
    # Simulate the card processor: variable latency and a small decline rate.
    await asyncio.sleep(random.uniform(0.02, 0.15))
    if random.random() < FAILURE_RATE:
        # A decline is a business answer: 402, so the SERVER span is not ERROR.
        # 5xx stays for real failures of payments itself.
        return JSONResponse(
            status_code=402,
            content={"status": "DECLINED", "order_id": request.order_id, "reason": "card declined"},
        )

    return PaymentResponse(payment_id=str(uuid.uuid4()), order_id=request.order_id, status="PAID")
