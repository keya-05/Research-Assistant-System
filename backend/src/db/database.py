"""Database operations with JSONB schema for conversations."""
import os, json, logging, asyncpg
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None


async def get_pool():
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def init_db():
    """Initialize database with new JSONB schema."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create users table for authentication
        # Supports both email/password and Google OAuth
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255),  -- NULL for Google OAuth users
                full_name VARCHAR(255),
                email_verified BOOLEAN DEFAULT FALSE,
                google_id VARCHAR(255) UNIQUE,  -- Google OAuth user ID
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """)
        
        # Create conversations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        # Create conversation_messages table with JSONB
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                messages JSONB NOT NULL DEFAULT '[]',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        # Create indexes for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_created_at ON conversations(created_at);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON conversations(user_id);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_conv_id ON conversation_messages(conversation_id);
        """)
        
        # Keep legacy queries table for backward compatibility
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources JSONB NOT NULL DEFAULT '[]',
                confidence VARCHAR(10) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_question ON queries(question);
        """)
    logger.info("DB ready with JSONB schema and user authentication.")


# ==================== CONVERSATION OPERATIONS ====================

async def create_conversation(user_id: int) -> int:
    """Create a new conversation for a user and return its ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "INSERT INTO conversations (user_id) VALUES ($1) RETURNING id",
            user_id
        )
        conversation_id = result["id"]
        
        # Create corresponding message row with empty array
        await conn.execute(
            "INSERT INTO conversation_messages (conversation_id, messages) VALUES ($1, '[]'::jsonb)",
            conversation_id
        )
        
        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        return conversation_id


async def get_conversation(conversation_id: int) -> Optional[Dict[str, Any]]:
    """Get full conversation with all messages."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT c.id, c.created_at, c.updated_at, cm.messages
            FROM conversations c
            LEFT JOIN conversation_messages cm ON c.id = cm.conversation_id
            WHERE c.id = $1
        """, conversation_id)
    
    if row:
        return {
            "id": row["id"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "messages": row["messages"] if isinstance(row["messages"], list) else json.loads(row["messages"]) if row["messages"] else []
        }
    return None


# ==================== MESSAGE OPERATIONS ====================

async def add_message_to_conversation(
    conversation_id: int,
    question: str,
    answer: str,
    sources: List[str],
    confidence: str
) -> int:
    """Add a message to conversation's JSONB array. Returns message index."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create message object
        message = {
            "question": question,
            "answer": answer,
            "confidence": confidence,
            "sources": sources,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Append to JSONB array
        await conn.execute("""
            UPDATE conversation_messages
            SET messages = messages || $1::jsonb,
                updated_at = NOW()
            WHERE conversation_id = $2
        """, json.dumps([message]), conversation_id)
        
        # Update conversation's updated_at
        await conn.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
            conversation_id
        )
        
        # Get message count (which is the new message index)
        result = await conn.fetchrow("""
            SELECT jsonb_array_length(messages) - 1 as msg_count
            FROM conversation_messages
            WHERE conversation_id = $1
        """, conversation_id)
        
        message_id = result["msg_count"] if result else 0
        logger.info(f"Added message to conversation {conversation_id}, message_id: {message_id}")
        return message_id


async def get_cached_query(question: str, conversation_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Search for similar question in conversation or globally.
    If conversation_id provided, searches within that conversation only.
    Otherwise searches legacy queries table.
    """
    pool = await get_pool()
    
    if conversation_id:
        # Search within specific conversation's JSONB messages
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT messages
                FROM conversation_messages
                WHERE conversation_id = $1
            """, conversation_id)
        
        if row:
            messages = row["messages"] if isinstance(row["messages"], list) else json.loads(row["messages"])
            # Search for exact or similar question
            for msg in messages:
                if msg.get("question") == question:
                    logger.info(f"Found cached query in conversation {conversation_id}")
                    return {
                        "answer": msg.get("answer"),
                        "sources": msg.get("sources", []),
                        "confidence": msg.get("confidence")
                    }
    else:
        # Search legacy queries table for backward compatibility
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT answer, sources, confidence FROM queries WHERE question=$1 ORDER BY created_at DESC LIMIT 1",
                question
            )
        if row:
            logger.info("Found cached query in legacy table")
            return {
                "answer": row["answer"],
                "sources": row["sources"] if isinstance(row["sources"], list) else json.loads(row["sources"]),
                "confidence": row["confidence"]
            }
    
    return None


# ==================== USER OPERATIONS ====================

async def create_user(email: str, hashed_password: Optional[str] = None, full_name: Optional[str] = None, google_id: Optional[str] = None) -> int:
    """Create a new user and return their ID.
    
    For regular auth: provide hashed_password
    For Google OAuth: provide google_id (password will be null)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # For Google users, mark email as verified automatically
        email_verified = google_id is not None
        
        result = await conn.fetchrow(
            """INSERT INTO users (email, hashed_password, full_name, email_verified, google_id) 
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            email, hashed_password, full_name, email_verified, google_id
        )
        user_id = result["id"]
        logger.info(f"Created user {user_id} with email {email} (google: {google_id is not None})")
        return user_id


async def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Google ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, full_name, email_verified, created_at FROM users WHERE google_id = $1",
            google_id
        )
    
    if row:
        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "email_verified": row["email_verified"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None
        }
    return None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email address."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, hashed_password, full_name, email_verified, created_at FROM users WHERE email = $1",
            email
        )
    
    if row:
        return {
            "id": row["id"],
            "email": row["email"],
            "hashed_password": row["hashed_password"],
            "full_name": row["full_name"],
            "email_verified": row["email_verified"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None
        }
    return None


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, full_name, created_at FROM users WHERE id = $1",
            user_id
        )
    
    if row:
        return {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None
        }
    return None


# ==================== LEGACY SUPPORT ====================

async def save_query_response(question, answer, sources, confidence):
    """Legacy function: saves to queries table for backward compatibility."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO queries (question, answer, sources, confidence) VALUES ($1,$2,$3::jsonb,$4)",
            question, answer, json.dumps(sources), confidence
        )
