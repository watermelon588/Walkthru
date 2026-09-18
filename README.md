# Walkthru

AI personas test your website in a real browser and tell you where first-time users get stuck.

- Start here: [AGENTS.md](AGENTS.md), [CURRENT_STATE.md](CURRENT_STATE.md)
- Product spec: [SPEC.md](SPEC.md) · Architecture: [ARCHITECTURE.md](ARCHITECTURE.md) · Design: [DESIGN.md](DESIGN.md) · Skills: [SKILLS.md](SKILLS.md)
- Plan: [tasks/plan.md](tasks/plan.md) · Tasks: [tasks/todo.md](tasks/todo.md)

## Dev
```
cd apps/api && python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/uvicorn app.main:app --reload
cd apps/web && npm install && npm run dev
```
Copy `.env.example` to `.env` and fill in keys.
