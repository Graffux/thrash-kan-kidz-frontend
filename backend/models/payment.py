"""
Payment models
"""
from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime
import uuid


class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    package_id: str
    amount: float
    currency: str = "usd"
    coins_amount: int
    payment_status: str = "pending"  # pending, paid, failed, expired
    status: str = "initiated"  # initiated, completed, failed
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CoinPurchaseRequest(BaseModel):
    user_id: str
    package_id: str
    origin_url: str
