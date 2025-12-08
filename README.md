# AWS Cost Estimation Web Application

A full production-grade, offline-capable AWS Cost Estimation tool.

## Features
- **Offline Pricing**: Downloads AWS Bulk Pricing API data once.
- **Privacy**: No external API calls during runtime.
- **Calculators**: EC2, S3 (RDS placeholder).
- **Architecture**: Architecture Builder to sum costs.
- **Export**: JSON/PDF export (future).

## Architecture
- **Downloader**: Python script (`downloader/pricing_downloader.py`).
- **Normalizer**: Python SQLite-based engine (`normalizer/main.py`).
- **Backend**: FastAPI (`backend/app/main.py`).
- **Frontend**: React + Tailwind (`frontend/`).
- **Data**: Stored in `/data/raw` and `/data/normalized`.

## Quick Start (Docker)

1. **Downloader Data** (Initial Setup - Takes time!)
   ```bash
   # Run the tools profile to download and normalize data
   docker-compose --profile tools run downloader
   ```
   *Note: This downloads ~7GB+ of data. Ensure stable internet.*

2. **Run Application**
   ```bash
   docker-compose up backend frontend
   ```
3. **Access**
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000/docs`

## Local Development

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Data Update
```bash
python downloader/pricing_downloader.py
python normalizer/main.py
```
