from __future__ import annotations

from pydantic import BaseModel, Field


class DepositUtxosRequest(BaseModel):
    address: str | None = None
    addresses: list[str] | None = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    exclude_claimed: bool = True


class TransfersRequest(BaseModel):
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    created_after: str | None = None
    created_before: str | None = None


class IdentifierRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=512)


class TokenTransactionsRequest(BaseModel):
    transaction_hashes: list[str] | None = None
    token_identifier: str | None = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    created_after: str | None = None
    created_before: str | None = None
