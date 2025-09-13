#!/usr/bin/env python3
"""
Test Odoo client connection and authentication directly.
"""

import asyncio
import sys
sys.path.insert(0, 'src')

async def test_odoo_connection():
    """Test Odoo client connection, authentication, and basic operations."""
    
    from odoo_mcp.config import get_settings
    from odoo_mcp.client import OdooClient
    
    print("🧪 Testing Odoo Client Connection")
    print("=" * 50)
    
    settings = get_settings()
    client = OdooClient(settings)
    
    print(f"🌐 URL: {client.url}")
    print(f"🗄️  Database: {client.database}")
    print(f"👤 Username: {client.username}")
    print()
    
    # Test connection check
    print("1️⃣  Testing connection check...")
    try:
        connection_info = await client.check_connection()
        print(f"✅ Connection info: {connection_info}")
    except Exception as e:
        print(f"❌ Connection check failed: {e}")
        return False
    
    # Test authentication
    print("\n2️⃣  Testing authentication...")
    try:
        uid = await client.authenticate()
        print(f"✅ Authenticated with UID: {uid}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    
    # Test search
    print("\n3️⃣  Testing search records...")
    try:
        records = await client.search_records(
            model="res.partner",
            domain=[["is_company", "=", True]],
            fields=["id", "name", "email"],
            limit=2
        )
        print(f"✅ Found {len(records)} records:")
        for record in records:
            print(f"   - {record.get('name', 'No name')} (ID: {record.get('id')})")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All Odoo Client Tests Passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_odoo_connection())
    sys.exit(0 if success else 1)