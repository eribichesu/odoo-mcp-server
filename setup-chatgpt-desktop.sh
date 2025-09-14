#!/bin/bash

# ChatGPT Desktop MCP Server Setup Script
# This script helps configure the Odoo MCP server for ChatGPT Desktop

echo "🚀 ChatGPT Desktop - Odoo MCP Server Setup"
echo "=" * 50

# Function to check if a directory exists and create it if not
create_dir_if_not_exists() {
    if [ ! -d "$1" ]; then
        echo "📁 Creating directory: $1"
        mkdir -p "$1"
    else
        echo "✅ Directory exists: $1"
    fi
}

# Function to copy config file
copy_config() {
    local source="$1"
    local dest="$2"
    
    if [ -f "$source" ]; then
        echo "📋 Copying config from $source to $dest"
        cp "$source" "$dest"
        echo "✅ Configuration file copied successfully"
    else
        echo "❌ Source file not found: $source"
        return 1
    fi
}

echo ""
echo "🔍 Detecting ChatGPT Desktop configuration..."

# Common ChatGPT Desktop configuration paths
CHATGPT_CONFIG_DIRS=(
    "$HOME/.config/chatgpt-desktop"
    "$HOME/Library/Application Support/ChatGPT Desktop"
    "$HOME/.chatgpt-desktop"
    "$HOME/AppData/Roaming/ChatGPT Desktop"
)

# Check which configuration directory exists or should be created
CONFIG_DIR=""
for dir in "${CHATGPT_CONFIG_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        CONFIG_DIR="$dir"
        echo "✅ Found ChatGPT Desktop config directory: $CONFIG_DIR"
        break
    fi
done

# If no directory found, use the most common one
if [ -z "$CONFIG_DIR" ]; then
    CONFIG_DIR="$HOME/.config/chatgpt-desktop"
    echo "📁 Will create config directory: $CONFIG_DIR"
fi

echo ""
echo "📦 Setting up MCP server configuration..."

# Create configuration directory
create_dir_if_not_exists "$CONFIG_DIR"

# Copy the MCP configuration
PROJECT_DIR="/Users/edoardo.ribichesu/vscode/odoo.mcp"
SOURCE_CONFIG="$PROJECT_DIR/odoo-mcp-chatgpt-config.json"
DEST_CONFIG="$CONFIG_DIR/mcp-config.json"

if copy_config "$SOURCE_CONFIG" "$DEST_CONFIG"; then
    echo "✅ MCP server configuration installed"
else
    echo "❌ Failed to install MCP configuration"
    exit 1
fi

echo ""
echo "🔧 Configuration Summary:"
echo "   Config file: $DEST_CONFIG"
echo "   Server script: $PROJECT_DIR/src/odoo_mcp/server.py"
echo "   Python path: $PROJECT_DIR/.venv/bin/python"
echo "   Working directory: $PROJECT_DIR"

echo ""
echo "📋 Next Steps:"
echo "1. Restart ChatGPT Desktop completely"
echo "2. Look for MCP/Extensions settings in ChatGPT Desktop"
echo "3. Test the connection by asking: 'What MCP tools are available?'"
echo "4. Try: 'Check my Odoo connection'"

echo ""
echo "🔍 Alternative Configuration Locations:"
echo "If the above doesn't work, try placing the config file in:"
for dir in "${CHATGPT_CONFIG_DIRS[@]}"; do
    echo "   - $dir/mcp-config.json"
done

echo ""
echo "📞 Need Help?"
echo "If you encounter issues:"
echo "1. Check ChatGPT Desktop documentation for MCP support"
echo "2. Look for extension/plugin settings in the app"
echo "3. Verify the configuration file location"

echo ""
echo "🎉 Setup complete! Your Odoo MCP server is ready for ChatGPT Desktop."