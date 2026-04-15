# Agent Monitor API

This project is a small AI monitoring backend built with FastAPI, PostgreSQL, token-based authentication, and an LLM-backed summary endpoint.

## What the system does

- Stores monitored agents in PostgreSQL.
- Protects API routes with a bearer token.
- Supports CRUD operations for agents.
- Generates one-line health summaries for agents by calling the OpenRouter chat completions API.
- Applies rate limiting on the summary endpoint.

## Current architecture

- `app/main.py`: FastAPI app setup, router registration, rate-limit handler.
- `app/database.py`: SQLAlchemy engine, session factory, base model.
- `app/models.py`: `Agent` table definition.
- `app/auth.py`: bearer-token verification.
- `app/routers/agents.py`: create, read, update, delete agent endpoints.
- `app/routers/summary.py`: LLM-powered summary endpoint with in-memory caching.

## API flow

1. Client sends a request with `Authorization: Bearer <API_TOKEN>`.
2. FastAPI validates the token in `app/auth.py`.
3. CRUD routes read or write agent rows in PostgreSQL.
4. `/agents-summary/` loads all agents from the database.
5. Each agent status is sent to OpenRouter to generate a short health summary.
6. Summaries are cached in memory by status to avoid repeated external calls.

## Endpoints

### Health

- `GET /`

Example response:

```json
{
  "message": "Agent Monitor API running"
}
```

### Create agent

- `POST /agents/`

Request body:

```json
{
  "name": "Planner-01",
  "agent_type": "planner",
  "status": "healthy"
}
```

### List agents

- `GET /agents/`
- Optional query params: `status`, `limit`, `offset`

Example:

```text
GET /agents/?status=healthy&limit=5&offset=0
```

### Get one agent

- `GET /agents/{agent_id}`

### Update status

- `PUT /agents/{agent_id}?status=degraded`

### Delete agent

- `DELETE /agents/{agent_id}`

### Generate summaries

- `GET /agents-summary/`

This endpoint is rate-limited to `10/minute`.

## Running the API

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the server:

```powershell
uvicorn app.main:app --reload
```

Open docs:

- [Swagger UI](http://127.0.0.1:8000/docs)

## Environment variables

Create a `.env` file with:

```env
API_TOKEN=your-secret-token
OPENROUTER_API_KEY=your-openrouter-api-key
```

## Demonstrating the API

Use Swagger UI for the demo:

- [Swagger UI](http://127.0.0.1:8000/docs)

Recommended demo flow:

1. Authorize with your bearer token.
2. Create an agent with `POST /agents/`.
3. View agents with `GET /agents/`.
4. Update agent status with `PUT /agents/{agent_id}`.
5. Generate AI summaries with `GET /agents-summary/`.
6. Delete the demo agent with `DELETE /agents/{agent_id}`.

## Example cURL calls

Set your token first:

```powershell
$env:API_TOKEN = "your-secret-token"
```

Create:

```powershell
curl -X POST "http://127.0.0.1:8000/agents/" `
  -H "Authorization: Bearer $env:API_TOKEN" `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Planner-01\",\"agent_type\":\"planner\",\"status\":\"healthy\"}"
```

List:

```powershell
curl -X GET "http://127.0.0.1:8000/agents/" `
  -H "Authorization: Bearer $env:API_TOKEN"
```

Update:

```powershell
curl -X PUT "http://127.0.0.1:8000/agents/1?status=degraded" `
  -H "Authorization: Bearer $env:API_TOKEN"
```

Summaries:

```powershell
curl -X GET "http://127.0.0.1:8000/agents-summary/" `
  -H "Authorization: Bearer $env:API_TOKEN"
```

## Analysis: what is working well

- The structure is clean and easy to follow.
- Agent CRUD is separated from summary generation.
- Logging is present on important operations.
- Authentication is simple enough for local demos.
- Summary generation is asynchronous and uses `asyncio.gather`, which is a good fit for concurrent LLM calls.

## Analysis: main risks and improvement areas

- The database URL is hardcoded in code instead of being read from environment variables.
- Returning ORM objects directly can make API contracts less explicit than response models.
- The summary cache is process-local and disappears on restart.
- The OpenRouter response is not checked with `raise_for_status()`, so upstream failures may surface unclearly.
- The selected model string in `app/routers/summary.py` may not be the best long-term choice if provider availability changes.
- The root endpoint currently contains a non-ASCII rocket character that can display oddly on some Windows terminals.

## Recommended next upgrades

1. Move `DATABASE_URL` to `.env`.
2. Add Pydantic response models for agents and summaries.
3. Add `response.raise_for_status()` and better error messages in the LLM call.
4. Add tests for auth, CRUD, and summary failures.
5. Consider Redis or database-backed caching if this grows beyond a local demo.
