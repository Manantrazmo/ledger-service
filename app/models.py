from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union, Any, Generic, TypeVar

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    status: str = Field(..., description="Status of the request: 'success', 'error', 'partial_error'")
    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Human readable message")
    data: Optional[T] = Field(None, description="Response payload")
    errors: Optional[List[dict]] = Field(None, description="List of errors if any")

# --- Account Models ---

class AccountBase(BaseModel):
    id: Union[int, str] = Field(..., description="128-bit unique account ID")
    debits_pending: Optional[Union[int, str]] = Field(0, description="Amount of debits reserved by pending transfers (Must be 0 on creation)")
    debits_posted: Optional[Union[int, str]] = Field(0, description="Amount of posted debits (Must be 0 on creation)")
    credits_pending: Optional[Union[int, str]] = Field(0, description="Amount of credits reserved by pending transfers (Must be 0 on creation)")
    credits_posted: Optional[Union[int, str]] = Field(0, description="Amount of posted credits (Must be 0 on creation)")
    user_data_128: Optional[Union[int, str]] = Field(0, description="128-bit secondary identifier")
    user_data_64: Optional[Union[int, str]] = Field(0, description="64-bit secondary identifier")
    user_data_32: Optional[int] = Field(0, description="32-bit secondary identifier")
    reserved: Optional[int] = Field(0, description="Reserved for future use (Must be 0)")
    ledger: int = Field(..., description="Unsigned 32-bit integer ledger identifier")
    code: int = Field(..., description="Unsigned 16-bit integer chart-of-accounts code (e.g. 718 for assets)")
    flags: Optional[int] = Field(0, description="Bitfield: 1=linked, 2=credits_must_not_exceed_debits, 4=debits_must_not_exceed_credits, 8=history, 16=imported")
    timestamp: Optional[Union[int, str]] = Field(0, description="Assigned by cluster, or provided if flags.imported is set")

class AccountCreate(AccountBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "1",
                    "debits_pending": "0",
                    "debits_posted": "0",
                    "credits_pending": "0",
                    "credits_posted": "0",
                    "user_data_128": "0",
                    "user_data_64": "0",
                    "user_data_32": 0,
                    "reserved": 0,
                    "ledger": 1,
                    "code": 718,
                    "flags": 8,
                    "timestamp": "0"
                }
            ]
        }
    )

class AccountResponse(AccountBase):
    pass

# --- Transfer Models ---

class TransferBase(BaseModel):
    id: Union[int, str] = Field(..., description="128-bit unique transfer ID")
    debit_account_id: Union[int, str] = Field(..., description="Source account ID")
    credit_account_id: Union[int, str] = Field(..., description="Destination account ID")
    amount: Union[int, str] = Field(..., description="Unsigned 64-bit amount")
    pending_id: Optional[Union[int, str]] = Field(0, description="Referenced pending transfer ID for void/post")
    user_data_128: Optional[Union[int, str]] = Field(0, description="128-bit secondary identifier")
    user_data_64: Optional[Union[int, str]] = Field(0, description="64-bit secondary identifier")
    user_data_32: Optional[int] = Field(0, description="32-bit secondary identifier")
    timeout: Optional[int] = Field(0, description="Seconds before a pending transfer times out")
    ledger: int = Field(..., description="Ledger identifier (Must match accounts)")
    code: int = Field(..., description="Transfer type code (User-defined)")
    flags: Optional[int] = Field(0, description="Bitfield: 1=linked, 2=pending, 4=post, 8=void, 16=imported, etc.")
    timestamp: Optional[Union[int, str]] = Field(0, description="Assigned by cluster, or provided if flags.imported is set")

class TransferCreate(TransferBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "101",
                    "debit_account_id": "1",
                    "credit_account_id": "2",
                    "amount": "5000",
                    "pending_id": "0",
                    "user_data_128": "0",
                    "user_data_64": "0",
                    "user_data_32": 0,
                    "timeout": 0,
                    "ledger": 1,
                    "code": 1,
                    "flags": 0,
                    "timestamp": "0"
                }
            ]
        }
    )

class TransferResponse(TransferBase):
    pass

# --- Filter Models ---

class AccountFilter(BaseModel):
    account_id: Union[int, str]
    user_data_128: Optional[Union[int, str]] = 0
    user_data_64: Optional[Union[int, str]] = 0
    user_data_32: Optional[int] = 0
    code: Optional[int] = 0
    timestamp_min: Optional[int] = 0
    timestamp_max: Optional[int] = 0
    limit: Optional[int] = 10
    flags: Optional[int] = 0

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "account_id": "1",
                    "user_data_128": "0",
                    "user_data_64": "0",
                    "user_data_32": 0,
                    "code": 0,
                    "timestamp_min": 0,
                    "timestamp_max": 0,
                    "limit": 10,
                    "flags": 0
                }
            ]
        }
    )

class AccountBalanceQuery(BaseModel):
    account_id: Union[int, str]
    user_data_128: Optional[Union[int, str]] = Field(0, description="Filter by user_data_128")
    user_data_64: Optional[Union[int, str]] = Field(0, description="Filter by user_data_64")
    user_data_32: Optional[int] = Field(0, description="Filter by user_data_32")
    code: Optional[int] = Field(0, description="Filter by code")
    timestamp_min: Optional[int] = Field(0, description="Filter by min timestamp")
    timestamp_max: Optional[int] = Field(0, description="Filter by max timestamp")
    limit: Optional[int] = Field(10, description="Limit results")
    flags: Optional[int] = Field(0, description="Filter flags")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "account_id": "1"
                }
            ]
        }
    )

class QueryFilter(BaseModel):
    ledger: Optional[int] = Field(0, description="Filter by ledger")
    code: Optional[int] = Field(0, description="Filter by chart-of-accounts code")
    user_data_128: Optional[Union[int, str]] = Field(0, description="Filter by user_data_128")
    user_data_64: Optional[Union[int, str]] = Field(0, description="Filter by user_data_64")
    user_data_32: Optional[int] = Field(0, description="Filter by user_data_32")
    timestamp_min: Optional[int] = Field(0, description="Minimum timestamp (inclusive)")
    timestamp_max: Optional[int] = Field(0, description="Maximum timestamp (inclusive)")
    limit: Optional[int] = Field(10, description="Max number of results to return")
    flags: Optional[int] = Field(0, description="Filter flags (e.g. reversed)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ledger": 1,
                    "code": 718,
                    "user_data_128": "0",
                    "user_data_64": "0",
                    "user_data_32": 0,
                    "timestamp_min": 0,
                    "timestamp_max": 0,
                    "limit": 5,
                    "flags": 0
                }
            ]
        }
    )

class AccountBalance(BaseModel):
    debits_pending: Union[int, str]
    debits_posted: Union[int, str]
    credits_pending: Union[int, str]
    credits_posted: Union[int, str]
    timestamp: Union[int, str]

# --- User & Auth Models ---

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
