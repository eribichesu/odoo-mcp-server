# Development Guide

This guide covers development setup, testing, and contribution guidelines for the Odoo MCP Server.

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git
- Virtual environment tools (venv or conda)

### Quick Setup

1. Clone and setup:
```bash
git clone <repository-url>
cd odoo.mcp
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

2. Configure environment:
```bash
cp config/.env.example .env
# Edit .env with your Odoo credentials
```

3. Run tests:
```bash
pytest tests/ -v
```

4. Quick start (with demo data):
```bash
python quickstart.py
```

## Development Tools

### Code Quality

The project uses several tools for code quality:

```bash
# Format code
black src/ tests/

# Sort imports  
isort src/ tests/

# Type checking
mypy src/

# Run all quality checks
black src/ tests/ && isort src/ tests/ && mypy src/
```

### Testing

```bash
# Run all tests with coverage
pytest tests/ --cov=src/ --cov-report=html

# Run specific test
pytest tests/test_basic.py::test_search_records_tool_success -v

# Run tests with different verbosity
pytest tests/ -v -s
```

## Project Structure

```
odoo.mcp/
├── src/odoo_mcp/          # Main package
│   ├── __init__.py        # Package exports
│   ├── server.py          # FastMCP server implementation
│   ├── client.py          # Odoo XML-RPC client
│   ├── config.py          # Configuration management
│   └── tools.py           # MCP tool implementations
├── tests/                 # Test suite
├── config/                # Configuration examples
├── .github/               # GitHub configuration
├── pyproject.toml         # Project configuration
├── quickstart.py          # Development quick-start
└── README.md             # User documentation
```

## Adding New Features

### Adding a New MCP Tool

1. Implement the tool function in `src/odoo_mcp/tools.py`:
```python
async def my_new_tool(
    client: OdooClient,
    param1: str,
    param2: Optional[int] = None,
) -> Dict[str, Any]:
    """Tool description."""
    try:
        result = await client.some_method(param1, param2)
        return {"success": True, "result": result}
    except OdooError as e:
        return {"success": False, "error": str(e)}
```

2. Register the tool in `src/odoo_mcp/server.py`:
```python
@app.tool()
async def my_new_tool_mcp(param1: str, param2: int = 100):
    """Tool description for MCP."""
    client = await get_odoo_client()
    return await my_new_tool(client, param1, param2)
```

3. Add tests in `tests/test_basic.py` or create a new test file.

4. Update documentation in `README.md`.

### Adding Configuration Options

1. Add field to `Settings` class in `src/odoo_mcp/config.py`:
```python
new_setting: str = Field(
    default="default_value",
    description="Setting description",
)
```

2. Update `config/.env.example` with the new environment variable.

3. Add tests for the new setting.

## Testing with Real Odoo

For testing with a real Odoo instance:

1. Create a test database or use a sandbox environment
2. Create API credentials (username/password or API key)
3. Set environment variables:
```bash
export ODOO_URL="https://your-instance.odoo.com"
export ODOO_DATABASE="your_database"
export ODOO_USERNAME="your_username"
export ODOO_PASSWORD="your_password"
```

4. Run integration tests (when available):
```bash
pytest tests/integration/ -v --real-odoo
```

## Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
python quickstart.py
```

### Common Issues

1. **Import errors**: Make sure package is installed with `pip install -e .`
2. **Configuration errors**: Check `.env` file and required environment variables
3. **Connection errors**: Verify Odoo URL, database name, and credentials
4. **Permission errors**: Ensure Odoo user has appropriate access rights

### Testing MCP Integration

To test the MCP server with Claude Desktop or other MCP clients:

1. Build the server:
```bash
pip install -e .
```

2. Configure your MCP client to connect to the server
3. Test basic operations through the client interface

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes with tests
4. Ensure all tests pass: `pytest tests/`
5. Run code quality checks: `black . && isort . && mypy src/`
6. Commit with descriptive messages
7. Push and create a pull request

### Commit Message Format

```
type: short description

Longer description if needed, explaining what and why.

- Bullet points for multiple changes
- Reference issues: Fixes #123
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`

### Code Style

- Follow PEP 8
- Use type hints throughout
- Write docstrings for all public functions
- Keep functions focused and small
- Add tests for new functionality
- Update documentation when needed

## Release Process

1. Update version in `pyproject.toml` and `src/odoo_mcp/config.py`
2. Update `CHANGELOG.md` with new features and fixes
3. Run full test suite: `pytest tests/`
4. Create release commit: `git commit -m "Release v0.2.0"`
5. Tag release: `git tag v0.2.0`
6. Push: `git push && git push --tags`

The CI/CD pipeline will handle building and publishing the release.