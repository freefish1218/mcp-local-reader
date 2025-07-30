#!/usr/bin/env python3
"""
Direct test using the MCP client library
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.file_reader import FileReader, LocalReadRequest, LocalFileStorageClient

async def test_direct_pdf_reading():
    """Test PDF reading directly without MCP layer"""
    
    pdf_path = os.path.abspath("AIBT作业缴交表.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing PDF file: {pdf_path}")
    
    try:
        # Create storage client
        local_storage_client = LocalFileStorageClient(
            allowed_directories=["/Users/ben"],
            allow_absolute_paths=True
        )
        
        # Create file reader
        file_reader = FileReader(
            storage_client=local_storage_client,
            max_workers=5,
            min_content_length=1  # Allow short content
        )
        
        # Create read request
        request = LocalReadRequest(
            file_paths=[pdf_path],
            allow_absolute_paths=True,
            max_size=20 * 1024 * 1024  # 20MB
        )
        
        # Read file
        print("🔄 Reading PDF file directly...")
        response = await file_reader.read_files(request)
        
        # Check results
        if response.contents and len(response.contents) > 0:
            content = response.contents[0].content
            print(f"✅ Successfully read PDF content ({len(content)} characters)")
            print(f"📋 Content preview: {content[:200]}...")
            return True
        elif response.failed and len(response.failed) > 0:
            failed_file = response.failed[0]
            print(f"❌ Read failed: {failed_file.type.value} - {failed_file.error_message}")
            return False
        else:
            print("❌ No content or error returned")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting direct PDF reading test...")
    success = asyncio.run(test_direct_pdf_reading())
    
    if success:
        print("🎉 Test passed - Direct PDF reading works!")
        sys.exit(0)
    else:
        print("💥 Test failed")
        sys.exit(1)