import os
import time

START_TIME = time.time()
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from dotenv import load_dotenv
from pydantic import BaseModel

import wintermute.orchestrator

load_dotenv()

SECRET_KEY = os.environ.get("WINTERMUTE_AUTH_KEY", "default_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="Wintermute API Gateway")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class ChatRequest(BaseModel):
    prompt: str

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Validate against WINTERMUTE_AUTH_KEY loaded from .env
    auth_key = os.environ.get("WINTERMUTE_AUTH_KEY")
    if not auth_key or form_data.password != auth_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    return username

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, current_user: str = Depends(get_current_user)):
    try:
        result = wintermute.orchestrator.process_request(request.prompt, yield_thoughts=False)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/telemetry")
async def telemetry_endpoint(current_user: str = Depends(get_current_user)):
    try:
        from src.neuromancer import memory_core
        memory_capacity = len(memory_core.collection.get()['ids'])
    except Exception:
        memory_capacity = 0

    try:
        from src.constructs.ssh_agent import ssh_manager
        active_constructs = len(ssh_manager.list_active_nodes())
    except Exception:
        active_constructs = 0
        
    return {
        "status": "ONLINE",
        "active_constructs": active_constructs,
        "memory_capacity": memory_capacity,
        "uptime_seconds": time.time() - START_TIME
    }
