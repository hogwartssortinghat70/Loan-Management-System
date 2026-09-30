# Loan Management System

FastAPI + SQLite backend and React (Vite) frontend for managing customers, loans and payments.

## Run the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Run the frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (set `VITE_API_URL` to point at a different backend).
