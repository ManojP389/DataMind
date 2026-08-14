# DataMind

DataMind is an AI-powered data analytics platform that allows users to upload CSV datasets, analyze them, visualize important patterns, and ask questions using natural language.

The project uses a multi-agent architecture with LangGraph. Groq API with Llama 3.3 70B is used for intent classification, SQL generation, and insight generation, while Python, Pandas, and SQLite handle data processing and calculations.

## Features

| Feature | Description |
|---|---|
| CSV Upload | Upload datasets through the web interface |
| Dataset Analysis | Automatically profile and analyze datasets |
| Data Visualization | Generate charts from the dataset |
| Natural Language Queries | Ask questions about the uploaded data |
| SQL Generation | Convert natural-language questions into SQL |
| SQL Validation | Validate generated SQL before execution |
| AI Insights | Generate explanations from query results |
| Multi-Agent Workflow | Coordinate specialized AI and data agents |
| Execution Trace | Show the agents involved in each request |

## Agents

| Agent | Role |
|---|---|
| Manager Agent | Classifies the request as query or analysis |
| Data Agent | Profiles the uploaded dataset |
| EDA Agent | Performs exploratory data analysis |
| SQL Agent | Generates and executes validated SQL queries |
| Insight Agent | Explains SQL results using the LLM |
| Visualization Agent | Creates data visualization results |

## How It Works

For an analysis request such as:

```text
Analyze this dataset and identify the key patterns.
```

the Manager Agent classifies the request as an analysis and routes it through the Data Agent, EDA Agent, and Visualization Agent.

```text
Manager Agent
      ↓
Data Agent
      ↓
EDA Agent
      ↓
Visualization Agent
```

For a query such as:

```text
Which region has the highest profit?
```

the Manager Agent classifies it as a query. The SQL Agent sends the question and dataset schema to the Groq LLM, generates a SQL query, validates it, and executes it using SQLite. The Insight Agent then explains the verified result.

```text
Manager Agent
      ↓
SQL Agent
      ↓
Groq API
      ↓
SQL Validation
      ↓
SQLite
      ↓
Insight Agent
      ↓
Answer
```

## Example

User question:

```text
Which region has the highest profit?
```

Generated SQL:

```sql
SELECT "Region",
       SUM("Profit") AS "total_profit"
FROM "dataset"
GROUP BY "Region"
ORDER BY "total_profit" DESC
LIMIT 1;
```

Example result:

```text
West - $67,860.56
```

The Insight Agent converts the verified result into a concise natural-language answer.

## Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React.js, CSS, Vite |
| Backend | FastAPI, Python |
| AI | Groq API, Llama 3.3 70B |
| Agent Framework | LangGraph |
| Data Processing | Pandas, NumPy |
| Database | SQLite |
| API Communication | Axios, REST APIs |
| Testing | Pytest |
| Deployment | Vercel, Render |
| Version Control | Git, GitHub |

## Project Structure

```text
DataMind/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── data_agent.py
│   │   │   ├── eda_agent.py
│   │   │   ├── insight_agent.py
│   │   │   ├── manager_agent.py
│   │   │   ├── sql_agent.py
│   │   │   └── visualization_agent.py
│   │   │
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   └── workflow.py
│   │   │
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   └── upload_service.py
│   │   │
│   │   ├── tools/
│   │   │   ├── data_tools.py
│   │   │   ├── eda_tools.py
│   │   │   ├── sql_tools.py
│   │   │   └── visualization_tools.py
│   │   │
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── requirements.txt
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check API status |
| POST | `/upload` | Upload CSV dataset |
| POST | `/analyze/{file_id}` | Analyze dataset |
| POST | `/agent/analyze/{file_id}` | Run analysis workflow |
| POST | `/agent/query/{file_id}` | Ask a question about the dataset |

## Local Setup

### Backend

Clone the repository:

```bash
git clone https://github.com/ManojP389/DataMind.git
cd DataMind/backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` directory:

```env
GROQ_API_KEY=your_groq_api_key
```

Run the FastAPI backend:

```bash
python -m uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server will provide the frontend URL in the terminal.

## Testing

DataMind includes automated tests for the API, agents, dataset processing, SQL validation, visualization, and LangGraph workflows.

Run the complete test suite:

```bash
cd backend
python -m pytest
```

Current test result:

```text
65 passed
```

## Deployment

The FastAPI backend is deployed on Render and the React frontend is deployed on Vercel.

Backend:

```text
https://datamind-0v4c.onrender.com
```

Swagger API documentation:

```text
https://datamind-0v4c.onrender.com/docs
```

The frontend communicates with the deployed backend using the `VITE_API_BASE_URL` environment variable.

## Security

The Groq API key is stored in environment variables and is not committed to GitHub.

Generated SQL is validated before execution, and only read-only queries are allowed.

Uploaded datasets, virtual environments, environment files, cache files, and build files are excluded from version control using `.gitignore`.

## Project Status

DataMind is a functional full-stack AI data analytics platform with multi-agent orchestration, Groq LLM integration, natural-language SQL querying, dataset analysis, visualization, automated testing, and cloud deployment.

The backend currently has 65 passing automated tests.

## License

This project is developed for educational, portfolio, and demonstration purposes.
