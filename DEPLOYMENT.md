# Hapticware Research Assistant — Deployment Documentation

**Deployment Environment:** Linux-based server environment
**Containerization:** Docker + Docker Compose  
**Database:** Neon PostgreSQL  
**Frontend:** React + Vite  
**Backend:** FastAPI  

---

## 1. Objective

The goal of this deployment was to run the full-stack research assistant system in a Linux-based environment using Docker and Docker Compose.

The deployed system includes:

- React + Vite frontend container
- FastAPI backend container
- PostgreSQL database connection using Neon DB
- Environment variable configuration using `.env`
- Docker Compose orchestration
- Restart policies for container reliability
- Accessible frontend and backend endpoints

---

## 2. Final Deployment Architecture

```text
host machine
   |
   | UTM Virtual Machine
   v
Ubuntu Linux VM
   |
   | Docker Compose
   |
   |-- Frontend Container
   |     React + Vite
   |     Port: 5173
   |
   |-- Backend Container
         FastAPI
         Port: 8000
         |
         v
      Neon PostgreSQL Database
```

---

## 3. Final Deployment URLs

Replace the IP address if the VM IP changes.

```text
Frontend URL:
http://192.168.64.5:5173

Backend Health Endpoint:
http://192.168.64.5:8000/health

Backend Query Endpoint:
POST http://192.168.64.5:8000/query
```

---

## 4. Tools Installed in Ubuntu VM

The following tools were installed inside the Ubuntu VM:

```bash
sudo apt update
sudo apt install -y git curl nano unzip
```

Docker and Docker Compose were installed inside the Ubuntu VM.

Verification commands:

```bash
docker --version
docker compose version
docker run hello-world
```

---

## 5. Repository Setup in VM

The GitHub repository was cloned directly inside the Ubuntu VM:

```bash
cd ~
git clone https://github.com/keya-05/Research-Assistant-System.git
cd Research-Assistant-System
```

Project structure:

```text
Research-Assistant-System/
│
├── backend/
│   ├── Dockerfile
│   ├── .env
│   └── .env.example
│
├── frontend/
│   └── Dockerfile
│
├── docker-compose.yml
├── .dockerignore
└── README.md
```

---

## 6. Environment Variables

Real environment variables were stored locally inside the VM in:

```text
backend/.env
```

The `.env` file was not pushed to GitHub because it contains secrets.

Example structure:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require

GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=My-Multi-Agent-Project
```

A safe placeholder file was added for reference:

```text
backend/.env.example
```

---

## 7. Docker Compose Configuration

The system was orchestrated using `docker-compose.yml`.

```yaml
services:
  backend:
    build: ./backend
    container_name: research_backend
    env_file:
      - ./backend/.env
    ports:
      - "8000:8000"
    restart: always

  frontend:
    build: ./frontend
    container_name: research_frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    restart: always
```

### Explanation

- `backend` builds the FastAPI backend container.
- `frontend` builds the React + Vite frontend container.
- `env_file` injects backend environment variables securely.
- `ports` expose services outside the containers.
- `depends_on` starts the frontend after the backend service.
- `restart: always` restarts containers automatically if they crash.

---

## 8. Docker Ignore File

A `.dockerignore` file was created to avoid copying unnecessary or sensitive files into the Docker build context.

Important ignored files:

```dockerignore
.git
.env
*.env
backend/.env
frontend/.env
node_modules/
frontend/node_modules/
__pycache__/
venv/
.venv/
dist/
frontend/dist/
.DS_Store
.vscode/
.idea/
```

This improves build performance and prevents secrets from entering the Docker image.

---

## 9. Running the Deployment

From the project root inside Ubuntu VM:

```bash
cd ~/Research-Assistant-System
docker compose down
docker compose up --build
```

After successful startup, backend logs showed:

```text
DB ready.
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

For running containers in the background:

```bash
docker compose up -d
```

To check running containers:

```bash
docker ps
```

---

## 10. Backend Testing

Health endpoint test:

```bash
curl http://localhost:8000/health
```

Expected output:

```json
{"status":"ok"}
```

Query endpoint test:

