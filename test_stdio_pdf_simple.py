#!/usr/bin/env python3
"""
Simplified test script for MCP stdio mode PDF reading
Tests reading AIBT作业缴交表.pdf through the MCP server
"""

import json
import subprocess
import sys
import os
import time

def test_mcp_stdio_pdf_reading():
    """Test reading PDF file through MCP stdio server"""
    
    # Get absolute path to the PDF file
    pdf_path = os.path.abspath("AIBT作业缴交表.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing PDF file: {pdf_path}")
    
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
        
        # Give the server time to start
        time.sleep(1)
        
        # Send initialization request
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
        
        print("🔄 Sending initialization request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Wait for initialization response
        init_response = process.stdout.readline()
        if init_response:
            init_data = json.loads(init_response.strip())
            if "result" in init_data:
                print("✅ Server initialized successfully")
            else:
                print(f"❌ Initialization failed: {init_data}")
                return False
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        print("🔄 Sending initialized notification...")
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Send read request
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
        
        print("🔄 Sending PDF read request...")
        process.stdin.write(json.dumps(read_request) + "\n")
        process.stdin.flush()
        
        # Close stdin to signal end of input
        process.stdin.close()
        
        # Wait for response with timeout
        try:
            stdout, stderr = process.communicate(timeout=30)
            
            if stderr:
                print(f"⚠️  Server stderr: {stderr}")
            
            # Parse all responses
            if stdout:
                print(f"📤 Raw stdout: {stdout}")
                lines = stdout.strip().split('\n')
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        response = json.loads(line)
                        if response.get("id") == 2:  # This is our read response
                            if "result" in response:
                                result = response["result"]
                                if "content" in result and isinstance(result["content"], list):
                                    content = result["content"]
                                    if len(content) > 0 and "text" in content[0]:
                                        text_content = content[0]["text"]
                                        print(f"✅ Successfully read PDF content ({len(text_content)} characters)")
                                        print(f"📋 Content preview: {text_content[:200]}...")
                                        return True
                                elif isinstance(result, str):
                                    print(f"✅ Successfully read PDF content ({len(result)} characters)")
                                    print(f"📋 Content preview: {result[:200]}...")
                                    return True
                                print(f"❌ Unexpected result format: {result}")
                                return False
                            elif "error" in response:
                                print(f"❌ MCP Error: {response['error']}")
                                return False
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Failed to parse JSON line: {line[:100]}... Error: {e}")
                        continue
            
            print("❌ No valid read response received")
            return False
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("❌ Request timeout")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting MCP stdio PDF reading test (simplified)...")
    success = test_mcp_stdio_pdf_reading()
    
    if success:
        print("🎉 Test passed - MCP server can read PDF files via stdio mode!")
        sys.exit(0)
    else:
        print("💥 Test failed - Check server logs for details")
        sys.exit(1)