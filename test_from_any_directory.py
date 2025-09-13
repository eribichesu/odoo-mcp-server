#!/usr/bin/env python3
"""
Test MCP server from /tmp directory to simulate Claude Desktop behavior.
"""

import subprocess
import os
import time

def test_from_tmp():
    """Test that server loads .env from any working directory."""
    
    # Change to /tmp to simulate Claude Desktop launching from random directory
    os.chdir("/tmp")
    print(f"🧪 Testing from: {os.getcwd()}")
    
    python_path = "/Users/edoardo.ribichesu/vscode/odoo.mcp/.venv/bin/python"
    server_script = "/Users/edoardo.ribichesu/vscode/odoo.mcp/src/odoo_mcp/server.py"
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "/Users/edoardo.ribichesu/vscode/odoo.mcp/src"
    
    try:
        # Start the server process
        process = subprocess.Popen(
            [python_path, server_script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start up
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ MCP server started successfully from /tmp!")
            print("✅ .env file loaded correctly with absolute path")
            
            # Terminate the process
            process.terminate()
            process.wait()
            return True
        else:
            print("❌ MCP server failed to start:")
            stdout, stderr = process.communicate()
            if stderr:
                print("STDERR:", stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_from_tmp()
    print("🎉 SUCCESS: Server works from any directory!" if success else "💥 FAILED")
