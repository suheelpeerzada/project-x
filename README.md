# Project-X

A local-first desktop AI client: a FastAPI backend plus a React frontend.
It talks directly to AI providers using **your own API keys**. There are no
servers, no accounts and no telemetry. Your chats, settings and keys stay on
your machine.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- An API key from at least one supported provider (for example Groq or OpenAI)

## Quick start

**Windows:** double-click `start.bat` (or run it from a terminal).

**macOS / Linux:**

```bash
bash start.sh
```

The script creates a Python virtual environment, installs the backend and
frontend packages on first run, then starts both. Open the address the
frontend prints (usually http://localhost:5173) and follow the setup screen.

## Manual start

Backend (run from the `backend` folder, not from `backend/app`):

```bash
cd backend
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

The backend runs at http://127.0.0.1:8000. API docs are at
http://127.0.0.1:8000/docs.

## Adding your API key

Enter your key in the app's setup screen or in Settings. It is stored in your
operating system's keychain (service name `project_x`), never in this
repository and never in the config file.

## Where your data lives

Everything is stored in your home folder, outside this project:

| What | Where |
| --- | --- |
| Settings (no keys) | `~/.project_x_config.json` |
| Chat history | `~/.project_x_history.db` |
| Uploaded files | `~/.project_x_files/` |
| API keys | OS keychain, service `project_x` |

Cloning or downloading this repository never includes anyone's history or keys.
To remove your data, use **Reset Config** in Settings and delete the files above.

## Troubleshooting

- **Models don't load / chat is locked:** check that the backend is running and
  that your key is valid. The lock message explains the reason.
- **"No usable keychain" warning (some Linux setups):** install a keyring
  backend such as GNOME Keyring or KWallet. Without one, the key is kept in the
  config file in your home folder instead.
- **Port already in use:** stop the other process, or start the backend with
  `uvicorn app.main:app --port 8001` and update the address in
  `frontend/src/services/api.ts`.
- **Browser blocks requests (CORS):** the backend only accepts requests from
  its allowed local origins. Use the address the frontend prints.

## Security note

This app is designed to run on your own computer for one user. Do not expose
the backend to the internet: it has no accounts or login.
