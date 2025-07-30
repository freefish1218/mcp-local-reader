#!/usr/bin/env python3
"""
Test error handling for content length validation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.file_reader import FileReader, LocalReadRequest, LocalFileStorageClient

async def test_content_length_validation():
    """Test that short content returns error message instead of exception"""
    
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
        
        # Create file reader with min_content_length=10
        file_reader = FileReader(
            storage_client=local_storage_client,
            max_workers=5,
            min_content_length=10  # Set to 10 to trigger error
        )
        
        # Create read request
        request = LocalReadRequest(
            file_paths=[pdf_path],
            allow_absolute_paths=True,
            max_size=20 * 1024 * 1024  # 20MB
        )
        
        # Read file
        print("🔄 Reading PDF file with min_content_length=10...")
        response = await file_reader.read_files(request)
        
        # Check results - we expect this to fail due to short content
        if response.failed and len(response.failed) > 0:
            failed_file = response.failed[0]
            error_message = failed_file.error_message
            print(f"✅ Correctly returned error: {failed_file.type.value} - {error_message}")
            if "提取的内容过短" in error_message:
                print("✅ Error message contains expected content")
                return True
            else:
                print(f"❌ Unexpected error message: {error_message}")
                return False
        elif response.contents and len(response.contents) > 0:
            print("❌ Expected error but got content")
            return False
        else:
            print("❌ No content or error returned")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected exception (should return error message instead): {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_valid_content_length():
    """Test with lower min_content_length to ensure content is returned"""
    
    pdf_path = os.path.abspath("AIBT作业缴交表.pdf")
    
    print(f"📄 Testing PDF file with lower threshold: {pdf_path}")
    
    try:
        # Create storage client
        local_storage_client = LocalFileStorageClient(
            allowed_directories=["/Users/ben"],
            allow_absolute_paths=True
        )
        
        # Create file reader with min_content_length=1
        file_reader = FileReader(
            storage_client=local_storage_client,
            max_workers=5,
            min_content_length=1  # Set to 1 to allow short content
        )
        
        # Create read request
        request = LocalReadRequest(
            file_paths=[pdf_path],
            allow_absolute_paths=True,
            max_size=20 * 1024 * 1024  # 20MB
        )
        
        # Read file
        print("🔄 Reading PDF file with min_content_length=1...")
        response = await file_reader.read_files(request)
        
        # Check results - we expect this to succeed
        if response.contents and len(response.contents) > 0:
            content = response.contents[0].content
            print(f"✅ Successfully read content ({len(content)} characters)")
            print(f"📋 Content: {repr(content)}")
            return True
        elif response.failed and len(response.failed) > 0:
            failed_file = response.failed[0]
            print(f"❌ Unexpected failure: {failed_file.type.value} - {failed_file.error_message}")
            return False
        else:
            print("❌ No content or error returned")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 Starting content length validation tests...")
    
    # Clear cache first
    import shutil
    if os.path.exists("cache"):
        shutil.rmtree("cache")
    
    print("\n" + "="*50)
    print("Test 1: Content too short (min_content_length=10)")
    print("="*50)
    test1_passed = await test_content_length_validation()
    
    print("\n" + "="*50)
    print("Test 2: Content acceptable (min_content_length=1)")
    print("="*50)
    test2_passed = await test_valid_content_length()
    
    print("\n" + "="*50)
    print("Summary")
    print("="*50)
    
    if test1_passed and test2_passed:
        print("🎉 All tests passed!")
        print("✅ Error handling works correctly")
        print("✅ Content length validation works as expected")
        return True
    else:
        print("💥 Some tests failed")
        print(f"❌ Test 1 (error handling): {'PASS' if test1_passed else 'FAIL'}")
        print(f"❌ Test 2 (valid content): {'PASS' if test2_passed else 'FAIL'}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)