#!/usr/bin/env python
"""Debug Python file parsing"""

import asyncio
from pathlib import Path
from src.file_reader import FileReader, LocalReadRequest

async def test_debug():
    """Debug Python file parsing"""
    reader = FileReader()
    
    # Create a test Python file
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    
    py_file = test_dir / "test.py"
    py_file.write_text('''def hello_world():
    """Print hello world"""
    print("Hello, World!")
''')
    
    print(f"📁 Test file: {py_file.absolute()}")
    print(f"📄 File exists: {py_file.exists()}")
    print(f"📏 File size: {py_file.stat().st_size} bytes")
    
    # Check mapping
    print(f"📚 .py in reader.file_type_mapping: {'.py' in reader.file_type_mapping}")
    if '.py' in reader.file_type_mapping:
        print(f"   Maps to: {reader.file_type_mapping['.py']}")
    
    # Try to parse
    request = LocalReadRequest(file_paths=[str(py_file.absolute())])
    print(f"\n🔍 Request file_paths: {request.file_paths}")
    
    response = await reader.read_file(request)
    
    print(f"\n📊 Results:")
    print(f"  Successful: {len(response.contents)}")
    print(f"  Failed: {len(response.failed)}")
    
    if response.contents:
        for content in response.contents:
            print(f"\n✅ Success:")
            print(f"  Resource ID: {content.resource_id}")
            print(f"  Content length: {len(content.content)}")
            print(f"  Preview: {content.content[:50]}...")
    
    if response.failed:
        for failure in response.failed:
            print(f"\n❌ Failure:")
            print(f"  Resource ID: {failure.resource_id}")
            print(f"  Type: {failure.type}")
            print(f"  Error: {failure.error_message}")
    
    # Clean up
    import shutil
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    asyncio.run(test_debug())