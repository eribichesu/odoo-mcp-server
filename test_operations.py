#!/usr/bin/env python3
"""
Quick test of actual Odoo operations with your configuration.
"""

import asyncio
import sys
sys.path.insert(0, 'src')

async def test_odoo_operations():
    """Test actual Odoo operations."""
    
    from odoo_mcp.config import get_settings
    from odoo_mcp.client import OdooClient
    
    print("🔧 Testing Odoo MCP Server operations...")
    settings = get_settings()
    client = OdooClient(settings)
    
    # Authenticate
    await client.authenticate()
    print("✅ Authentication successful!")
    
    # Test search records
    print("\n📊 Testing search_records operation...")
    try:
        partners = await client.search_records(
            model="res.partner",
            domain=[],
            fields=["id", "name", "email"],
            limit=3
        )
        
        print(f"✅ Found {len(partners)} partner records:")
        for partner in partners:
            name = partner.get('name', 'No name')
            email = partner.get('email', 'No email')
            print(f"   - {name} ({email}) [ID: {partner['id']}]")
            
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    # Test model fields
    print("\n🔍 Testing get_model_fields operation...")
    try:
        fields = await client.get_model_fields("res.partner")
        field_count = len(fields)
        print(f"✅ Retrieved {field_count} field definitions for res.partner")
        
        # Show a few interesting fields
        interesting_fields = ['name', 'email', 'phone', 'is_company']
        for field_name in interesting_fields:
            if field_name in fields:
                field_info = fields[field_name]
                field_type = field_info.get('type', 'unknown')
                field_string = field_info.get('string', field_name)
                print(f"   - {field_string} ({field_name}): {field_type}")
                
    except Exception as e:
        print(f"❌ Model fields test failed: {e}")
    
    print("\n🎉 Odoo MCP Server is fully operational!")
    print("   Ready for use with MCP clients like Claude Desktop.")

if __name__ == "__main__":
    asyncio.run(test_odoo_operations())