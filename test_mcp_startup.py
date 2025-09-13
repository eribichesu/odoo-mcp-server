#!/usr/bin/env python3
"""
Quick test to verify MCP server starts without errors.
This simulates what Claude Desktop does when starting the server.
"""

import subprocess
import sys
import os
import signal
import time

def test_mcp_server():
    """Test that the MCP server starts without immediate errors."""
    
    print("🧪 Testing Odoo MCP Server Startup...")
    print("=" * 50)
    
    # Change to project directory
    project_dir = "/Users/edoardo.ribichesu/vscode/odoo.mcp"
    os.chdir(project_dir)
    
    # Use the same command that Claude Desktop uses
    python_path = "/Users/edoardo.ribichesu/vscode/odoo.mcp/.venv/bin/python"
    server_script = "/Users/edoardo.ribichesu/vscode/odoo.mcp/src/odoo_mcp/server.py"
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "/Users/edoardo.ribichesu/vscode/odoo.mcp/src"
    
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python: {python_path}")
    print(f"📄 Server script: {server_script}")
    print(f"🔧 PYTHONPATH: {env.get('PYTHONPATH')}")
    print()
    
    try:
        # Start the server process
        print("🚀 Starting MCP server...")
        process = subprocess.Popen(
            [python_path, server_script],
            cwd=project_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start up and check for immediate errors
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ MCP server started successfully!")
            print("✅ No immediate startup errors detected")
            print("✅ Server is running and waiting for MCP client connections")
            
            # Terminate the process
            process.terminate()
            process.wait()
            print("✅ Server terminated cleanly")
            
            return True
        else:
            print("❌ MCP server exited immediately with errors:")
            stdout, stderr = process.communicate()
            if stdout:
                print("STDOUT:", stdout)
            if stderr:
                print("STDERR:", stderr)
            return False
            
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        return False

if __name__ == "__main__":
    success = test_mcp_server()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 MCP Server Test: PASSED")
        print("   Your server is ready for Claude Desktop!")
        print("   Restart Claude Desktop and test the connection.")
    else:
        print("💥 MCP Server Test: FAILED")
        print("   Check the error messages above.")
        
    sys.exit(0 if success else 1)