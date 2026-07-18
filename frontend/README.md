# DevWhisper Frontend

React + Vite frontend for DevWhisper.

## Setup

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

Opens at `http://localhost:5173`. The dev server proxies `/history`, `/webhook`, `/health`, and `/static` to the FastAPI backend at `http://127.0.0.1:8000`.

## Build

```bash
npm run build
```

Produces a static build in `dist/`.