#!/usr/bin/env python3
"""
Manual test by running server and client separately
Just test the MCP call_tool function directly
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.mcp_stdio_server import call_tool

async def test_mcp_call_tool():
    """Test the MCP call_tool function directly"""
    
    pdf_path = os.path.abspath("AIBT作业缴交表.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing PDF file: {pdf_path}")
    
    try:
        # Call the tool function directly
        arguments = {
            "file_path": pdf_path,
            "max_size": 20
        }
        
        print("🔄 Calling MCP tool function directly...")
        result = await call_tool("read_local_file", arguments)
        
        if result and len(result) > 0:
            text_content = result[0].text
            print(f"✅ Successfully read PDF content ({len(text_content)} characters)")
            print(f"📋 Content preview: {text_content[:200]}...")
            return True
        else:
            print("❌ No content returned")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting MCP tool function test...")
    success = asyncio.run(test_mcp_call_tool())
    
    if success:
        print("🎉 Test passed - MCP tool function works!")
        sys.exit(0)
    else:
        print("💥 Test failed")
        sys.exit(1)