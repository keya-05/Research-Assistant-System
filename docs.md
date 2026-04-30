# Research Assistant - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Backend Documentation](#backend-documentation)
4. [Frontend Documentation](#frontend-documentation)
5. [Database Schema](#database-schema)
6. [Authentication System](#authentication-system)
7. [Google OAuth Setup](#google-oauth-setup)
8. [API Endpoints](#api-endpoints)
9. [Common Issues & Solutions](#common-issues--solutions)
10. [Deployment Guide](#deployment-guide)

---

## Project Overview

A multi-agent AI research system built with FastAPI (backend) and React (frontend). The system uses LangGraph for orchestrating multiple AI agents (Research, Summarization, Verification) to answer research questions with confidence scoring.

### Key Features
- JWT-based authentication with Google OAuth + email/password
- Multi-agent research pipeline
- Conversation management with JSONB storage
- PostgreSQL database with NeonDB compatibility
- Caching for repeated queries
- RESTful API with FastAPI

---

## Architecture

```
Research-Assistant-System/
├── backend/
│   ├── src/                    # Main source code
│   │   ├── agents/            # LangGraph multi-agent system
│   │   │   ├── agents/        # Individual agent implementations
│   │   │   ├── graph/         # Workflow/state definitions
│   │   │   └── utils/         # LLM utilities
│   │   ├── api/               # API routes & middleware
│   │   ├── db/                # Database operations
│   │   ├── models/            # Pydantic schemas
│   │   └── services/          # Business logic
│   ├── main.py                # FastAPI entry point
│   ├── schema.sql             # Database schema (for NeonDB)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── context/          # Auth context
│   │   ├── App.jsx           # Main app
│   │   └── index.css         # Styling
└── docs.md                   # This file
```

---

## Backend Documentation

### File: `main.py`
**Purpose**: FastAPI application entry point and route definitions.

**Key Components**:
- `lifespan()`: Async context manager for startup/shutdown (initializes DB)
- CORS middleware configuration
- Route definitions split into public and protected endpoints

**Routes**:
- `GET /health` - Health check (public)
- `POST /auth/register` - User registration with email/password (public)
- `POST /auth/login` - User login with email/password (public)
- `POST /auth/google` - Google OAuth login/registration (public)
- `POST /conversations` - Create conversation (protected)
- `GET /conversations/{id}` - Get conversation (protected)
- `POST /query` - Research query (protected)

**Why this structure?**
Separating route handlers into `src/api/routes.py` keeps main.py clean and focused on app configuration.

---

### File: `src/db/database.py`
**Purpose**: All database operations using asyncpg.

**Key Functions**:
- `get_pool()`: Returns asyncpg connection pool (singleton pattern)
- `init_db()`: Creates tables on startup
- `create_user()`: Creates new user (supports email/password or Google OAuth)
- `get_user_by_google_id()`: Gets user by Google ID
- `create_conversation()`: Creates conversation for user
- `add_message_to_conversation()`: Appends to JSONB array
- `get_cached_query()`: Searches for existing answers

**JSONB Schema Explanation**:
Instead of separate tables for each message, we store all messages in a JSONB array:
```sql
messages: [
  {
    "question": "...",
    "answer": "...",
    "sources": [...],
    "confidence": "high",
    "timestamp": "..."
  }
]
```

**Why JSONB?**
- Flexible schema (easy to add fields later)
- Atomic operations per conversation
- Efficient for read-heavy workloads
- Native PostgreSQL support for querying

---

### File: `src/services/auth_service.py`
**Purpose**: Password hashing and JWT token management.

**Key Functions**:
- `get_password_hash()`: bcrypt password hashing with 72-byte truncation
- `verify_password()`: bcrypt verification
- `create_access_token()`: JWT token generation
- `decode_access_token()`: JWT verification

**The bcrypt 72-byte Issue**:
bcrypt has a fundamental limit of 72 bytes for passwords. We encountered:
```
ValueError: password cannot be longer than 72 bytes
```

**Solution**:
```python
def _truncate_password(password: str) -> bytes:
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return password_bytes
```

We use bcrypt directly instead of passlib to avoid compatibility issues with newer bcrypt versions.

---

### File: `src/services/google_auth_service.py`
**Purpose**: Google OAuth token verification.

**Key Functions**:
- `verify_google_token(token)`: Verifies Google ID token and returns user info

**How it works**:
1. Frontend gets Google ID token via Google Sign-In button
2. Frontend sends token to backend `/auth/google`
3. Backend verifies token with Google's servers
4. If valid, backend gets user's email, name, and Google ID
5. Backend creates new user or logs in existing user

---

### File: `src/api/auth_routes.py`
**Purpose**: Authentication business logic.

**Registration Flow (Email/Password)**:
1. Check if email exists
2. Hash password (with truncation for bcrypt 72-byte limit)
3. Create user
4. Generate JWT token
5. Return token + user data (auto-login after registration)

**Login Flow (Email/Password)**:
1. Find user by email
2. Verify password
3. Generate JWT token
4. Return token + user data

**Google OAuth Flow**:
1. Verify Google ID token with Google's servers
2. Check if user exists by Google ID
3. If new user: create account with Google info (no password needed)
4. Generate JWT token
5. Return token + user data

---

### File: `src/api/auth_middleware.py`
**Purpose**: JWT token validation for protected routes.

**Key Components**:
- `HTTPBearer`: FastAPI security scheme
- `get_current_user()`: Dependency for protected routes
- `get_optional_user()`: Optional auth (not currently used)

**Usage in Routes**:
```python
@app.post("/query")
async def query(req: QueryRequest, current_user: UserResponse = Depends(get_current_user)):
    # User is authenticated
```

---

### File: `src/models/schemas.py`
**Purpose**: Pydantic models for request/response validation.

**Models**:
- `UserCreate`: Registration request (email, password, full_name)
- `UserLogin`: Login request (email, password)
- `GoogleLogin`: Google OAuth request (token)
- `UserResponse`: User data response (no password)
- `TokenResponse`: Login response (token + user)
- `QueryRequest`: Research query (question, conversation_id)
- `QueryResponse`: Research answer (answer, sources, confidence, etc.)

**Validation**:
- Email format validation via `EmailStr`
- Password minimum 8 characters
- Question length 5-2000 characters

---

## Frontend Documentation

### File: `src/context/AuthContext.jsx`
**Purpose**: Global authentication state management.

**Key Functions**:
- `login(email, password)`: Authenticates with email/password
- `register(email, password, fullName)`: Creates account with email/password
- `googleLogin(googleToken)`: Authenticates with Google OAuth
- `apiCall(endpoint, options)`: Authenticated API wrapper
- `logout()`: Clears token

**Token Storage**:
- Stored in `localStorage`
- Automatically added to API calls via `Authorization: Bearer <token>`
- 401 responses trigger logout

---

### File: `src/components/AuthModal.jsx`
**Purpose**: Login/Register modal UI with Google Sign-In.

**Features**:
- Email/password login and registration
- Google Sign-In button (via Google Identity Services)
- Toggle between login/register modes
- Error handling

**Google Sign-In Flow**:
1. User clicks Google Sign-In button
2. Google's popup opens for account selection
3. Google returns ID token to frontend
4. Frontend sends token to backend `/auth/google`
5. Backend verifies and returns JWT token
6. User is logged in immediately

---

### File: `src/App.jsx`
**Purpose**: Main application component.

**Components**:
- `AppContent`: Main research assistant UI
- `ConfidenceBadge`, `ResultCard`, `Loading`: UI components

---

## Database Schema

### Tables

**users**
```sql
id SERIAL PRIMARY KEY
email VARCHAR(255) UNIQUE NOT NULL
hashed_password VARCHAR(255)  -- NULL for Google OAuth users
full_name VARCHAR(255)
email_verified BOOLEAN DEFAULT FALSE
google_id VARCHAR(255) UNIQUE  -- Google OAuth user ID (NULL for email/password users)
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()
```

**conversations**
```sql
id SERIAL PRIMARY KEY
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()
```

**conversation_messages (JSONB)**
```sql
id SERIAL PRIMARY KEY
conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE
messages JSONB NOT NULL DEFAULT '[]'
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()
```

**queries (legacy)**
```sql
id SERIAL PRIMARY KEY
question TEXT NOT NULL
answer TEXT NOT NULL
sources JSONB NOT NULL DEFAULT '[]'
confidence VARCHAR(10) NOT NULL
created_at TIMESTAMPTZ DEFAULT NOW()
```

---

## Authentication System

### JWT Token Structure
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "exp": 1234567890
}
```

### Protected vs Public Endpoints

**Public** (no token needed):
- `/health`
- `/auth/register`
- `/auth/login`
- `/auth/verify-email`

**Protected** (token required):
- `/conversations` (POST)
- `/conversations/{id}` (GET)
- `/query` (POST)

### Security Flow
1. User registers (email/password or Google OAuth) → auto-logged in
2. User receives JWT token immediately
3. Token sent in `Authorization: Bearer <token>` header
4. Server validates token on protected routes

### Authentication Methods

**Email/Password**:
- User provides email and password
- Password hashed with bcrypt (truncated to 72 bytes if needed)
- JWT token returned on successful login/registration

**Google OAuth**:
- User clicks Google Sign-In button
- Google handles authentication
- Backend receives verified Google ID token
- User created if new, or logged in if existing
- JWT token returned

Both methods return the same JWT token format for API access.

---

## Google OAuth Setup

### 1. Create Google OAuth Credentials
1. Go to https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"
4. Add authorized JavaScript origins:
   - `http://localhost:5173` (for development)
   - `https://yourdomain.com` (for production)
5. Save the Client ID

### 2. Configure Environment Variables

**Backend `.env`:**
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

**Frontend `.env`:**
```
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### 3. How Google OAuth Works
1. Google Sign-In button loads via Google's JS library
2. User clicks and selects their Google account
3. Google returns an ID token (JWT) to the frontend
4. Frontend sends token to backend `/auth/google`
5. Backend verifies token with Google's API
6. If valid:
   - New user: Create account with Google info (email, name, Google ID)
   - Existing user: Log them in
7. Backend returns JWT token for API access

### Development Mode
If `GOOGLE_CLIENT_ID` is not set in backend, the server accepts any token and creates a mock user for testing. **DO NOT use in production.**

---

## API Endpoints

### POST /auth/register
Registers user with email/password and auto-logs them in.

Request:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

### POST /auth/login
Authenticates user with email/password.
Request:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

### POST /query (Protected)
Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "question": "What is AI?",
  "conversation_id": null
}
```

Response:
```json
{
  "answer": "AI is...",
  "sources": ["https://..."],
  "confidence": "high",
  "cached": false,
  "conversation_id": 1,
  "message_id": 0
}
```

---

## Common Issues & Solutions

### Issue 1: bcrypt password length error
**Error**: `ValueError: password cannot be longer than 72 bytes`

**Solution**: Truncate passwords to 72 bytes before hashing:
```python
password_bytes = password.encode('utf-8')
if len(password_bytes) > 72:
    password_bytes = password_bytes[:72]
```

### Issue 2: Python cache not updating
**Symptom**: Changes to code don't take effect

**Solution**: Clear `__pycache__` directories:
```powershell
Remove-Item -Recurse -Path "backend/__pycache__"
Remove-Item -Recurse -Path "backend/src/__pycache__"
```

### Issue 3: CORS errors
**Error**: `Access-Control-Allow-Origin` header missing

**Solution**: CORS middleware is configured in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origin in production
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### Issue 4: Database connection fails
**Error**: `connection refused` or `database does not exist`

**Solution**: Check `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://user:password@host:port/database
```

### Issue 5: Google OAuth not working
**Symptom**: Google Sign-In button doesn't appear or fails

**Solution**: 
1. Check `VITE_GOOGLE_CLIENT_ID` is set in frontend `.env`
2. Check `GOOGLE_CLIENT_ID` is set in backend `.env`
3. Verify authorized JavaScript origins in Google Console match your domain
4. Check browser console for JavaScript errors
5. Ensure you're not using ad blockers that block Google scripts

---

## Deployment Guide

### NeonDB Setup
1. Create Neon project at https://neon.tech
2. Get connection string from dashboard
3. Set `DATABASE_URL` in environment variables
4. Run schema:
   ```bash
   psql $DATABASE_URL -f schema.sql
   ```

### Backend Deployment (Railway/Render/Heroku)
1. Set environment variables:
   - `DATABASE_URL`
   - `SECRET_KEY` (random string)
   - `GOOGLE_CLIENT_ID` (for OAuth, optional)

2. Deploy with:
   ```bash
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Frontend Deployment (Vercel/Netlify)
1. Set build command: `npm run build`
2. Set output directory: `dist`
3. Set environment variables:
   - `VITE_API_BASE`: your backend URL
   - `VITE_GOOGLE_CLIENT_ID`: your Google OAuth Client ID

---

## Redundant Files to Remove

These files are from the old structure and should be removed:
- `backend/agents.py` - Replaced by `src/agents/`
- `backend/database.py` - Replaced by `src/db/database.py`
- `backend/Agents/` - Moved to `src/agents/`
- `backend/app/` - Old restructuring attempt
- `backend/__pycache__/` - Python cache

Keep:
- `backend/main.py` - Entry point
- `backend/src/` - All source code
- `backend/schema.sql` - Database setup
- `backend/requirements.txt` - Dependencies

### Removed Files (Email Verification Era)
These were removed when switching to Google OAuth:
- `backend/src/services/email_service.py`
- `frontend/src/components/VerifyEmail.jsx`
- `frontend/src/components/VerifyEmail.css`

---

## Summary

This system uses:
- **FastAPI** for async API endpoints
- **PostgreSQL + JSONB** for flexible data storage
- **bcrypt** for secure password hashing (with 72-byte limit handling)
- **JWT** for stateless authentication
- **LangGraph** for multi-agent orchestration
- **React Context** for frontend auth state
- **Google OAuth** for easy, secure authentication

All sensitive operations require authentication. Users can log in via Google OAuth (one-click) or traditional email/password.