```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"question":"What is LangGraph?"}'
```

Expected response format:

```json
{
  "answer": "...",
  "sources": ["..."],
  "confidence": "high",
  "cached": false
}
```

---

## 11. Frontend Testing

The frontend was opened in the browser using:

```text
http://localhost:5173
```

From the host machine, the frontend was accessed using the VM IP:

```text
http://192.168.64.5:5173
```

A test query was submitted from the frontend to confirm frontend-to-backend integration.

---

## 12. Database Persistence

Neon PostgreSQL was used as the persistent database.

Persistence was verified by:

1. Submitting a query through the frontend or API.
2. Checking that the query and generated answer were stored in Neon.
3. Restarting Docker containers.
4. Confirming the previous database row still existed in Neon.

Restart command:

```bash
docker compose down
docker compose up -d
```

Because Neon is a managed PostgreSQL database, data persists independently of Docker container restarts, rebuilds, or VM restarts.

---

## 13. Final Deliverables Checklist

| Requirement | Status |
|---|---|
| Fully dockerized backend | Completed |
| Fully dockerized frontend | Completed |
| Docker Compose orchestration | Completed |
| Environment variable configuration | Completed |
| Restart policies | Completed |
| Accessible frontend URL | Completed |
| Accessible backend API endpoint | Completed |
| Persistent PostgreSQL database | Completed using Neon PostgreSQL |
| Linux-based deployment | Completed using Ubuntu VM in UTM |

---


## Screenshot 1 — Running Docker Containers

Command:

```bash
docker ps
```

Expected proof:

- `research_backend` container running
- `research_frontend` container running


![Docker containers running]!(image.png)

---

## Screenshot 2 — Docker Compose Configuration

Command:

```bash
cat docker-compose.yml
```

Expected proof:

- Backend service
- Frontend service
- `env_file`
- Port mappings
- `restart: always`
- `depends_on`


![Docker Compose configuration](image-1.png)

---

## Screenshot 3 — Backend Health Endpoint

Open in browser or run:

```bash
curl http://localhost:8000/health
```

Expected output:

```json
{"status":"ok"}
```


![Backend health endpoint](image-2.png)

---

## Screenshot 4 — Frontend Application

Open:

```text
http://192.168.64.5:5173
```

Expected proof:

- Frontend page loads successfully


![Frontend application](image-3.png)
---


## Screenshot 5 — Query API Response

Command:

```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"question":"What is LangGraph?"}'
```

Expected proof:

- JSON response contains `answer`
- JSON response contains `sources`
- JSON response contains `confidence`

Add screenshot here:

![Query API response](image-4.png)

---

## Screenshot 7 — Neon Database Row

Open Neon dashboard and show the stored database row.

Expected proof:

- Query is stored
- Response is stored
- Timestamp exists

Do not show passwords, connection strings, or API keys.

Add screenshot here:

![Neon database row](image-5.png)

---


## 15. Demo Explanation

Use this explanation during the demo:

> I deployed the full-stack research assistant inside an Ubuntu Linux VM using Docker Compose. The backend runs as a FastAPI container, the frontend runs as a React Vite container, and the database is Neon PostgreSQL. I configured environment variables using `backend/.env`, exposed ports for frontend and backend accessibility, configured Docker Compose networking between frontend and backend, and added restart policies using `restart: always`. Database persistence is handled by Neon PostgreSQL, so query data remains available even after containers are stopped or rebuilt.

---

## 16. Notes 

Nginx reverse proxy was not added because the assignment deliverables were already satisfied using direct exposed ports.

Nginx can be added later for:

- HTTPS
- Custom domain support
- Single entry point routing
- Production reverse proxy setup

---

## 17. Final Submission Summary

```text
Frontend URL:
http://192.168.64.5:5173

Backend Health Endpoint:
http://192.168.64.5:8000/health

Backend Query Endpoint:
POST http://192.168.64.5:8000/query

GitHub Repository:
https://github.com/keya-05/Research-Assistant-System

Deployment Environment:
Ubuntu Linux VM using UTM

Containerization:
Docker + Docker Compose

Database:
Neon PostgreSQL
```
