# AWS Cost Estimation Platform API Documentation

## Service Discovery
### List All Services
`GET /api/services`
Returns a list of all registered services and their capabilities.

### Get Service Metadata
`GET /api/services/{service_id}/metadata`
Returns specific metadata (regions, instance types, etc.) for a service. Powered by `metadata.py`.

## Estimation
### Estimate Cost
`POST /api/estimate/{service_id}`

**Payload**: JSON object matching the service's schema.
**Response**:
```json
{
  "service": "ec2",
  "total_cost": 123.45,
  "breakdown": { ... }
}
```

## Pricing Data
### Get Raw/Normalized Pricing
`GET /api/pricing/{service_id}`
Returns the full pricing dataset for the service (use with caution on large files).

## Architecture
- **Dynamic Routing**: `estimate_router.py` loads the estimator module at runtime.
- **Plugin System**: To add a route, you do NOT edit the backend. You add the service to the registry and create the plugin files.
