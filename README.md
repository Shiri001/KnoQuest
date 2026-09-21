# KnoQuest — Enterprise Cognitive Workspace & AI Agent

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF.svg)](https://vitejs.dev/)
[![Azure Foundry](https://img.shields.io/badge/Azure_Foundry-GPT--4.1--mini-0078D4.svg)](https://azure.microsoft.com/)

**KnoQuest** is an enterprise-grade AI knowledge workspace and autonomous agent platform built for secure corporate environments. It bridges internal knowledge policies, model-context-protocol (MCP) corporate tools, and conversational intelligence powered by Azure AI Foundry, GPT-4.1-mini, Azure AI Search, and Azure Speech Services.

---

## 🌟 Key Features

### 1. 🛡️ Enterprise Access & Session Security
- **Employee Portal Authentication**: Login with Employee ID or corporate email with company tenant isolation.
- **Argon2id Password Hashing**: State-of-the-art cryptographic password protection with automatic salt generation.
- **Strict Session Management**: HttpOnly cookie sessions with automated 5-attempt lockout defense.
- **Server-Side RBAC**: Role-based access control governing sensitive policy documents and tool invocations.

### 2. 🧠 Grounded Enterprise Intelligence (RAG)
- **Azure AI Foundry**: Multi-turn conversational reasoning powered by `gpt-4.1-mini`.
- **Azure AI Search (Hybrid + Vector)**: Grounded enterprise document indexing and semantic retrieval.
- **Collapsed Citation Cards**: Verifiable provenance citing official policy titles, sections, and page references.
- **Multilingual Read-Aloud**: Text-to-speech with natural pronunciation across supported corporate languages.

### 3. 🛠️ Model-Context-Protocol (MCP) Tools
- **Outlook & Communications**:
  - Save drafts directly from chat prompts or manual editor.
  - Interactive compose pane with sticky action bars, folder counts, and in-place draft updating.
  - One-click Outlook transmission with live left-panel synchronization.
- **Calendar & Appointments**:
  - Natural language scheduling with dynamic date, time, duration, and attendee resolution.
  - Outlook / Microsoft Teams calendar synchronization.
- **IT Support Helpdesk**:
  - Issue ticketing with severity tiers (Low, Medium, High, Critical) and department routing.
- **Staff Directory & Persona Dossiers**:
  - Bi-directional name/role matching.
  - Executive-grade dossiers covering domain responsibilities, extensions, and collaboration shortcuts.

### 4. 💎 Enterprise UI Experience
- Full-bleed SaaS layout with high-contrast dark theme.
- **Confirmation Modals**: Sensitive operations ask for confirmation before proceeding.
- **5-Second Feedback Toasts**: Animated progress track with automatic dismissal.
- Clean, unobstructed sign-in fields without overlapping icons.

---

## 📁 Repository Structure

```
KnoQuest/
├── backend/
│   ├── app/
│   │   ├── auth.py                  # Argon2id authentication & sessions
│   │   ├── database.py              # SQLite employee database & migrations
│   │   ├── agent.py                 # Azure Foundry RAG & MCP agent orchestration
│   │   ├── main.py                  # FastAPI application routes
│   │   ├── mcp/
│   │   │   └── tools/
│   │   │       ├── calendar_tools.py        # Calendar parser & event booking
│   │   │       ├── communication_tools.py   # Outlook drafting & transmission
│   │   │       ├── employee_tools.py        # Directory search & dossiers
│   │   │       └── ticket_tools.py          # IT Support ticketing
│   │   └── services/
│   │       ├── azure_client.py      # Azure OpenAI / Foundry integration
│   │       └── search_service.py    # Azure AI Search retriever
│   ├── tests/                       # 28 automated pytest test suites
│   ├── requirements.txt
│   └── run_backend.bat
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/LoginPage.tsx   # Enterprise login component
│   │   │   ├── common/              # ConfirmationModal & ActionFeedbackToast
│   │   │   └── layout/              # AppShell, TopNav, Sidebar
│   │   ├── views/                   # Dashboard, Chat, Comms, Calendar, IT, Directory
│   │   ├── services/api.ts          # Axios backend API client
│   │   └── index.css                # Enterprise design system
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+**
- **Node.js 20+** & npm
- (Optional for cloud features) Active **Azure AI Foundry** resource with `gpt-4.1-mini` and Azure AI Search.

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Fill in your Azure credentials in .env (or run in local sandbox mode)

# Run tests
pytest tests/ -v

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run build
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🔒 Security Notice
Do not commit sensitive configuration or API keys to GitHub. All production credentials must be set through environment variables (`.env`).
