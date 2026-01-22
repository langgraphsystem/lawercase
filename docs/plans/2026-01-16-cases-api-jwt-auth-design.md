# Cases API + JWT Auth Design

**Date:** 2026-01-16
**Status:** Approved

## Overview

Синхронизация frontend и backend для работы с кейсами через JWT аутентификацию.

## Problem

- Frontend вызывает `GET /cases` — endpoint не существует
- Backend имеет `case_management.py` но не подключён
- Нет аутентификации — `user_id` передаётся как query param

## Solution

### Architecture

```
Frontend (Next.js)                    Backend (FastAPI)
─────────────────                    ─────────────────
/login page                    ──►   POST /auth/login
  └─ форма email/password             └─ возвращает JWT token

/chat page (protected)         ──►   GET /cases (+ Bearer token)
  └─ fetchCases() с token             └─ case_management.py
  └─ case selector                        извлекает user_id из JWT

localStorage
  └─ хранит JWT token
```

### Flow

1. Пользователь заходит → редирект на `/login` если нет токена
2. Вводит credentials → backend возвращает JWT с `user_id` и `roles`
3. Frontend сохраняет токен в `localStorage`
4. Все запросы к `/cases` и `/agui/*` включают `Authorization: Bearer <token>`
5. Backend извлекает `user_id` из токена, фильтрует кейсы по владельцу

## Implementation Plan

### 1. Backend: Auth Endpoint

**New file:** `api/routes/auth.py`

```python
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt
from core.security.config import SecurityConfig

router = APIRouter()

DEMO_USERS = {
    "admin@eb1a.com": {"password": "<DEMO_PASSWORD>", "user_id": "admin-001", "roles": ["admin"]},
    "lawyer@eb1a.com": {"password": "<DEMO_PASSWORD>", "user_id": "lawyer-001", "roles": ["lawyer"]},
    "client@eb1a.com": {"password": "<DEMO_PASSWORD>", "user_id": "client-001", "roles": ["viewer"]},
}

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = DEMO_USERS.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    config = SecurityConfig()
    expires_delta = timedelta(hours=24)
    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": user["user_id"],
        "user_id": user["user_id"],
        "email": request.email,
        "roles": user["roles"],
        "exp": expire,
    }

    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)

    return TokenResponse(
        access_token=token,
        expires_in=int(expires_delta.total_seconds()),
    )
```

**Changes in `api/main.py`:**

```python
from api.routes import auth as auth_routes
from api.routes import case_management

app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(case_management.router, prefix="/cases", tags=["cases"])
```

### 2. Backend: Update Case Management

**Changes in `api/routes/case_management.py`:**

Replace `user_id: str = Query(...)` with `Depends(get_current_user)`:

```python
from api.deps import get_current_user
from typing import Optional

def get_user_id(user: dict) -> str:
    return user.get("sub") or user.get("user_id")

@router.get("", response_model=CaseListResponse)
async def list_cases(
    user: dict = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    # ... other params
):
    user_id = get_user_id(user)
    # ... rest of implementation
```

Add `id` alias in response model:

```python
class CaseResponse(BaseModel):
    id: str  # alias for case_id (frontend compatibility)
    case_id: str
    # ... rest of fields

    @validator("id", pre=True, always=True)
    def set_id(cls, v, values):
        return v or values.get("case_id")
```

### 3. Frontend: Auth Module

**New file:** `web/src/lib/auth.ts`

```typescript
import { API_BASE_URL } from "./agui";

const TOKEN_KEY = "eb1a_auth_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export async function login(email: string, password: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) return false;
    const { access_token } = await res.json();
    setToken(access_token);
    return true;
  } catch {
    return false;
  }
}

export function logout(): void {
  clearToken();
  window.location.href = "/login";
}

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
```

### 4. Frontend: Update Types

**Changes in `web/src/lib/agui.ts`:**

```typescript
import { getAuthHeaders } from "./auth";

export interface Case {
  id: string;
  case_id: string;
  title: string;
  description: string;
  case_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export async function fetchCases(): Promise<Case[]> {
  const response = await fetch(`${API_BASE_URL}/cases`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!response.ok) {
    if (response.status === 401) {
      window.location.href = "/login";
      return [];
    }
    throw new Error("Failed to fetch cases");
  }
  return response.json();
}
```

### 5. Frontend: Login Page

**New file:** `web/src/app/login/page.tsx`

Simple form with email/password fields, login button, error handling.

### 6. Frontend: Auth Guard

**New file:** `web/src/components/AuthGuard.tsx`

```typescript
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    } else {
      setChecking(false);
    }
  }, [router]);

  if (checking) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return <>{children}</>;
}
```

## User Storage

### Phase 1: Hardcoded (MVP)

```python
DEMO_USERS = {
    "admin@eb1a.com": {"password": "<DEMO_PASSWORD>", "user_id": "admin-001", "roles": ["admin"]},
    "lawyer@eb1a.com": {"password": "<DEMO_PASSWORD>", "user_id": "lawyer-001", "roles": ["lawyer"]},
    "client@eb1a.com": {"password": "<DEMO_PASSWORD>", "user_id": "client-001", "roles": ["viewer"]},
}
```

### Phase 2: Supabase Table (Later)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  roles TEXT[] DEFAULT '{viewer}',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## Security

- JWT signed with secret (existing `SecurityConfig`)
- Token expires in 24 hours
- HTTPS required in production
- Passwords hashed in Phase 2

## Test Data

Create 2-3 cases for `lawyer-001` user in Supabase for testing.

## Execution Order

1. Backend: auth endpoint
2. Backend: connect case_management on `/cases`
3. Backend: update case_management to use JWT
4. Frontend: auth module
5. Frontend: update agui.ts types and headers
6. Frontend: login page
7. Frontend: AuthGuard wrapper
8. Test locally
9. Deploy to Vercel/Railway
