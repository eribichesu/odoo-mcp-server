#!/usr/bin/env python3
"""
Test script to verify Odoo MCP server works with ChatGPT Desktop configuration.
"""

import json
import subprocess
import sys
import os
import time

def test_chatgpt_desktop_config():
    """Test MCP server with ChatGPT Desktop configuration format."""
    
    print("🧪 Testing Odoo MCP Server for ChatGPT Desktop")
    print("=" * 60)
    
    # Load the ChatGPT Desktop configuration
    config_file = "/Users/edoardo.ribichesu/vscode/odoo.mcp/odoo-mcp-chatgpt-config.json"
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print(f"✅ Configuration loaded from: {config_file}")
        
        # Extract server configuration
        odoo_config = config["mcpServers"]["odoo"]
        python_cmd = odoo_config["command"]
        script_path = odoo_config["args"][0]
        working_dir = odoo_config["cwd"]
        env_vars = odoo_config["env"]
        
        print(f"🐍 Python: {python_cmd}")
        print(f"📄 Script: {script_path}")
        print(f"📁 Working dir: {working_dir}")
        print(f"🔧 Environment: {env_vars}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False
    
    # Test if files exist
    if not os.path.exists(python_cmd):
        print(f"❌ Python executable not found: {python_cmd}")
        return False
    
    if not os.path.exists(script_path):
        print(f"❌ Server script not found: {script_path}")
        return False
    
    if not os.path.exists(working_dir):
        print(f"❌ Working directory not found: {working_dir}")
        return False
    
    print("✅ All paths verified")
    print()
    
    # Test server startup
    print("🚀 Testing MCP server startup...")
    
    try:
        # Prepare environment
        env = os.environ.copy()
        env.update(env_vars)
        
        # Start the server process
        process = subprocess.Popen(
            [python_cmd] + odoo_config["args"],
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it time to start
        time.sleep(3)
        
        # Check if still running
        if process.poll() is None:
            print("✅ MCP server started successfully!")
            print("✅ Server is running and waiting for connections")
            
            # Clean shutdown
            process.terminate()
            process.wait(timeout=5)
            print("✅ Server terminated cleanly")
            
            return True
        else:
            print("❌ MCP server exited immediately")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"Error output: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        return False

def print_setup_instructions():
    """Print setup instructions for ChatGPT Desktop."""
    
    print("\n" + "=" * 60)
    print("📋 ChatGPT Desktop Setup Instructions")
    print("=" * 60)
    
    print("\n1️⃣  Run the setup script:")
    print("   ./setup-chatgpt-desktop.sh")
    
    print("\n2️⃣  Manual configuration (if needed):")
    print("   Copy odoo-mcp-chatgpt-config.json to one of:")
    print("   - ~/.config/chatgpt-desktop/mcp-config.json")
    print("   - ~/Library/Application Support/ChatGPT Desktop/mcp-config.json")
    
    print("\n3️⃣  Restart ChatGPT Desktop")
    
    print("\n4️⃣  Test commands:")
    print("   - 'What MCP tools are available?'")
    print("   - 'Check my Odoo connection'")
    print("   - 'Search for customers in Odoo'")
    
    print("\n🔧 Configuration files created:")
    print("   - odoo-mcp-chatgpt-config.json (Basic MCP config)")
    print("   - odoo-mcp-extension.json (Full extension manifest)")
    print("   - setup-chatgpt-desktop.sh (Automated setup)")

if __name__ == "__main__":
    success = test_chatgpt_desktop_config()
    
    print_setup_instructions()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: Your Odoo MCP server is ready for ChatGPT Desktop!")
        print("   Run './setup-chatgpt-desktop.sh' to complete the setup.")
    else:
        print("💥 FAILED: Please check the error messages above.")
    
    sys.exit(0 if success else 1)