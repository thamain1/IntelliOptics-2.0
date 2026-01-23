# IntelliOptics 2.0 - Installation Guide

## Prerequisites

Before installing, ensure you have:

> **Important:** Clone or install to a path **without spaces** (e.g., `C:\intellioptics-2.0` not `C:\intellioptics 2.0`). Spaces in paths can cause issues with Docker and command-line tools.

1. **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop)
2. **Azure CLI** - [Install Guide](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
3. **Azure Account** with access to:
   - Azure Container Registry (acrintellioptics)
   - Azure Storage Account (for image storage)
   - Optional: Azure Service Bus (for async processing)

## Quick Start (Windows)

### Option 1: Automated Installation

```powershell
# Run as Administrator
.\install-windows.ps1
```

### Option 2: Manual Installation

1. **Login to Azure**
   ```powershell
   az login
   az acr login --name acrintellioptics
   ```

2. **Pull Images**
   ```powershell
   docker pull acrintellioptics.azurecr.io/intellioptics/backend:v2.0.0
   docker pull acrintellioptics.azurecr.io/intellioptics/frontend:v2.0.0
   docker pull acrintellioptics.azurecr.io/intellioptics/worker:v2.0.0
   ```

3. **Configure Environment**
   ```powershell
   copy .env.template .env
   # Edit .env with your credentials
   ```

4. **Start Services**
   ```powershell
   docker compose -f docker-compose.prod.yml up -d
   ```

5. **Access Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Configuration

### Required Settings

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | Database password (generate secure password) |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Storage connection string |
| `API_SECRET_KEY` | JWT signing key (32+ characters) |

### Optional Settings

| Variable | Description |
|----------|-------------|
| `SENDGRID_API_KEY` | For email alerts |
| `TWILIO_*` | For SMS alerts |
| `SERVICE_BUS_CONN` | For async processing |

## Management Commands

```powershell
# View logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker compose -f docker-compose.prod.yml logs -f backend

# Stop all services
docker compose -f docker-compose.prod.yml down

# Restart services
docker compose -f docker-compose.prod.yml restart

# Update to new version
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Backend won't start
- Check database connection: `docker compose -f docker-compose.prod.yml logs postgres`
- Verify `.env` has correct `POSTGRES_PASSWORD`

### Can't pull images
- Ensure Azure CLI is logged in: `az login`
- Ensure ACR access: `az acr login --name acrintellioptics`

### Health check fails
- Wait 30 seconds for services to fully start
- Check logs: `docker compose -f docker-compose.prod.yml logs backend`

### .env file not found
- Ensure `.env` file exists in the `install` folder (same folder as `docker-compose.prod.yml`)
- Copy from template: `copy .env.template .env`
- On Windows, check for hidden `.txt` extension: `dir .env*`
- **If path contains spaces:** Rename folder to remove spaces (e.g., `C:\intellioptics-2.0` instead of `C:\intellioptics 2.0`)

## Image Versions

| Image | Version | Registry |
|-------|---------|----------|
| backend | v2.0.0 | acrintellioptics.azurecr.io/intellioptics/backend |
| frontend | v2.0.0 | acrintellioptics.azurecr.io/intellioptics/frontend |
| worker | v2.0.0 | acrintellioptics.azurecr.io/intellioptics/worker |

## Support

For issues, check:
- [Deployment Guide](../docs/DEPLOYMENT_GUIDE.md)
- [Quick Start](../docs/QUICKSTART.md)
