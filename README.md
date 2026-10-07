# AI Agent Workflow Automation

## Overview

- Converts business workflows defined in Excel into executable AI-agent workflows.
- The agent understands the user request and selects the appropriate workflow.
- A generic `WorkflowEngine` executes the workflow using reusable tools and configurable decisions.
- The architecture is designed so new workflows can be added with minimal code changes.

## Tech Stack

- Python
- FastAPI
- Groq LLM
- OpenPyXL
- Pydantic
- HTTPX
- Pytest
- CSV mock data

## How It Works

```
┌──────────────────────┐
│    User Request      │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   FastAPI Endpoint   │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│     AI Agent + LLM   │
│   Workflow Selection │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Workflow Registry   │
│   Excel Definitions  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   Workflow Engine    │
│  Executes Steps in   │
│    Defined Order     │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│     Tool Registry    │
│  Reusable Tools +    │
│     Decisions        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│     Final Result     │
│ Steps + Decisions +  │
│      Output          │
└──────────────────────┘

Workflow Execution
Each workflow follows the same execution architecture:
Excel Definition → Workflow Selection → Engine Execution → Tool Execution → Decision Evaluation → Final Result
- Excel — Stores workflow definitions, steps, inputs, tools, and decision logic.
- AI Agent — Understands the user request and selects the appropriate workflow.
- Workflow Engine — Executes the selected workflow step by step.
- Tool Registry — Provides reusable tools for file processing, calculations, validation, LLM tasks, ranking, reporting, and lookups.
- Decisions — Evaluates workflow-specific conditions and handles exceptions.
- Final Result — Returns the workflow output along with executed steps and decision results.Result
```

- **FastAPI** — HTTP API that receives the user request.
- **Agent + LLM** — interprets the request and selects a workflow.
- **Workflow Registry** — holds all workflow definitions loaded from Excel.
- **Workflow Engine** — executes the selected workflow step by step.
- **Tool Registry** — resolves each step to a registered tool.
- **Tools + Decisions** — perform the work and apply executable conditions.

Configuration-driven workflow execution:

- Excel is the workflow definition/source.
- `bindings.json` maps workflow steps to reusable tools.
- `decisions.json` defines executable conditions.
- `WorkflowEngine` remains generic and does not contain WF001/WF002/etc. branches.

## Workflows

| ID | Workflow | Purpose |
|---|---|---|
| WF001 | Inventory Restock Check | Identify products below minimum stock and calculate reorder quantity |
| WF002 | Product Price Validation | Compare internal and vendor prices and flag differences above 10% |
| WF003 | Vendor File Processing | Validate vendor data and produce cleaned/invalid datasets |
| WF004 | Product Description Generator | Generate product descriptions and SEO content using the LLM |
| WF005 | Customer Order Status | Find order and shipment status using order ID or customer email |
| WF006 | Duplicate Product Detection | Identify definite and possible duplicate products |
| WF007 | Marketing Campaign Brief | Generate a structured campaign brief |
| WF008 | SEO Keyword Classification | Classify keyword intent and map keywords to pages |
| WF009 | Employee Task Assignment | Rank employees and recommend the best available employee |
| WF010 | Workflow Performance Report | Analyze execution logs and identify failing/slow workflows |
| WF011 | Product Category Count | Count products by category — scalability demonstration |

## Project Structure

```
AI_Agent_workflow/
├── config/
│   ├── bindings.json
│   └── decisions.json
├── data/
│   ├── mock/
│   └── workflows/
├── src/
│   └── agent_workflow/
│       ├── tools/
│       ├── agent.py
│       ├── engine.py
│       ├── registry.py
│       ├── service.py
│       ├── decisions.py
│       ├── llm.py
│       └── api.py
├── tests/
├── .env.example
├── .gitignore
└── requirements.txt
```

- `config/` — workflow-to-tool bindings and decision rules.
- `data/mock/` — CSV mock data consumed by the workflows.
- `data/workflows/` — Excel workbook with workflow and test-question definitions.
- `src/agent_workflow/tools/` — reusable tools (calc, classify, lookup, reporting, assign, aggregate, etc.).
- `tests/` — pytest suite, one test module per workflow plus unit tests.

## Setup

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Groq API key and configuration locally. Do not commit `.env`.

### Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key |
| `LLM_MODEL` | LLM model name |
| `LLM_BASE_URL` | LLM base URL |
| `LLM_TIMEOUT` | Request timeout in seconds |

## Run

```bash
python -m uvicorn agent_workflow.api:app --app-dir src
```

API endpoints:

- `GET /health` — health check.
- `POST /agent/run` — send a user request (`{"message": "..."}`) and receive the executed workflow result.

## Example

```
User:
Which products need restocking?

Agent:
WF001

Workflow:
Load inventory
→ Compare stock
→ Identify low stock
→ Calculate reorder quantity
→ Generate restock list

Result:
Products requiring restock
```

The same agent architecture handles the other workflows. The workflow is selected from the request, then executed via the generic engine, tools, and decisions.

## Scalability — WF011

WF011 was added after WF001–WF010 to verify that the architecture is reusable.

WF011 was added using:

- Excel workflow definition
- `bindings.json`
- `decisions.json`
- reusable tools
- mock CSV data

Important verification:

- `engine.py` was NOT modified for WF011.
- No WF011-specific branch/class was added to `WorkflowEngine`.
- WF011 executes through the same `AgentService` and `WorkflowEngine` used by the other workflows.
- This demonstrates that a new workflow can be added with minimal code changes.

The scalability test resulted in all tests passing.

## Testing

```bash
.\venv\Scripts\python.exe -m pytest tests -q
```

Current verified result:

```
142 passed, 1 warning
```

The warning is a pre-existing Starlette deprecation warning.

## Security

- `.env` is ignored by Git.
- API keys are not committed.
- `.env.example` contains placeholders.
- `venv/`, `__pycache__/`, `*.pyc`, and `.pytest_cache/` are ignored.