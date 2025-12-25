# AWS Terraform Cost Calculator

Production-ready monolithic application for calculating AWS costs from Terraform files using real AWS pricing data.

## 🚀 Features

- **Real AWS Pricing Data**: Downloads and normalizes actual AWS pricing from official APIs
- **Complete Terraform Support**: Parses resources, variables, locals, count, for_each, and local modules
- **Accurate Cost Calculation**: Database-driven pricing with no hardcoded values
- **Service Support**: EC2, RDS, S3, EBS, Lambda (extensible architecture)
- **Interactive Dashboard**: React frontend with cost breakdowns and visualizations
- **Production-Ready**: Docker Compose, PostgreSQL, proper error handling

## 📋 Prerequisites

- Docker and Docker Compose
- 2GB+ free disk space (for pricing data)
- Internet connection (for initial pricing download)

## 🏃 Quick Start

### 1. Clone and Setup

```bash
cd aws-estimation-ui
cp .env.example .env
```

### 2. Start the Application

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Frontend UI (port 3000)

### 3. Initialize Pricing Data

**IMPORTANT**: The first time you run the application, you must download pricing data:

```bash
docker-compose exec backend python -c "from app.pricing.scheduler import pricing_scheduler; pricing_scheduler.run_now()"
```

This will take **30-60 minutes** and download ~500MB of AWS pricing data. This is a one-time operation.

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📖 Usage

### Upload Terraform Files

1. Open http://localhost:3000
2. Drag and drop a `.tf` file or `.zip` archive
3. Wait for analysis to complete
4. View detailed cost breakdown

### API Usage

```bash
# Upload file
curl -X POST -F "file=@example.tf" http://localhost:8000/api/upload

# Analyze (use job_id from upload response)
curl -X POST http://localhost:8000/api/analyze/{job_id}

# Get results
curl http://localhost:8000/api/results/{job_id}
```

## 🏗️ Architecture

### Backend (Python/FastAPI)

```
backend/
├── app/
│   ├── api/          # REST endpoints
│   ├── pricing/      # AWS pricing pipeline
│   ├── terraform/    # HCL parser & normalizer
│   ├── engine/       # Cost calculation engine
│   ├── models/       # SQLAlchemy models
│   └── db/           # Database utilities
```

### Frontend (React/TypeScript)

```
frontend/
├── src/
│   ├── components/   # Upload & Dashboard
│   ├── services/     # API client
│   └── App.tsx       # Main app
```

### Database Schema

- **Pricing Tables**: versions, services, regions, dimensions, rules, free_tiers
- **Job Tables**: upload_jobs, analysis_results, resource_costs
- **Audit Tables**: pricing_ingestion_logs

## 🔧 Configuration

Edit `.env` to customize:

```env
# Database
POSTGRES_DB=aws_cost_calculator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Pricing Updates
PRICING_UPDATE_ENABLED=true
PRICING_UPDATE_SCHEDULE=0 2 * * *  # Daily at 2 AM

# Upload Limits
MAX_UPLOAD_SIZE_MB=50
```

## 🧪 Testing

### Sample Terraform Files

Sample files are provided in `backend/tests/sample_terraform/`:

```bash
# Test with sample EC2 instance
curl -X POST -F "file=@backend/tests/sample_terraform/ec2.tf" http://localhost:8000/api/upload
```

### Run Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Integration tests
pytest tests/test_integration.py -v
```

## 📊 Supported AWS Services

| Service | Resource Types | Pricing Components |
|---------|---------------|-------------------|
| **EC2** | aws_instance | Instance hours, tenancy, OS |
| **RDS** | aws_db_instance | Instance hours, storage, Multi-AZ |
| **S3** | aws_s3_bucket | Storage, requests, transfer |
| **EBS** | aws_ebs_volume | Volume storage, IOPS |
| **Lambda** | aws_lambda_function | Requests, GB-seconds, free tier |

## 🔌 Adding New Services

1. **Create Adapter**: `backend/app/pricing/adapters/new_service.py`
2. **Register in Matcher**: Add to `ADAPTER_MAP` in `engine/matcher.py`
3. **Add Resource Mapping**: Update `RESOURCE_TYPE_MAP` in `terraform/normalizer.py`
4. **Add Service Code**: Update `supported_services` in `config.py`
5. **Run Pricing Ingestion**: Download pricing for new service

Example adapter structure:

```python
from app.pricing.adapters.base import BaseAdapter

class NewServiceAdapter(BaseAdapter):
    def calculate_cost(self, resource: Dict) -> Dict:
        # Query pricing database
        pricing = self.query_pricing(
            service_code="ServiceCode",
            region_code=resource.get("region"),
            filters={"attribute": "value"}
        )
        
        # Calculate cost
        monthly_cost = pricing.price_per_unit * quantity
        
        return self.format_cost_result(
            monthly_cost,
            {"breakdown": "details"},
            ["warnings"]
        )
```

## 🐛 Troubleshooting

### No Pricing Data

```bash
# Check pricing version
curl http://localhost:8000/api/pricing/stats

# Manually trigger update
curl -X POST http://localhost:8000/api/pricing/update
```

### Database Issues

```bash
# Reset database
docker-compose down -v
docker-compose up -d
# Re-run pricing ingestion
```

### Logs

```bash
# View backend logs
docker-compose logs -f backend

# View all logs
docker-compose logs -f
```

## 🚀 Production Deployment

### Environment Variables

Set production values:

```env
APP_ENV=production
DEBUG=false
POSTGRES_PASSWORD=<strong-password>
CORS_ORIGINS=https://yourdomain.com
```

### Database Backups

```bash
# Backup
docker-compose exec postgres pg_dump -U postgres aws_cost_calculator > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres aws_cost_calculator < backup.sql
```

### Scaling

- Use managed PostgreSQL (RDS, Cloud SQL)
- Add Redis cluster for caching
- Deploy backend with multiple replicas
- Use CDN for frontend

## 📝 License

MIT License - See LICENSE file

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## 📧 Support

For issues and questions:
- GitHub Issues: [Create Issue]
- Documentation: See `/docs` directory

---

**Built with**: Python 3.11, FastAPI, React, PostgreSQL, Docker
