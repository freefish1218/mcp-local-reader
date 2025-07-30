#!/usr/bin/env python3
"""
Test script for MCP stdio mode PDF reading
Tests reading AIBT作业缴交表.pdf through the MCP server
"""

import json
import subprocess
import sys
import os
from pathlib import Path

def test_mcp_stdio_pdf_reading():
    """Test reading PDF file through MCP stdio server"""
    
    # Get absolute path to the PDF file
    pdf_path = os.path.abspath("作业缴交表.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing PDF file: {pdf_path}")
    
    # MCP initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    # MCP initialized notification
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    
    # MCP request to read the PDF file
    read_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "read_local_file",
            "arguments": {
                "file_path": pdf_path,
                "max_size": 20
            }
        }
    }
    
    try:
        # Start the MCP stdio server
        process = subprocess.Popen(
            [sys.executable, "src/mcp_stdio_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Send initialization request, notification, then the read request
        init_json = json.dumps(init_request) + "\n"
        initialized_json = json.dumps(initialized_notification) + "\n"
        read_json = json.dumps(read_request) + "\n"
        requests = init_json + initialized_json + read_json
        print("🔄 Sending MCP initialization, notification and read requests...")
        
        stdout, stderr = process.communicate(input=requests, timeout=60)
        
        if stderr:
            print(f"⚠️  Server errors: {stderr}")
        
        # Parse response
        if stdout.strip():
            print(f"📤 Raw stdout: {stdout}")
            lines = stdout.strip().split('\n')
            for line in lines:
                try:
                    response = json.loads(line)
                    print(f"📋 Parsed response: {response}")
                    
                    # Handle the read request response (id=2)
                    if response.get("id") == 2:
                        if "result" in response:
                            result = response["result"]
                            if isinstance(result, str):
                                print(f"✅ Successfully read PDF content ({len(result)} characters)")
                                print(f"📋 Content preview: {result[:200]}...")
                                return True
                            elif "content" in result:
                                content = result["content"]
                                if isinstance(content, list) and len(content) > 0:
                                    text_content = content[0].get("text", "")
                                    print(f"✅ Successfully read PDF content ({len(text_content)} characters)")
                                    print(f"📋 Content preview: {text_content[:200]}...")
                                    return True
                            print(f"❌ Unexpected result format: {result}")
                            return False
                        elif "error" in response:
                            print(f"❌ MCP Error: {response['error']}")
                            return False
                except json.JSONDecodeError:
                    continue
        
        print("❌ No valid response received")
        return False
        
    except subprocess.TimeoutExpired:
        process.kill()
        print("❌ Request timeout")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting MCP stdio PDF reading test...")
    success = test_mcp_stdio_pdf_reading()
    
    if success:
        print("🎉 Test passed - MCP server can read PDF files via stdio mode!")
        sys.exit(0)
    else:
        print("💥 Test failed - Check server logs for details")
        sys.exit(1)