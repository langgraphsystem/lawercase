# -*- coding: utf-8 -*-
"""A self-contained FastAPI app for security integration tests."""

import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_403_FORBIDDEN

# --- Configuration ---
SECRET_KEY = "a_very_secret_key"
ALGORITHM = "HS256"
ALLOWED_ORIGINS = ["http://localhost:3000", "https://example.com"]

# --- JWT Generation for Tests ---
def create_test_token(payload: dict, expires_delta: timedelta = timedelta(minutes=15)):
    to_encode = payload.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Security Dependencies ---
auth_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(auth_scheme)):
    """Dependency to validate JWT and extract user info."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
            raise HTTPException(status_code=401, detail="Token has expired")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(required_role: str):
    """Dependency factory to enforce role-based access control."""
    def role_checker(current_user: dict = Depends(get_current_user)):
        roles = current_user.get("roles", [])
        if required_role not in roles:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource"
            )
        return current_user
    return role_checker

# --- FastAPI App ---
app = FastAPI()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
@app.get("/public")
def public_route():
    return {"message": "This is a public route"}

@app.get("/protected", dependencies=[Depends(get_current_user)])
def protected_route():
    return {"message": "This is a protected route"}

@app.get("/admin", dependencies=[Depends(require_role("admin"))])
def admin_route():
    return {"message": "This is an admin-only route"}
