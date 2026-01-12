import os
import time
import logging
from datetime import timedelta
from typing import List, Union, Optional
from fastapi import FastAPI, HTTPException, Body, Security, Request, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import tigerbeetle as tb
from dotenv import load_dotenv

# SlowAPI for rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .models import (
    AccountCreate, AccountResponse, TransferCreate, TransferResponse,
    AccountFilter, AccountBalance, QueryFilter,
    UserCreate, UserResponse, Token, StandardResponse,
    AccountBalanceQuery
)
from .client import get_client
from .auth import (
    verify_password, get_password_hash, create_access_token, decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .database import SessionLocal, engine, init_db, get_db, DBUser
from . import crud

# Environment and Config
load_dotenv()
ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "admin@tigerbeetle.com")
ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "tigerbeetle")
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TigerBeetleAPI")

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

# --- Security Dependencies ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None:
        logger.warning(f"Invalid token or decoding failed: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload.get("sub")
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_current_active_user(current_user: DBUser = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user. Contact administrator.")
    return current_user

async def get_current_superuser(current_user: DBUser = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser privileges required")
    return current_user

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Database...")
    init_db()
    
    # Ensure Super Admin exists
    db = SessionLocal()
    try:
        admin = crud.get_user_by_email(db, ADMIN_EMAIL)
        if not admin:
            logger.info(f"Creating default super admin: {ADMIN_EMAIL}")
            crud.create_user(db, UserCreate(email=ADMIN_EMAIL, password=ADMIN_PASSWORD), is_superuser=True)
    finally:
        db.close()
        
    logger.info("Starting up TigerBeetle REST API Bridge...")
    yield
    # Shutdown
    logger.info("Shutting down...")
    try:
        client = get_client()
        client.close()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="TigerBeetle REST API",
    description="An enterprise-grade RESTful wrapper for the TigerBeetle financial database.",
    version="1.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global Rate Limit Exception Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Global Exception Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=StandardResponse(
            status="error",
            code=500,
            message="Internal server error. Please contact administrator.",
            errors=[{"detail": str(exc)}]
        ).model_dump()
    )

# --- Middleware ---

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(time.time()))
    
    response = await call_next(request)
    
    duration = (time.perf_counter() - start_time) * 1000
    logger.info(f"RID:{request_id} {request.method} {request.url.path} - {response.status_code} ({duration:.2f}ms)")
    response.headers["X-Request-ID"] = request_id
    return response

def to_int(val: Union[int, str]) -> int:
    return int(val) if isinstance(val, str) else val

# --- Auth Endpoints ---

@app.post("/v1/auth/register", response_model=StandardResponse[UserResponse], tags=["Auth"], summary="Register a New User")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        return StandardResponse(
            status="error",
            code=400,
            message="Email already registered",
            errors=[{"field": "email", "message": "Email already exists"}]
        )
    new_user = crud.create_user(db, user=user)
    return StandardResponse(
        status="success",
        code=200,
        message="User registered successfully. Please contact admin for activation.",
        data=UserResponse.model_validate(new_user)
    )

