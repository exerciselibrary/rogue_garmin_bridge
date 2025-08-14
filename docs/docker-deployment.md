# Docker Deployment Guide

This guide covers deploying the Rogue Garmin Bridge application using Docker and Docker Compose across different environments.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (for cloning the repository)
- curl (for health checks)

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd rogue-garmin-bridge
```

2. Copy and customize environment file:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Deploy the application:
```bash
./scripts/deploy.sh deploy
```

## Environment Configurations

### Development Environment

For local development with hot reloading and debugging:

```bash
# Deploy development environment
./scripts/deploy.sh -e development deploy

# Or manually
docker-compose -f docker-compose.dev.yml --env-file .env up -d
```

Features:
- Hot reloading with volume mounts
- Debug port exposed (5678)
- Simulator enabled by default
- Development tools included
- Relaxed security settings

### Staging Environment

For testing in a production-like environment:

```bash
# Deploy staging environment
./scripts/deploy.sh -e staging deploy

# Or manually
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d
```

Features:
- Production-like configuration
- Simulator can be enabled/disabled
- Shorter data retention
- Enhanced logging
- Test data generation tools

### Production Environment

For production deployment:

```bash
# Deploy production environment
./scripts/deploy.sh -e production deploy

# Or manually
docker-compose -f docker-compose.prod.yml --env-file .env up -d
```

Features:
- Optimized multi-stage builds
- Security hardening
- Resource limits
- Log rotation
- Health checks
- Optional monitoring stack

## Docker Compose Profiles

Use profiles to enable additional services:

### Nginx Reverse Proxy

```bash
./scripts/deploy.sh -e production -p nginx deploy
```

Provides:
- SSL termination
- Load balancing
- Static file serving
- Security headers

### Monitoring Stack

```bash
./scripts/deploy.sh -e production -p monitoring deploy
```

Includes:
- Prometheus metrics collection
- Grafana dashboards
- Alert management
- Performance monitoring

### Development Tools

```bash
./scripts/deploy.sh -e development -p tools deploy
```

Includes:
- Database viewer (Adminer)
- Test runners
- Code quality tools

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key (production) | `your-secret-key-here` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `5000` | Application port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `USE_SIMULATOR` | `false` | Enable simulator mode |
| `CONNECTION_TIMEOUT` | `30` | Bluetooth connection timeout |
| `DATA_RETENTION_DAYS` | `365` | Data retention period |

See `.env.example` for complete list.

## Health Checks

The application includes comprehensive health checks:

### Basic Health Check
```bash
curl http://localhost:5000/health
```

### Detailed Health Check
```bash
curl http://localhost:5000/health/detailed
```

### Kubernetes Probes
- Liveness: `/health/live`
- Readiness: `/health/ready`

## Storage and Volumes

### Development
Uses named volumes for easy cleanup:
- `dev_data` - Application data
- `dev_logs` - Log files
- `dev_fit_files` - Generated FIT files

### Production
Uses bind mounts for persistence:
- `./data` - Application data
- `./logs` - Log files
- `./fit_files` - Generated FIT files

## Networking

### Development
- Application: `http://localhost:5000`
- Debug port: `5678`

### Production
- Application: `http://localhost:5000`
- Prometheus: `http://localhost:9090` (with monitoring profile)
- Grafana: `http://localhost:3000` (with monitoring profile)

## Security Considerations

### Production Security

1. **Environment Variables**: Never commit sensitive data to version control
2. **SSL/TLS**: Use nginx profile with proper certificates
3. **Firewall**: Restrict access to necessary ports only
4. **Updates**: Regularly update base images and dependencies
5. **Secrets**: Use Docker secrets or external secret management

### Container Security

- Non-root user execution
- Read-only root filesystem where possible
- Resource limits
- Security scanning of images

## Troubleshooting

### Common Issues

1. **Bluetooth Access**
   - Ensure `privileged: true` is set
   - Use `network_mode: host` on Linux
   - Check Bluetooth adapter permissions

2. **Health Check Failures**
   ```bash
   # Check application logs
   ./scripts/deploy.sh -e production logs
   
   # Check health endpoint manually
   curl -v http://localhost:5000/health
   ```

3. **Database Issues**
   ```bash
   # Check database file permissions
   ls -la data/
   
   # Restore from backup
   ./scripts/deploy.sh restore
   ```

4. **Port Conflicts**
   - Change `APP_PORT` in environment file
   - Check for other services using the same port

### Log Analysis

```bash
# View all logs
./scripts/deploy.sh logs

# View specific service logs
docker-compose -f docker-compose.prod.yml logs rogue-garmin-bridge

# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f
```

## Backup and Recovery

### Create Backup
```bash
./scripts/deploy.sh backup
```

### Restore from Backup
```bash
./scripts/deploy.sh restore
```

### Manual Backup
```bash
# Stop application
./scripts/deploy.sh stop

# Create backup
tar -czf backup-$(date +%Y%m%d).tar.gz data/ config/ fit_files/

# Start application
./scripts/deploy.sh start
```

## Performance Tuning

### Resource Limits

Adjust in docker-compose files:
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '1.0'
    reservations:
      memory: 256M
      cpus: '0.5'
```

### Database Optimization

- Regular VACUUM operations
- Proper indexing
- Data archival policies

### Monitoring

Enable monitoring profile to track:
- CPU and memory usage
- Database performance
- Bluetooth connection quality
- Application response times

## Maintenance

### Regular Tasks

1. **Update Images**
   ```bash
   ./scripts/deploy.sh update
   ```

2. **Clean Up**
   ```bash
   ./scripts/deploy.sh cleanup
   ```

3. **Log Rotation**
   - Automatic with logrotate service
   - Manual: `docker-compose exec logrotate logrotate -f /etc/logrotate.conf`

4. **Database Maintenance**
   ```bash
   # Connect to database
   docker-compose exec rogue-garmin-bridge sqlite3 data/workouts.db
   
   # Run VACUUM
   VACUUM;
   ```

### Monitoring Alerts

Set up alerts for:
- Application health check failures
- High memory/CPU usage
- Disk space low
- Database errors
- Bluetooth connection issues

## Migration Guide

### From Development to Production

1. Export development data:
   ```bash
   ./scripts/deploy.sh -e development backup
   ```

2. Set up production environment:
   ```bash
   cp .env.example .env
   # Customize .env for production
   ```

3. Deploy production:
   ```bash
   ./scripts/deploy.sh -e production deploy
   ```

4. Import data if needed:
   ```bash
   ./scripts/deploy.sh restore
   ```

### Version Updates

1. Pull latest code:
   ```bash
   git pull origin main
   ```

2. Update deployment:
   ```bash
   ./scripts/deploy.sh update
   ```

3. Verify health:
   ```bash
   ./scripts/deploy.sh status
   ```

## Support

For issues and questions:
1. Check application logs
2. Verify health endpoints
3. Review this documentation
4. Check GitHub issues
5. Create new issue with logs and configuration details