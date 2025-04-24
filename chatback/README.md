# Chatback API

Backend service for the AI4MDE chat application.

## Development Setup

1. Enter the Nix shell:
   ```bash
   cd chatback
   nix-shell
   ```

2. Start the API server:
   ```bash
   ./bin/dev api
   ```

3. Run tests:
   ```bash
   ./bin/dev test
   ```

4. Run database migrations:
   ```bash
   ./bin/dev migrate
   ```

## Environment

The application requires the following services:
- PostgreSQL: Running on port 5432
- Redis: Running on port 6379
- Qdrant: Running on port 6333

## Configuration

Configuration is managed through environment variables defined in `config/chatback.env`. 