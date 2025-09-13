# Odoo MCP Server

An MCP (Model Context Protocol) server for Odoo that allows interaction with Odoo online instances via XML-RPC API.

## Features

- **CRUD Operations**: Create, read, update, and delete records in any Odoo model
- **Model Introspection**: Get field definitions and metadata for Odoo models
- **Custom Method Calls**: Execute custom methods on Odoo models
- **Async Support**: Built with async/await for better performance
- **Error Handling**: Comprehensive error handling with detailed error messages
- **Type Safety**: Full type hints throughout the codebase

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd odoo.mcp
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the package in development mode:
```bash
pip install -e .
```

## Configuration

The server can be configured using environment variables or by passing configuration directly.

### Environment Variables

Create a `.env` file in the project root:

```env
ODOO_URL=https://your-odoo-instance.odoo.com
ODOO_DATABASE=your_database_name
ODOO_USERNAME=your_username
ODOO_PASSWORD=your_password
SERVER_NAME=odoo-mcp
```

### Configuration Options

- `ODOO_URL`: Your Odoo instance URL
- `ODOO_DATABASE`: Database name
- `ODOO_USERNAME`: Odoo username
- `ODOO_PASSWORD`: Odoo password
- `SERVER_NAME`: MCP server name (default: "odoo-mcp")

## Usage

### Running the Server

To start the MCP server:

```bash
python -m odoo_mcp.server
```

### Available Tools

The server provides the following MCP tools:

#### 1. Search Records
Search for records in any Odoo model.

**Parameters:**
- `model` (required): Odoo model name (e.g., "res.partner")
- `domain` (optional): Search filters as a list
- `fields` (optional): Fields to retrieve
- `limit` (optional): Maximum number of records
- `offset` (optional): Number of records to skip
- `order` (optional): Sort order

**Example:**
```json
{
  "model": "res.partner",
  "domain": [["is_company", "=", true]],
  "fields": ["id", "name", "email"],
  "limit": 10
}
```

#### 2. Create Record
Create a new record in an Odoo model.

**Parameters:**
- `model` (required): Odoo model name
- `values` (required): Field values as a dictionary

**Example:**
```json
{
  "model": "res.partner",
  "values": {
    "name": "New Company",
    "is_company": true,
    "email": "contact@newcompany.com"
  }
}
```

#### 3. Update Record
Update an existing record.

**Parameters:**
- `model` (required): Odoo model name
- `record_id` (required): ID of the record to update
- `values` (required): Field values to update

**Example:**
```json
{
  "model": "res.partner",
  "record_id": 123,
  "values": {
    "email": "newemail@company.com",
    "phone": "+1234567890"
  }
}
```

#### 4. Delete Record
Delete a record from an Odoo model.

**Parameters:**
- `model` (required): Odoo model name
- `record_id` (required): ID of the record to delete

**Example:**
```json
{
  "model": "res.partner",
  "record_id": 123
}
```

#### 5. Get Model Fields
Get field definitions for an Odoo model.

**Parameters:**
- `model` (required): Odoo model name

**Example:**
```json
{
  "model": "res.partner"
}
```

#### 6. Call Model Method
Execute a custom method on an Odoo model.

**Parameters:**
- `model` (required): Odoo model name
- `method` (required): Method name to call
- `args` (optional): Positional arguments as a list
- `kwargs` (optional): Keyword arguments as a dictionary

**Example:**
```json
{
  "model": "res.partner",
  "method": "name_get",
  "args": [[1, 2, 3]]
}
```

### Resources

The server provides access to Odoo model documentation and schemas:

- **Model Schemas**: Introspect field definitions for any Odoo model
- **API Documentation**: Access to Odoo XML-RPC API documentation

### Prompts

Pre-configured prompts for common Odoo operations:

- **Analyze Model**: Get comprehensive information about an Odoo model
- **Data Migration**: Help with data migration between Odoo instances
- **Custom Reports**: Generate custom reports from Odoo data

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

The project uses several tools for code quality:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
odoo.mcp/
├── src/
│   └── odoo_mcp/
│       ├── __init__.py
│       ├── server.py      # Main MCP server
│       ├── client.py      # Odoo XML-RPC client
│       ├── config.py      # Configuration management
│       └── tools.py       # MCP tool implementations
├── tests/
│   ├── __init__.py
│   └── test_basic.py
├── config/
│   └── .env.example
├── pyproject.toml
└── README.md
```

## Error Handling

The server includes comprehensive error handling:

- **Authentication Errors**: Clear messages for login failures
- **Permission Errors**: Detailed access control error messages
- **Validation Errors**: Field validation and constraint errors
- **Network Errors**: Connection and timeout handling
- **General Errors**: Graceful handling of unexpected errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the GitHub issues
2. Create a new issue with detailed information
3. Include error messages and configuration details