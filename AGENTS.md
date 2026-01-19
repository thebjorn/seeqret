# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.
Consult CLAUDE.md/GEMINI.md for agent-specific instructions.

## Project Overview

Seeqret is a Python CLI tool and library for securely storing and transferring code secrets (passwords, API keys, etc.). Secrets are stored encrypted in a SQLite database with platform-specific protections (encrypted folders on Windows, 0600 permissions on Linux).

## virtual Environments

Make sure to always use the seeqret311 virtual environment for development and testing.

## Build and Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run all tests with coverage
pytest -vv --cov=seeqret --cov-report=xml tests/

# Run a single test file
pytest tests/test_cli.py -v

# Run a specific test
pytest tests/test_cli.py::test_function_name -v

# Lint
flake8 --max-line-length 100 seeqret/
```

## Architecture

### Core Components

- **CLI entry point**: `seeqret/main.py` - Click-based CLI with commands organized into groups (`add`, `rm`, `edit`, `server`)
- **Storage layer**: `seeqret/storage/` - SQLite-backed storage with encrypted values
  - `SqliteStorage` class handles all database operations
  - Secrets are stored encrypted using Fernet (AES) symmetric encryption
- **Encryption**: `seeqret/seeqrypt/`
  - `aes_fernet.py` - Symmetric encryption for local storage
  - `nacl_backend.py` - Asymmetric encryption (NaCl/libsodium) for secure transfer between users
- **Models**: `seeqret/models/`
  - `Secret` - Encrypts/decrypts values on access via property
  - `User` - Stores username, email, and public key

### Key Patterns

**Filter Strings**: Secrets are queried using filter strings with format `app:env:key`, supporting glob patterns:
- `:dev:POSTGRES_*` - All keys starting with POSTGRES_ in dev environment
- `myapp::` - All secrets for myapp across all environments
- `*` matches anything, `?` matches single character

**Serializers** (`seeqret/serializers/`): Multiple output formats for exporting secrets:
- `json-crypt` - Encrypted JSON for secure transfer
- `command` - Single-line command for chat/terminal sharing
- `env` - .env file format

**Environment**: The vault location is set via `SEEQRET` environment variable. The `seeqret_dir()` context manager handles changing to the vault directory.

### Database

SQLite database (`seeqrets.db`) with tables:
- `users` - username, email, pubkey
- `secrets` - app, env, key, value (encrypted), type

Migrations in `seeqret/migrations/`.

## API Usage

```python
import seeqret
# Fetch at point of use, not in settings files
password = seeqret.get("db_password", app="myapp", env="prod")
```

## Testing

Tests use Click's `CliRunner` for CLI testing. Test utilities in `tests/clirunner_utils.py`. The `SEEQRET` environment variable is mocked to point to test vault directories.

## Style Guide
- Follow PEP 8 for Python code.
- Use type hints for all functions and methods.
- Docstrings for all public functions/classes using format in STYLEGUIDE.md.
- STYLEGUIDE.md has more details and overrides PEP8 where necessary.
