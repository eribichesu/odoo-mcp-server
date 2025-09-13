<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Odoo MCP Server Project Instructions

This project is an MCP (Model Context Protocol) server for Odoo integration that allows interaction with Odoo online instances via XML-RPC API.

## Project Overview
- **Type**: Python MCP Server for Odoo
- **Purpose**: Provide tools for CRUD operations, model introspection, and reporting on Odoo instances
- **Architecture**: Async Python server with XML-RPC client for Odoo communication

## Development Guidelines
- Use async/await patterns for all MCP tools
- Follow MCP SDK conventions for tool definitions
- Implement proper error handling for Odoo API calls
- Use type hints throughout the codebase
- Follow Python best practices (PEP 8, docstrings)

## Key Components
- `src/odoo_mcp/server.py`: Main MCP server implementation
- `src/odoo_mcp/client.py`: Odoo XML-RPC client
- `src/odoo_mcp/tools/`: Individual MCP tools for Odoo operations
- `config/`: Configuration templates and examples

## Testing
- Use pytest for unit tests
- Mock Odoo API responses for testing
- Test both successful and error scenarios