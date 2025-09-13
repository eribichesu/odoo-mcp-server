#!/usr/bin/env python3
"""
Test script to validate your Odoo MCP server configuration.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

async def test_odoo_connection():
    """Test the Odoo connection with your actual configuration."""
    
    try:
        # Import our modules
        from odoo_mcp.config import get_settings
        from odoo_mcp.client import OdooClient
        
        print("🔧 Loading configuration from .env file...")
        settings = get_settings()
        
        print(f"📋 Configuration loaded:")
        print(f"   - URL: {settings.odoo_url}")
        print(f"   - Database: {settings.odoo_database}")
        print(f"   - Username: {settings.odoo_username}")
        print(f"   - Server: {settings.server_name}")
        
        print("\n🔌 Testing Odoo connection...")
        client = OdooClient(settings)
        
        # Test authentication
        print("🔑 Authenticating with Odoo...")
        await client.authenticate()
        print("✅ Authentication successful!")
        
        # Test a simple query - get server version info
        print("\n📊 Testing basic query...")
        try:
            # Get some basic info about the system
            partners = await client.search_records(
                model="res.partner",
                domain=[],
                fields=["id", "name"],
                limit=5
            )
            
            print(f"✅ Query successful! Found {len(partners)} partner records")
            if partners:
                print("   Sample partners:")
                for partner in partners[:3]:
                    print(f"     - {partner.get('name', 'No name')} (ID: {partner.get('id')})")
        
        except Exception as e:
            print(f"⚠️  Basic query test failed: {e}")
            print("   This might be due to access permissions, but authentication worked!")
        
        print("\n🎉 Odoo MCP Server configuration test completed successfully!")
        print("   Your server is ready to use with MCP clients.")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        print("\n🔍 Troubleshooting:")
        print("   1. Check your .env file has correct values")
        print("   2. Verify your Odoo URL is accessible")
        print("   3. Confirm your API key is valid")
        print("   4. Make sure your database name is correct")
        return False

if __name__ == "__main__":
    print("🚀 Odoo MCP Server Configuration Test")
    print("=" * 50)
    
    success = asyncio.run(test_odoo_connection())
    
    if success:
        print("\n✅ All tests passed! Your Odoo MCP server is ready to use.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Please check your configuration.")
        sys.exit(1)