@app.post("/v1/auth/token", response_model=Token, tags=["Auth"], summary="Login for Access Token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive. Please contact an admin.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Admin Endpoints ---

@app.get("/v1/admin/users", response_model=StandardResponse[List[UserResponse]], tags=["Admin"], summary="List All Users")
async def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: DBUser = Depends(get_current_superuser)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return StandardResponse(
        status="success",
        code=200,
        message="Users retrieved successfully",
        data=[UserResponse.model_validate(u) for u in users]
    )

@app.post("/v1/admin/users/{user_id}/activate", response_model=StandardResponse[UserResponse], tags=["Admin"], summary="Activate a User")
async def activate_user(user_id: int, db: Session = Depends(get_db), current_user: DBUser = Depends(get_current_superuser)):
    user = crud.update_user_status(db, user_id, is_active=True)
    if not user:
        return StandardResponse(status="error", code=404, message="User not found")
    return StandardResponse(
        status="success",
        code=200,
        message="User activated successfully",
        data=UserResponse.model_validate(user)
    )

@app.post("/v1/admin/users/{user_id}/deactivate", response_model=StandardResponse[UserResponse], tags=["Admin"], summary="Deactivate a User")
async def deactivate_user(user_id: int, db: Session = Depends(get_db), current_user: DBUser = Depends(get_current_superuser)):
    user = crud.update_user_status(db, user_id, is_active=False)
    if not user:
        return StandardResponse(status="error", code=404, message="User not found")
    return StandardResponse(
        status="success",
        code=200,
        message="User deactivated successfully",
        data=UserResponse.model_validate(user)
    )

# --- System Endpoints ---

@app.get("/health", tags=["System"], summary="Health Check")
async def health():
    return {"status": "ok", "timestamp": time.time()}

# --- TigerBeetle Endpoints ---

@app.post(
    "/v1/accounts",
    response_model=StandardResponse[List[dict]],
    tags=["Accounts"],
    summary="Batch Create Accounts",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def create_accounts(request: Request, accounts: List[AccountCreate]):
    client = get_client()
    tb_accounts = []
    for acc in accounts:
        tb_acc = tb.Account()
        tb_acc.id = to_int(acc.id)
        tb_acc.debits_pending = to_int(acc.debits_pending)
        tb_acc.debits_posted = to_int(acc.debits_posted)
        tb_acc.credits_pending = to_int(acc.credits_pending)
        tb_acc.credits_posted = to_int(acc.credits_posted)
        tb_acc.user_data_128 = to_int(acc.user_data_128)
        tb_acc.user_data_64 = to_int(acc.user_data_64)
        tb_acc.user_data_32 = acc.user_data_32
        tb_acc.ledger = acc.ledger
        tb_acc.code = acc.code
        tb_acc.flags = acc.flags
        tb_acc.timestamp = to_int(acc.timestamp)
        tb_accounts.append(tb_acc)
    
    results = client.create_accounts(tb_accounts)
    
    if not results:
        return StandardResponse(
            status="success",
            code=200,
            message="All accounts created successfully",
            data=[]
        )
    
    errors = []
    for res in results:
        try:
            # Map error code to string name if available
            error_name = tb.CreateAccountResult(res.result).name
        except Exception:
            error_name = "UNKNOWN_ERROR"
            
        errors.append({
            "index": res.index,
            "error_code": int(res.result),
            "error": error_name
        })
        
    return StandardResponse(
        status="partial_error",
        code=400,
        message="Some accounts failed to create",
        data=None,
        errors=errors
    )

@app.post(
    "/v1/accounts/lookup",
    response_model=StandardResponse[List[AccountResponse]],
    tags=["Accounts"],
    summary="Lookup Accounts",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def lookup_accounts(request: Request, ids: List[Union[int, str]] = Body(...)):
    client = get_client()
    tb_ids = [to_int(id) for id in ids]
    accounts = client.lookup_accounts(tb_ids)
    
    resp = []
    for acc in accounts:
        resp.append(AccountResponse(
            id=str(acc.id),
            user_data_128=str(acc.user_data_128),
            user_data_64=str(acc.user_data_64),
            user_data_32=acc.user_data_32,
            ledger=acc.ledger,
            code=acc.code,
            flags=acc.flags,
            debits_pending=str(acc.debits_pending),
            debits_posted=str(acc.debits_posted),
            credits_pending=str(acc.credits_pending),
            credits_posted=str(acc.credits_posted),
            timestamp=str(acc.timestamp)
        ))
    
    return StandardResponse(
        status="success",
        code=200,
        message=f"Found {len(resp)} accounts",
        data=resp
    )

@app.post(
    "/v1/transfers",
    response_model=StandardResponse[List[dict]],
    tags=["Transfers"],
    summary="Batch Create Transfers",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def create_transfers(request: Request, transfers: List[TransferCreate]):
    client = get_client()
    tb_transfers = []
    for t in transfers:
        tb_t = tb.Transfer()
        tb_t.id = to_int(t.id)
        tb_t.debit_account_id = to_int(t.debit_account_id)
        tb_t.credit_account_id = to_int(t.credit_account_id)
        tb_t.amount = to_int(t.amount)
        tb_t.pending_id = to_int(t.pending_id)
        tb_t.user_data_128 = to_int(t.user_data_128)
        tb_t.user_data_64 = to_int(t.user_data_64)
        tb_t.user_data_32 = t.user_data_32
        tb_t.timeout = t.timeout
        tb_t.ledger = t.ledger
        tb_t.code = t.code
        tb_t.flags = t.flags
        tb_t.timestamp = to_int(t.timestamp)
        tb_transfers.append(tb_t)
    
    results = client.create_transfers(tb_transfers)
    
    if not results:
        return StandardResponse(
            status="success",
            code=200,
            message="All transfers created successfully",
            data=[]
        )

    errors = []
    for res in results:
        try:
            error_name = tb.CreateTransferResult(res.result).name
        except Exception:
            error_name = "UNKNOWN_ERROR"
            
        errors.append({
            "index": res.index,
            "error_code": int(res.result),
            "error": error_name
        })
        
    return StandardResponse(
        status="partial_error",
        code=400,
        message="Some transfers failed to create",
        data=None,
        errors=errors
    )

@app.post(
    "/v1/transfers/lookup",
    response_model=StandardResponse[List[TransferResponse]],
    tags=["Transfers"],
    summary="Lookup Transfers",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def lookup_transfers(request: Request, ids: List[Union[int, str]] = Body(...)):
    client = get_client()
    tb_ids = [to_int(id) for id in ids]
    transfers = client.lookup_transfers(tb_ids)
    
    resp = []
    for t in transfers:
        resp.append(TransferResponse(
            id=str(t.id),
            debit_account_id=str(t.debit_account_id),
            credit_account_id=str(t.credit_account_id),
            amount=str(t.amount),
            pending_id=str(t.pending_id),
            user_data_128=str(t.user_data_128),
            user_data_64=str(t.user_data_64),
            user_data_32=t.user_data_32,
            timeout=t.timeout,
            ledger=t.ledger,
            code=t.code,
            flags=t.flags,
            timestamp=str(t.timestamp)
        ))
    
    return StandardResponse(
        status="success",
        code=200,
        message=f"Found {len(resp)} transfers",
        data=resp
    )

@app.post(
    "/v1/accounts/balances",
    response_model=StandardResponse[List[AccountBalance]],
    tags=["Accounts"],
    summary="Get Account Balances",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def get_account_balances(request: Request, filter: AccountBalanceQuery):
    client = get_client()
    tb_filter = tb.AccountFilter()
    tb_filter.account_id = to_int(filter.account_id)
    tb_filter.user_data_128 = to_int(filter.user_data_128)
    tb_filter.user_data_64 = to_int(filter.user_data_64)
    tb_filter.user_data_32 = filter.user_data_32
    tb_filter.code = filter.code
    tb_filter.timestamp_min = filter.timestamp_min
    tb_filter.timestamp_max = filter.timestamp_max
    tb_filter.limit = filter.limit
    tb_filter.flags = filter.flags
    
    balances = client.get_account_balances(tb_filter)
    resp = []
    for b in balances:
        resp.append(AccountBalance(
            debits_pending=str(b.debits_pending),
            debits_posted=str(b.debits_posted),
            credits_pending=str(b.credits_pending),
            credits_posted=str(b.credits_posted),
            timestamp=str(b.timestamp)
        ))
    
    return StandardResponse(
        status="success",
        code=200,
        message="Balances retrieved successfully",
        data=resp
    )

@app.post(
    "/v1/accounts/transfers",
    response_model=StandardResponse[List[TransferResponse]],
    tags=["Accounts"],
    summary="Get Account Transfer History",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def get_account_transfers(request: Request, filter: AccountFilter):
    client = get_client()
    tb_filter = tb.AccountFilter()
    tb_filter.account_id = to_int(filter.account_id)
    tb_filter.user_data_128 = to_int(filter.user_data_128)
    tb_filter.user_data_64 = to_int(filter.user_data_64)
    tb_filter.user_data_32 = filter.user_data_32
    tb_filter.code = filter.code
    tb_filter.timestamp_min = filter.timestamp_min
    tb_filter.timestamp_max = filter.timestamp_max
    tb_filter.limit = filter.limit
    tb_filter.flags = filter.flags
    
    transfers = client.get_account_transfers(tb_filter)
    resp = []
    for t in transfers:
        resp.append(TransferResponse(
            id=str(t.id),
            debit_account_id=str(t.debit_account_id),
            credit_account_id=str(t.credit_account_id),
            amount=str(t.amount),
            pending_id=str(t.pending_id),
            user_data_128=str(t.user_data_128),
            user_data_64=str(t.user_data_64),
            user_data_32=t.user_data_32,
            timeout=t.timeout,
            ledger=t.ledger,
            code=t.code,
            flags=t.flags,
            timestamp=str(t.timestamp)
        ))
        
    return StandardResponse(
        status="success",
        code=200,
        message=f"Found {len(resp)} related transfers",
        data=resp
    )

@app.post(
    "/v1/accounts/query",
    response_model=StandardResponse[List[AccountResponse]],
    tags=["Accounts"],
    summary="Query Accounts",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def query_accounts(request: Request, filter: QueryFilter):
    client = get_client()
    tb_filter = tb.QueryFilter()
    tb_filter.ledger = filter.ledger
    tb_filter.code = filter.code
    tb_filter.user_data_128 = to_int(filter.user_data_128)
    tb_filter.user_data_64 = to_int(filter.user_data_64)
    tb_filter.user_data_32 = filter.user_data_32
    tb_filter.timestamp_min = filter.timestamp_min
    tb_filter.timestamp_max = filter.timestamp_max
    tb_filter.limit = filter.limit
    tb_filter.flags = filter.flags
    
    accounts = client.query_accounts(tb_filter)
    resp = []
    for acc in accounts:
        resp.append(AccountResponse(
            id=str(acc.id),
            user_data_128=str(acc.user_data_128),
            user_data_64=str(acc.user_data_64),
            user_data_32=acc.user_data_32,
            ledger=acc.ledger,
            code=acc.code,
            flags=acc.flags,
            debits_pending=str(acc.debits_pending),
            debits_posted=str(acc.debits_posted),
            credits_pending=str(acc.credits_pending),
            credits_posted=str(acc.credits_posted),
            timestamp=str(acc.timestamp)
        ))
    
    return StandardResponse(
        status="success",
        code=200,
        message=f"Query returned {len(resp)} accounts",
        data=resp
    )

@app.post(
    "/v1/transfers/query",
    response_model=StandardResponse[List[TransferResponse]],
    tags=["Transfers"],
    summary="Query Transfers",
    dependencies=[Depends(get_current_active_user)]
)
@limiter.limit(RATE_LIMIT)
async def query_transfers(request: Request, filter: QueryFilter):
    client = get_client()
    tb_filter = tb.QueryFilter()
    tb_filter.ledger = filter.ledger
    tb_filter.code = filter.code
    tb_filter.user_data_128 = to_int(filter.user_data_128)
    tb_filter.user_data_64 = to_int(filter.user_data_64)
    tb_filter.user_data_32 = filter.user_data_32
    tb_filter.timestamp_min = filter.timestamp_min
    tb_filter.timestamp_max = filter.timestamp_max
    tb_filter.limit = filter.limit
    tb_filter.flags = filter.flags
    
    transfers = client.query_transfers(tb_filter)
    resp = []
    for t in transfers:
        resp.append(TransferResponse(
            id=str(t.id),
            debit_account_id=str(t.debit_account_id),
            credit_account_id=str(t.credit_account_id),
            amount=str(t.amount),
            pending_id=str(t.pending_id),
            user_data_128=str(t.user_data_128),
            user_data_64=str(t.user_data_64),
            user_data_32=t.user_data_32,
            timeout=t.timeout,
            ledger=t.ledger,
            code=t.code,
            flags=t.flags,
            timestamp=str(t.timestamp)
        ))
    
    return StandardResponse(
        status="success",
        code=200,
        message=f"Query returned {len(resp)} transfers",
        data=resp
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
