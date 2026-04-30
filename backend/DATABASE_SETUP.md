# Database Setup Guide

This guide explains how to set up the database schema for the Research Assistant system.

## Option 1: Using schema.sql (Recommended for Production/NeonDB)

### Running from Code Editor

**VS Code:**
1. Install the PostgreSQL extension (e.g., "PostgreSQL" by Weijan Chen)
2. Connect to your database
3. Right-click on `schema.sql` and select "Execute SQL File"

**Other Editors:**
- Use the database extension/plugin for your editor
- Or use the command line (see below)

### Running from Command Line

```bash
# Local PostgreSQL
psql -U your_username -d your_database -f schema.sql

# With connection string
psql $DATABASE_URL -f schema.sql
```

### NeonDB Deployment

**Option A: Via Neon Console**
1. Go to your Neon project dashboard
2. Navigate to "SQL Editor"
3. Paste the contents of `schema.sql`
4. Click "Run"

**Option B: Via Neon CLI**
```bash
# Install Neon CLI
npm install -g neonctl

# Login
neonctl auth

# Run schema
neonctl sql execute --file schema.sql
```

**Option C: Via Connection String**
```bash
psql $NEON_DATABASE_URL -f schema.sql
```

## Option 2: Using Python init_db() (Development Only)

The current Python code in `src/db/database.py` has an `init_db()` function that creates the schema programmatically. This is useful for development but not recommended for production.

```python
# In main.py, this runs automatically on startup
await init_db()
```

To run manually:
```bash
cd backend
python -c "import asyncio; from src.db.database import init_db; asyncio.run(init_db())"
```

## Environment Variables

Set these in your `.env` file:

```env
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-for-jwt
```

For NeonDB, get your connection string from the Neon console.

## Verification

After running the schema, verify tables were created:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

Expected output:
- users
- conversations
- conversation_messages
