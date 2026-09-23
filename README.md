# Walkthru

AI personas test your website in a real browser and tell you where first-time users get stuck.

- Start here: [AGENTS.md](AGENTS.md), [CURRENT_STATE.md](CURRENT_STATE.md)
- Product spec: [SPEC.md](SPEC.md) · Architecture: [ARCHITECTURE.md](ARCHITECTURE.md) · Design: [DESIGN.md](DESIGN.md) · Skills: [SKILLS.md](SKILLS.md)
- Plan: [tasks/plan.md](tasks/plan.md) · Tasks: [tasks/todo.md](tasks/todo.md)

## Run everything with one command (development only)

From the repository root in PowerShell or cmd:

```powershell
.\dev
```

This builds the extension and starts the API (:8000), web app (:5173), easy fixture (:8101) and hard fixture (:8102) with labelled, coloured output. Ctrl+C stops all of them. After it starts, reload Walkthru on `chrome://extensions` (first time: Load unpacked from `apps/extension/.output/chrome-mv3`). `dev.py` and `dev.cmd` are development conveniences and must be removed before production.

## Run locally on Windows, one process per terminal

Copy each block into a separate PowerShell terminal from the repository root. Copy `apps/api/.env.example` and `apps/web/.env.example` to `.env` and fill in the required keys first.

### 1. API: http://127.0.0.1:8000

```powershell
cd apps/api
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. Web app: http://127.0.0.1:5173

```powershell
cd apps/web
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run dev -- --host 127.0.0.1 --port 5173
```

### 3. Easy and hard fixture sites

```powershell
apps\api\.venv\Scripts\python.exe evals\serve.py
```

- Easy: http://127.0.0.1:8101
- Hard: http://127.0.0.1:8102

### 4. Build and load the Chrome extension

```powershell
cd apps/extension
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run build
```

Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**, and select:

```text
apps/extension/.output/chrome-mv3
```

After rebuilding, click **Reload** on the Walkthru extension card.

## End-to-end test

1. Confirm API health at http://127.0.0.1:8000/health.
2. Sign in at http://127.0.0.1:5173/login.
3. Open http://127.0.0.1:8101 for the easy flow or http://127.0.0.1:8102 for the hard flow.
4. Open the Walkthru side panel from its Chrome toolbar icon.
5. Enter a goal such as `Sign up for an account`, select a persona, and click **Start test**.
6. When the run finishes, open its report from the side panel or dashboard.
7. Verify the journey steps, screenshot evidence, Share, Email me, CSV export, and Save PDF.

## Automated checks

```powershell
# API
cd apps/api
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check .

# Web
cd ../web
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npx-cli.js' tsc --noEmit
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run lint
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run build

# Extension
cd ../extension
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' test
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npx-cli.js' tsc --noEmit
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run lint
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run build
```
