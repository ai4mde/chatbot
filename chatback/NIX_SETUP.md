# Nix Development Environment for Chatback

This document explains how to set up and use the Nix development environment for the Chatback project.

## Prerequisites

1. Install Nix package manager:
   ```bash
   sh <(curl -L https://nixos.org/nix/install) --daemon
   ```

2. (Optional but recommended) Install direnv for automatic environment loading:
   ```bash
   # On macOS with Homebrew
   brew install direnv
   
   # On Ubuntu/Debian
   apt-get install direnv
   
   # On NixOS
   nix-env -iA nixos.direnv
   ```

3. Configure direnv in your shell (add to your `.bashrc`, `.zshrc`, etc.):
   ```bash
   eval "$(direnv hook bash)"  # For bash
   eval "$(direnv hook zsh)"   # For zsh
   ```

4. Start the required services (if not already running):
   ```bash
   # Using podman
   podman run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:17-alpine
   podman run -d --name redis -p 6379:6379 redis:7-alpine
   podman run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
   ```

## Using the Nix Shell

### Option 1: With direnv (Recommended)

1. Allow direnv in the project directory:
   ```bash
   cd chatback
   direnv allow
   ```

2. The environment will automatically load when you enter the directory.

### Option 2: Manual Shell Activation

1. Enter the Nix shell manually:
   ```bash
   cd chatback
   nix-shell
   ```

## Available Commands

Once inside the Nix shell, you can use the following commands:

- `run-api` - Start the API server
- `run-tests` - Run tests
- `run-migrations` - Run database migrations

You can also use the development helper script:

```bash
./bin/dev help
```

## Environment Details

The Nix shell provides:

- Python 3.13 with uv package manager (matching the Dockerfile)
- Development tools (git, podman, docker-compose)
- Node.js 20 and npm (for frontend development)
- All system libraries needed for compilation

## External Services

The environment assumes the following services are already running:

- PostgreSQL on port 5432
- Redis on port 6379
- Qdrant on port 6333

You can check the status of these services with:

```bash
./bin/dev status
```

## Package Management with uv

This environment uses [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver, which is also used in the Dockerfile. This ensures development-production parity.

Benefits of using uv:
- Faster package installation
- Better compatibility with Python 3.13
- Consistent with the production environment

## Customizing the Environment

You can customize the environment by editing the `shell.nix` file. After making changes, exit and re-enter the directory (if using direnv) or restart the shell (if using nix-shell).

## Troubleshooting

### Missing Python Packages

If you need additional Python packages:

1. Add them to `requirements.txt`
2. Run `./bin/dev rebuild` to rebuild the virtual environment

### System Library Issues

If you encounter errors about missing system libraries, add them to the `buildInputs` list in `shell.nix`.

### Virtual Environment Problems

If the virtual environment becomes corrupted:

```bash
./bin/dev rebuild
```

Or manually:

```bash
rm -rf .venv
exit
cd chatback  # Re-enter the directory to trigger environment setup
```

### Package Version Conflicts

If you encounter package version conflicts:

1. Try using `uv pip install --no-deps <package>` to install specific versions
2. If that doesn't work, you may need to modify the requirements.txt file 