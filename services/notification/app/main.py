"""Notification service: accepts a notification request and pretends to send it."""

import asyncio
import logging
import random

from fastapi import FastAPI
from pydantic import BaseModel

log = logging.getLogger("notification")
app = FastAPI(title="notification")


class Notification(BaseModel):
    order_id: int
    channel: str = "email"
    event: str = "generic"


@app.get("/health")
async def health() -> dict:
    return {"status": "UP"}


@app.post("/notifications", status_code=202)
async def send(notification: Notification) -> dict:
    # Simulate the call to an email or SMS provider.
    await asyncio.sleep(random.uniform(0.005, 0.05))
    log.info(
        "queued %s for order %s via %s",
        notification.event,
        notification.order_id,
        notification.channel,
    )
    return {"status": "QUEUED", "order_id": notification.order_id}
