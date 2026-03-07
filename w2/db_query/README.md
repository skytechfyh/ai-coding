# DB Query Tool

A web-based database query tool that allows users to connect to databases, view table metadata, execute SQL queries, and generate SQL from natural language.

## Features

- Connect to PostgreSQL and MySQL databases
- View table and view metadata (columns, types, primary keys)
- Execute SQL SELECT queries
- Generate SQL from natural language using Claude API
- Results displayed in a table format

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- Pydantic V2
- SQLGlot (SQL parsing)
- Anthropic SDK (Claude API)
- psycopg2 (PostgreSQL driver)
- pymysql (MySQL driver)

### Frontend
- TypeScript 5+
- React 18
- Refine 5
- Ant Design 5
- Monaco Editor
- Vite

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL or MySQL database (for testing)
- Anthropic API key (Claude API)

## Setup

### Backend

```bash
cd backend

# Create virtual environment
uv venv

# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run the server
uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The app will be available at http://localhost:5173

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dbs` | List all saved databases |
| PUT | `/api/v1/dbs/{name}` | Add a new database |
| GET | `/api/v1/dbs/{name}` | Get database metadata |
| DELETE | `/api/v1/dbs/{name}` | Delete a database |
| POST | `/api/v1/dbs/{name}/query` | Execute SQL query |
| POST | `/api/v1/dbs/{name}/query/natural` | Generate SQL from natural language |

## Usage

1. Start the backend server
2. Start the frontend development server
3. Open http://localhost:5173 in your browser
4. Click "Add Database" to add a PostgreSQL or MySQL connection
   - PostgreSQL: `postgresql://user:password@localhost:5432/dbname`
   - MySQL: `mysql://user:password@localhost:3306/dbname`
5. Select a database to view its tables and columns
6. Write SQL in the editor or use natural language to generate SQL
7. Click Execute to run the query

## License

MIT
