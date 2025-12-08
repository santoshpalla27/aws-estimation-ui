# Migration Guide: Monolith to Plugin Architecture

## Overview
This guide provides instructions for migrating from the legacy monolithic AWS estimation system to the new modular, plugin-based architecture.

## Architecture Data Flow
### Old System (Monolith)
- **Hardcoded**: Services hardcoded in `estimate.py` and `frontend/calculators.js`.
- **Tight Coupling**: Adding a service required editing 5+ files across backend and frontend.

### New System (Plugin-Based)
- **Discovery**: `services_registry.json` drives the entire system.
- **Isolation**: Each service lives in `/services/{serviceId}` with its own lifecycle.
- **Dynamic Frontend**: React components loaded dynamically from `/src/services/{serviceId}`.

## Migration Steps

### 1. Register the Service
Add your service to `services_registry.json`.

### 2. Create Service Plugin Directory
Create `/services/new_service/` and populate modules:
- `downloader.py`
- `normalizer.py`
- `metadata.py`
- `estimator.py`
- `pricing_index.py` (Optional optimization)

### 3. Implement Frontend Calculator
Create `/frontend/src/services/new_service/Calculator.jsx`.
- Use `/api/services/{id}/metadata` to fetch dropdowns.
- Post to `/api/estimate/{id}`.

### 4. Verify
- Run downloaders/normalizers.
- Check Sidebar and Architecture Builder.
