# Research Assistant

A full-stack web application designed to assist with research tasks. The application consists of a Python backend and a React frontend, providing a seamless interface for managing and analyzing research data.

## Features

- **Backend API**: Built with Python, handling data processing and storage.
- **Frontend Interface**: Modern React application with Vite for fast development.
- **Database Integration**: Supports database operations for research data management.
- **Agent System**: Includes AI agents for automated research assistance.

## Technologies Used

- **Backend**: Python, FastAPI (assumed based on structure)
- **Frontend**: React, Vite, JavaScript
- **Database**: SQLite or similar (based on database.py)
- **Styling**: CSS

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the backend server:
   ```bash
   python main.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## Usage

1. Start both the backend and frontend servers as described above.
2. Open your browser and navigate to the frontend URL (usually `http://localhost:5173` for Vite).
3. Use the interface to interact with the research assistant features.

## Project Structure

```
research-assistant/
├── backend/
│   ├── agents.py       # AI agents for research tasks
│   ├── database.py     # Database operations
│   ├── main.py         # Backend entry point
│   └── requirements.txt # Python dependencies
└── frontend/
    ├── public/         # Static assets
    ├── src/            # React source code
    │   ├── App.jsx     # Main app component
    │   ├── main.jsx    # App entry point
    │   └── assets/     # Additional assets
    ├── package.json    # Node dependencies
    ├── vite.config.js  # Vite configuration
    └── index.html      # HTML template
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
