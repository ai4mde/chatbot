{ pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz") {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python
    python313
    python313Packages.pip
    python313Packages.virtualenv
    python313Packages.uvicorn
    python313Packages.fastapi
    python313Packages.python-dotenv
    python313Packages.numpy
    python313Packages.pandas
    python313Packages.scipy
    python313Packages.scikit-learn
    python313Packages.pytest
    python313Packages.black
    python313Packages.isort
    python313Packages.mypy
    python313Packages.coverage
    python313Packages.alembic
    python313Packages.mako
    python313Packages.httpx
    python313Packages.pydantic
    python313Packages.pydantic-core
    python313Packages.pydantic-settings
    python313Packages.sqlalchemy
    python313Packages.psycopg2
    python313Packages.python-jose
    python313Packages.passlib
    python313Packages.python-multipart
    python313Packages.redis
    python313Packages.cryptography
    python313Packages.bcrypt
    python313Packages.tomli
    python313Packages.tomli-w
    python313Packages.email-validator
    python313Packages.qdrant-client
    python313Packages.argon2-cffi
    python313Packages.termcolor
    
    # System libraries
    glibc
    glibc.dev
    stdenv.cc.cc.lib
    
    # PostgreSQL
    postgresql_15
    postgresql_15.lib
    
    # OpenSSL
    openssl
    openssl.dev
    
    # Rust and Cargo
    rustc
    cargo
    rustfmt
    rust-analyzer
    
    # System dependencies
    gcc
    gnumake
    pkg-config
    
    # Development tools
    git
    podman
    docker-compose
    nix-tree
    nix
    
    # Node.js (for frontend)
    nodejs_20
    nodejs_22
    
    # For C extensions
    musl
    musl.dev
  ];
  
  shellHook = ''
    # Set environment variables
    export PYTHONPATH="$PWD:$PYTHONPATH"
    export PATH="$HOME/.local/bin:$PATH"
    export PATH="$PWD/.venv/bin:$PATH"
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONUNBUFFERED=1
    
    # Create symbolic link to the external data directory
    echo "Setting up data directory..."
    if [ -L "data" ]; then
      echo "Removing existing data symlink..."
      rm data
    fi
    
    if [ -d "data" ]; then
      echo "Warning: data directory exists but is not a symlink. Renaming to data.bak..."
      mv data data.bak
    fi
    
    echo "Creating symlink to external data directory..."
    ln -s /opt/ai4mde/048/data data
    echo "Data directory linked successfully!"
    
    # Set data path environment variable
    export CHATBOT_DATA_PATH="$PWD/data"
    echo "CHATBOT_DATA_PATH set to: $CHATBOT_DATA_PATH"
    
    # Set PostgreSQL environment variables
    export PGDATA="$PWD/data/postgres"
    export PGHOST="localhost"
    export PGPORT="5432"
    
    # Set Rust environment variables
    export RUSTUP_HOME="$PWD/.rustup"
    export CARGO_HOME="$PWD/.cargo"
    export PATH="$CARGO_HOME/bin:$PATH"
    
    # Set library paths for building extensions
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.openssl.out
      pkgs.postgresql_15.lib
      pkgs.glibc
      pkgs.musl
    ]}:$LD_LIBRARY_PATH"
    
    # Set Rust build environment variables
    export RUSTFLAGS="-C link-args=-Wl,-rpath,$LD_LIBRARY_PATH"
    export PYO3_PYTHON="${pkgs.python313}/bin/python"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
      echo "Creating virtual environment..."
      python -m venv .venv
      source .venv/bin/activate
      python -m pip install --upgrade pip
      
      # Install asyncpg from a pre-built wheel
      echo "Installing asyncpg from pre-built wheel..."
      python -m pip install asyncpg>=0.29.0,<0.31.0 --only-binary=:all: --prefer-binary
      
      # Install argon2-cffi from a pre-built wheel
      echo "Installing argon2-cffi from pre-built wheel..."
      python -m pip install argon2-cffi --prefer-binary
      
      # Install termcolor for tests
      echo "Installing termcolor for tests..."
      python -m pip install termcolor --prefer-binary
      
      # Add all Nix Python packages to PYTHONPATH
      echo "Adding Nix Python packages to PYTHONPATH..."
      NIX_PYTHON_PACKAGES=(
        "pydantic" 
        "pydantic_core" 
        "pydantic_settings" 
        "email_validator"
        "numpy"
        "pandas"
        "scipy"
        "scikit_learn"
        "fastapi"
        "uvicorn"
        "sqlalchemy"
        "psycopg2"
        "python_jose"
        "passlib"
        "python_multipart"
        "redis"
        "cryptography"
        "bcrypt"
        "qdrant_client"
        "argon2_cffi"
        "termcolor"
      )
      
      for pkg in "''${NIX_PYTHON_PACKAGES[@]}"; do
        pkg_path=$(python -c "import $pkg; print($pkg.__path__[0] if hasattr($pkg, '__path__') else $pkg.__file__)" 2>/dev/null || echo "")
        if [ -n "$pkg_path" ]; then
          pkg_dir=$(dirname "$pkg_path")
          echo "export PYTHONPATH=$pkg_dir:\$PYTHONPATH" >> .venv/bin/activate
          echo "Added $pkg to PYTHONPATH"
        else
          echo "Warning: Could not find path for $pkg"
        fi
      done
      
      # Uninstall the project first to avoid dependency conflicts
      echo "Uninstalling existing project (if any)..."
      python -m pip uninstall -y chatback
      
      # Install project in development mode
      echo "Installing project in development mode..."
      python -m pip install -e . --prefer-binary
    else
      source .venv/bin/activate
    fi
    
    # Create a function to update packages
    update_packages() {
      echo "Updating packages..."
      source .venv/bin/activate
      python -m pip install --upgrade pip
      
      # Install asyncpg from a pre-built wheel
      echo "Installing asyncpg from pre-built wheel..."
      python -m pip install asyncpg>=0.29.0,<0.31.0 --only-binary=:all: --prefer-binary
      
      # Install argon2-cffi from a pre-built wheel
      echo "Installing argon2-cffi from pre-built wheel..."
      python -m pip install argon2-cffi --prefer-binary
      
      # Install termcolor for tests
      echo "Installing termcolor for tests..."
      python -m pip install termcolor --prefer-binary
      
      # Uninstall the project first to avoid dependency conflicts
      echo "Uninstalling existing project..."
      python -m pip uninstall -y chatback
      
      # Install any missing packages with binary preference
      echo "Checking for missing packages..."
      python -m pip install fastapi uvicorn sqlalchemy psycopg2 python-jose passlib python-multipart redis email-validator --prefer-binary
      
      # Reinstall project in development mode
      echo "Reinstalling project in development mode..."
      python -m pip install -e . --prefer-binary
      
      echo "Package update complete!"
    }
    
    # Create a function to rebuild the environment
    rebuild_env() {
      echo "Rebuilding virtual environment..."
      rm -rf .venv
      python -m venv .venv
      source .venv/bin/activate
      python -m pip install --upgrade pip
      
      # Install asyncpg from a pre-built wheel
      echo "Installing asyncpg from pre-built wheel..."
      python -m pip install asyncpg>=0.29.0,<0.31.0 --only-binary=:all: --prefer-binary
      
      # Install argon2-cffi from a pre-built wheel
      echo "Installing argon2-cffi from pre-built wheel..."
      python -m pip install argon2-cffi --prefer-binary
      
      # Install termcolor for tests
      echo "Installing termcolor for tests..."
      python -m pip install termcolor --prefer-binary
      
      # Add all Nix Python packages to PYTHONPATH
      echo "Adding Nix Python packages to PYTHONPATH..."
      NIX_PYTHON_PACKAGES=(
        "pydantic" 
        "pydantic_core" 
        "pydantic_settings" 
        "email_validator"
        "numpy"
        "pandas"
        "scipy"
        "scikit_learn"
        "fastapi"
        "uvicorn"
        "sqlalchemy"
        "psycopg2"
        "python_jose"
        "passlib"
        "python_multipart"
        "redis"
        "cryptography"
        "bcrypt"
        "qdrant_client"
        "argon2_cffi"
        "termcolor"
      )
      
      for pkg in "''${NIX_PYTHON_PACKAGES[@]}"; do
        pkg_path=$(python -c "import $pkg; print($pkg.__path__[0] if hasattr($pkg, '__path__') else $pkg.__file__)" 2>/dev/null || echo "")
        if [ -n "$pkg_path" ]; then
          pkg_dir=$(dirname "$pkg_path")
          echo "export PYTHONPATH=$pkg_dir:\$PYTHONPATH" >> .venv/bin/activate
          echo "Added $pkg to PYTHONPATH"
        else
          echo "Warning: Could not find path for $pkg"
        fi
      done
      
      # Uninstall the project first to avoid dependency conflicts
      echo "Uninstalling existing project (if any)..."
      python -m pip uninstall -y chatback
      
      # Install project in development mode
      echo "Installing project in development mode..."
      python -m pip install -e . --prefer-binary
      
      echo "Environment rebuild complete!"
    }
    
    # Export functions
    export -f update_packages
    export -f rebuild_env
    
    # Print welcome message
    echo ""
    echo "========================================="
    echo "Welcome to Chatback Development Environment"
    echo "========================================="
    echo ""
    echo "Python: $(python --version)"
    echo "Node: $(node --version)"
    echo "Rust: $(rustc --version)"
    echo "NixOS: Using unstable channel (25.05)"
    echo ""
    echo "Environment ready!"
    echo "Using external services:"
    echo "- PostgreSQL: Running on port 5432"
    echo "- Redis: Running on port 6379"
    echo "- Qdrant: Running on port 6333"
    echo "Data directory:"
    echo "- Using data from: /opt/ai4mde/048/data"
    echo ""
    echo "Available commands:"
    echo "run-api      - Start the API server"
    echo "run-tests    - Run tests"
    echo "run-migrations - Run database migrations"
    echo "update_packages - Update Python packages"
    echo "rebuild_env  - Rebuild the virtual environment"
    echo "Or use ./bin/dev for more options"
    echo ""
    echo "Note: All required packages are now provided by the Nix shell"
    echo "No need to use install-wheels script anymore"
    echo ""
    
    # Create aliases for common commands
    alias run-api="./bin/dev api"
    alias run-tests="./bin/dev test"
    alias run-migrations="./bin/dev migrate"
  '';
}
