#!/usr/bin/env python
"""Test MCP server with real files"""

import asyncio
import os
from pathlib import Path
from src.file_reader import FileReader, LocalReadRequest

async def test_real_files():
    """Test parsing various real file types"""
    reader = FileReader()
    
    # Create test files
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    
    # Create a text file
    text_file = test_dir / "test.txt"
    text_file.write_text("This is a test text file.\nIt has multiple lines.\n")
    
    # Create a JSON file
    json_file = test_dir / "test.json"
    json_file.write_text('{"name": "test", "value": 123, "nested": {"key": "value"}}')
    
    # Create a Python file
    py_file = test_dir / "test.py"
    py_file.write_text('''def hello_world():
    """Print hello world"""
    print("Hello, World!")
    
if __name__ == "__main__":
    hello_world()
''')
    
    # Create an RTF file
    rtf_file = test_dir / "test.rtf"
    rtf_file.write_text(r'{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}} \f0\fs24 This is RTF text.\par}')
    
    # Create a Markdown file
    md_file = test_dir / "test.md"
    md_file.write_text("""# Test Markdown

This is a test markdown file.

## Features
- Bullet point 1
- Bullet point 2

```python
def test():
    return "test"
```
""")
    
    # Test all files
    test_files = [
        str(text_file.absolute()),
        str(json_file.absolute()),
        str(py_file.absolute()),
        str(rtf_file.absolute()),
        str(md_file.absolute())
    ]
    
    print("🧪 Testing real file parsing...")
    print(f"📁 Test directory: {test_dir.absolute()}")
    print()
    
    request = LocalReadRequest(file_paths=test_files)
    response = await reader.read_file(request)
    
    # Check results
    for file_path in test_files:
        filename = Path(file_path).name
        print(f"📄 {filename}:")
        
        # Find the result for this file
        content_found = False
        error_found = False
        
        for content in response.contents:
            if content.resource_id == file_path:
                content_found = True
                print(f"  ✅ Successfully parsed")
                print(f"  📊 Content length: {len(content.content)} chars")
                # Show first 100 chars
                preview = content.content[:100].replace('\n', ' ')
                if len(content.content) > 100:
                    preview += "..."
                print(f"  📖 Preview: {preview}")
                break
        
        for failure in response.failed:
            if failure.resource_id == file_path:
                error_found = True
                print(f"  ❌ Failed: {failure.error_message}")
                break
        
        if not content_found and not error_found:
            print(f"  ⚠️  No result found")
        
        print()
    
    # Summary
    print("📊 Summary:")
    print(f"  ✅ Successful: {len(response.contents)}/{len(test_files)}")
    print(f"  ❌ Failed: {len(response.failed)}/{len(test_files)}")
    
    # Clean up
    import shutil
    shutil.rmtree(test_dir)
    print("\n🧹 Cleaned up test files")
    
    return len(response.contents) == len(test_files)

if __name__ == "__main__":
    success = asyncio.run(test_real_files())
    exit(0 if success else 1)