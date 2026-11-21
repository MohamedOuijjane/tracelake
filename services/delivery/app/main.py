"""Delivery service: assigns a courier to a paid order and estimates the arrival time."""

import asyncio
import logging
import random
import uuid

from fastapi import FastAPI
from pydantic import BaseModel, Field

log = logging.getLogger("delivery")
app = FastAPI(title="delivery")

COURIERS = [f"courier-{n:03d}" for n in range(1, 41)]


class DeliveryRequest(BaseModel):
    order_id: int
    restaurant_id: str
    preparation_minutes: int = Field(ge=0)
    address: str = "unknown"


class DeliveryResponse(BaseModel):
    delivery_id: str
    order_id: int
    courier_id: str
    eta_minutes: int
    status: str


@app.get("/health")
async def health() -> dict:
    return {"status": "UP"}


@app.post("/deliveries", response_model=DeliveryResponse, status_code=201)
async def assign(request: DeliveryRequest) -> DeliveryResponse:
    # Simulate the dispatch lookup for the nearest free courier.
    await asyncio.sleep(random.uniform(0.01, 0.06))
    courier_id = random.choice(COURIERS)
    # The courier rides to the restaurant while the kitchen cooks, then rides to the customer.
    pickup = max(request.preparation_minutes, random.randint(4, 12))
    eta = pickup + random.randint(8, 25)
    log.info("order %s assigned to %s, eta %s min", request.order_id, courier_id, eta)
    return DeliveryResponse(
        delivery_id=str(uuid.uuid4()),
        order_id=request.order_id,
        courier_id=courier_id,
        eta_minutes=eta,
        status="ASSIGNED",
    )
