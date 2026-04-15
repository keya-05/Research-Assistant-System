# Ticketing API

This project is a small support ticketing backend built with FastAPI, PostgreSQL, bearer-token authentication, and OpenRouter-based ticket classification.

This system uses Human-in-the-Loop validation to ensure AI outputs are reviewed before final action.

## What it does

- Accepts a support ticket with `text` and `email`
- Uses an LLM to classify the ticket into:
  - `Billing`, `Technical`, or `General`
  - `High`, `Medium`, or `Low`
- Generates a short AI draft reply
- Adds a human-in-the-loop review step before approval or closure
- Tracks SLA deadlines for the human review stage
- Automatically logs escalations for high-priority tickets
- Falls back safely when the LLM response is missing or invalid
- Stores tickets in PostgreSQL
- Returns all tickets with category, urgency, status, sorting, and search options
- Protects endpoints with a bearer token
- Includes a lightweight browser frontend for ticket submission and review

## Project structure

- `app/main.py`: FastAPI app setup and router registration
- `app/database.py`: SQLAlchemy engine, session factory, base model
- `app/models.py`: `Ticket` and `EscalationLog` database models
- `app/services/tickets.py`: ticket classification, escalation, search, sorting, stats, and serialization logic
- `app/auth.py`: bearer-token verification
- `app/routers/tickets.py`: ticket create and list endpoints
- `app/static/`: browser frontend files

## Human-in-the-Loop workflow

- New tickets are created with status `needs_review`
- A human reviewer can approve the AI output, correct category or urgency, edit the draft reply, or close the ticket
- High-urgency tickets are highlighted in the UI for manual attention
- High-urgency tickets automatically create an escalation log
- SLA is measured against the review stage:
  - `High`: 1 hour
  - `Medium`: 4 hours
  - `Low`: 24 hours
- Tickets still waiting on human review after the deadline are marked as breached

## Architecture

- `routes`: request and response handling
- `services`: ticket workflow, LLM handling, escalation rules, search, sorting, and stats
- `models`: database tables

## Endpoints

### Health

- `GET /health`

Example response:

```json
{
  "message": "Ticketing API running"
}
```

### Frontend

- `GET /`

This opens the browser dashboard for:

- saving the bearer token locally
- creating tickets
- seeing dashboard stats
- filtering stored tickets by category, urgency, status, and SLA state
- sorting by newest, oldest, or urgency
- searching ticket text, email, or draft reply
- loading tickets that need review
- approving or editing AI output
- seeing SLA due times and breach badges

### Create ticket

- `POST /tickets/`

Request body:

```json
{
  "text": "I am having trouble with the response time of a chatbot",
  "email": "xyz@gmail.com"
}
```

Example response:

```json
{
  "id": 1,
  "text": "I am having trouble with the response time of a chatbot",
  "email": "xyz@gmail.com",
  "category": "Technical",
  "urgency": "Medium",
  "status": "needs_review",
  "draft_reply": "Thank you for reaching out. Our team will look into the chatbot response delay and get back to you shortly.",
  "created_at": "2026-04-15T06:14:06.585018",
  "sla_due_at": "2026-04-15T10:14:06.585018",
  "sla_breached": false
}
```

### List tickets

- `GET /tickets/`
- Optional query params: `category`, `urgency`, `status`, `sla_breached`, `sort_by`

Examples:

```text
GET /tickets/
GET /tickets/?category=Billing
GET /tickets/?category=Technical
GET /tickets/?urgency=High
GET /tickets/?status=needs_review
GET /tickets/?sla_breached=true
GET /tickets/?sort_by=urgency
```

### Review queue

- `GET /tickets/review`

Returns tickets waiting for human review.

Optional query param:

- `sla_breached`

### Search tickets

- `GET /tickets/search?q=<term>`

Searches ticket text, email, and draft reply.

### Ticket stats

- `GET /tickets/stats`

Returns:

- total tickets
- high priority count
- pending review count
- breached review SLA count
- billing ticket count
- escalated ticket count

### Review ticket

- `PATCH /tickets/{ticket_id}/review`

Example body:

```json
{
  "category": "Technical",
  "urgency": "Medium",
  "draft_reply": "Thanks for reporting this. We have reviewed the issue and are investigating.",
  "status": "approved"
}
```

## Running the API

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the server:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open the frontend:

- [Ticketing UI](http://127.0.0.1:8000/)

Open docs:

- [Swagger UI](http://127.0.0.1:8000/docs)

## Environment variables

Create a `.env` file with:

```env
API_TOKEN=your-secret-token
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=openai/gpt-4o-mini
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
```

## Example cURL calls

Create ticket:

```powershell
curl -X POST "http://127.0.0.1:8000/tickets/" `
  -H "Authorization: Bearer mysecrettoken" `
  -H "Content-Type: application/json" `
  -d "{\"text\":\"I am having trouble with the response time of a chatbot\",\"email\":\"xyz@gmail.com\"}"
```

List all tickets:

```powershell
curl -X GET "http://127.0.0.1:8000/tickets/" `
  -H "Authorization: Bearer mysecrettoken"
```

Filter by category:

```powershell
curl -X GET "http://127.0.0.1:8000/tickets/?category=Technical" `
  -H "Authorization: Bearer mysecrettoken"
```

Get tickets needing review:

```powershell
curl -X GET "http://127.0.0.1:8000/tickets/review" `
  -H "Authorization: Bearer mysecrettoken"
```

Approve after review:

```powershell
curl -X PATCH "http://127.0.0.1:8000/tickets/1/review" `
  -H "Authorization: Bearer mysecrettoken" `
  -H "Content-Type: application/json" `
  -d "{\"status\":\"approved\"}"
```
