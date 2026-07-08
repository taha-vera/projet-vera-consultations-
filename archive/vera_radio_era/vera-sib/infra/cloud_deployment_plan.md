# Phase 2 W2 — Cloud Deployment Plan

## Infrastructure Specification

### VPS Requirements
- **Provider**: Hetzner Cloud / Scaleway
- **Specs**: 2 vCPU, 4GB RAM, 40GB SSD
- **OS**: Ubuntu 24.04 LTS
- **Cost**: ~$10-15/month

### Database
- **Type**: PostgreSQL 15
- **Size**: 10GB
- **Cost**: ~$5-10/month

### Storage
- **Type**: S3-compatible
- **Size**: 100GB (aggregates only)
- **Cost**: ~$5/month

### Total Monthly: ~$30-40

## Deployment Checklist

### Week 1: Setup
- [ ] Hetzner/Scaleway account
- [ ] VPS provisioning
- [ ] Ubuntu 24.04 installation
- [ ] PostgreSQL setup
- [ ] Firewall (port 443 only)
- [ ] SSL/TLS (Let's Encrypt)

### Week 2: Application
- [ ] Clone VERA repo
- [ ] Python dependencies
- [ ] API deployment
- [ ] Service configuration

### Week 3: Database
- [ ] PostgreSQL schema
- [ ] FMA data migration
- [ ] Automated backups
- [ ] Recovery testing

### Week 4: Testing + Launch
- [ ] Load testing
- [ ] Security audit
- [ ] Monitoring setup
- [ ] Public launch

## API Endpoints

### GET /api/v1/genres
Returns list of all genre profiles

### GET /api/v1/genre/{name}
Returns detailed statistics for genre

### POST /api/v1/validate
Validate new track metadata

## Monitoring

- API response time: < 200ms
- Database queries: < 50ms
- Error rate: < 0.1%
- Uptime: > 99.9%

