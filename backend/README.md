# Research Assistant Backend

A FastAPI-based backend for the Research Assistant system with JSONB-powered conversation management.

## Project Structure

```
backend/
├── main.py                      # FastAPI application entry point
├── database.py                  # Legacy database file (deprecated)
├── agents.py                    # Legacy agents file (deprecated)
├── app/                         # New modular structure
│   ├── __init__.py
│   ├── db/                      # Database operations
│   │   ├── __init__.py
│   │   └── database.py          # JSONB schema & DB functions
│   ├── models/                  # Pydantic models
│   │   ├── __init__.py
│   │   └── schemas.py           # Request/Response schemas
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   └── research_service.py  # Groq API integration
│   └── api/                     # API routes
│       ├── __init__.py
│       └── routes.py            # Route handlers
├── Agents/                      # LangGraph multi-agent system
│   ├── agents/
│   ├── graph/
│   └── utils/
├── requirements.txt
└── .env.example
```

## Database Schema

### New JSONB Schema

**conversations table:**
- `id` (SERIAL PRIMARY KEY)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**conversation_messages table:**
- `id` (SERIAL PRIMARY KEY)
- `conversation_id` (INTEGER, FK to conversations)
- `messages` (JSONB) - Array of message objects
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Message Object Structure:**
```json
{
  "question": "What is AI?",
  "answer": "AI is...",
  "confidence": "high",
  "sources": ["https://example.com"],
  "timestamp": "2024-04-29T10:00:00Z"
}
```

### Legacy Support

The old `queries` table is maintained for backward compatibility.

## API Endpoints

### POST /conversations
Create a new conversation session.

**Response:**
```json
{
  "conversation_id": 1
}
```

### GET /conversations/{id}
Retrieve full conversation with all messages.

**Response:**
```json
{
  "id": 1,
  "created_at": "2024-04-29T10:00:00Z",
  "updated_at": "2024-04-29T10:35:00Z",
  "messages": [...]
}
```

### POST /query
Process a research query.

**Request:**
```json
{
  "question": "What is AI?",
  "conversation_id": 1  // Optional, creates new if not provided
}
```

**Response:**
```json
{
  "answer": "AI is...",
  "sources": ["https://example.com"],
  "confidence": "high",
  "cached": false,
  "conversation_id": 1,
  "message_id": 0
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## Database Operations

### Conversation Operations
- `create_conversation()` - Create new conversation
- `get_conversation(id)` - Fetch conversation with messages

### Message Operations
- `add_message_to_conversation(...)` - Append message to JSONB array
- `get_cached_query(question, conv_id)` - Search for cached queries

### Legacy Support
- `save_query_response(...)` - Save to legacy queries table

## Environment Variables

Required environment variables in `.env`:
```
DATABASE_URL=postgresql://user:password@host:port/dbname
GROQ_API_KEY=your_groq_api_key
```

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Key Features

- **JSONB Storage**: Efficient binary JSON storage for message arrays
- **Conversation Tracking**: Group queries by conversation sessions
- **Flexible Schema**: Add message fields without schema changes
- **Backward Compatible**: Legacy queries table still available
- **Connection Pooling**: Async connection pooling with asyncpg
- **Caching**: Conversation-specific query caching

## Migration Notes

To migrate from the old schema to the new JSONB schema, see the migration script in the database documentation.

## Performance Considerations

- Indexes on `conversations.created_at` and `conversation_messages.conversation_id`
- JSONB binary format for efficient storage
- O(1) complexity for appending to JSONB arrays
- For very large conversations (100+ messages), consider pagination or archiving
