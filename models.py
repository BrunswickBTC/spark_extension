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


class SparkTransferRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=128)
    amount_sats: int = Field(..., gt=0)
    receiver_spark_address: str = Field(..., min_length=1, max_length=512)
    memo: str = Field("", max_length=640)


class TokenTransferRequest(BaseModel):
    token_identifier: str = Field(..., min_length=1, max_length=512)
    token_amount: int = Field(..., gt=0)
    receiver_spark_address: str = Field(..., min_length=1, max_length=512)
    output_selection_strategy: str | None = Field(None, max_length=64)


class WithdrawalQuoteRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=128)
    amount_sats: int = Field(..., gt=0)
    withdrawal_address: str = Field(..., min_length=1, max_length=256)
    exit_speed: str = Field("FAST", min_length=1, max_length=32)


class WithdrawalRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=128)
    onchain_address: str = Field(..., min_length=1, max_length=256)
    amount_sats: int | None = Field(None, gt=0)
    exit_speed: str = Field(..., min_length=1, max_length=32)
    fee_quote_id: str = Field(..., min_length=1, max_length=512)
    fee_amount_sats: int = Field(..., ge=0)
    deduct_fee_from_withdrawal_amount: bool = True
    memo: str = Field("", max_length=640)


class ReceiveAddressRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=128)


class DepositClaimRequest(BaseModel):
    deposit_id: str = Field(..., min_length=1, max_length=128)
    txid: str = Field(..., min_length=1, max_length=256)
    amount_sats: int = Field(..., gt=0)


class GlobalWalletRequest(BaseModel):
    wallet_id: str = Field(..., min_length=1, max_length=128)
