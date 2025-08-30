#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat API Stream Test Script

This script tests the streaming chat API endpoint to verify the complete RAG workflow.
It sends a test query and validates the streaming response.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any


class ChatAPITester:
    """Chat API testing utility"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health_check(self) -> bool:
        """Test if the API server is running"""
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    print("✅ API server is running")
                    return True
                else:
                    print(f"❌ API server health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Failed to connect to API server: {e}")
            return False
    

    
    async def create_session(self) -> str:
        """Create a new session and return session_id"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/sessions",
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    session_id = data.get("session_id")
                    print(f"✅ Session created: {session_id}")
                    return session_id
                else:
                    error_text = await response.text()
                    print(f"❌ Session creation failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return None
    
    async def test_stream_endpoint(self, query: str, session_id: str) -> Dict[str, Any]:
        """Test the streaming chat endpoint"""
        url = f"{self.base_url}/api/v1/chat/stream"
        payload = {
            "query": query,
            "session_id": session_id,
            "stream": True
        }
        
        print(f"\n🌊 Testing streaming query: '{query}'")
        print(f"📡 Sending streaming request to: {url}")
        
        start_time = time.time()
        chunks = []
        
        try:
            async with self.session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"📊 Status code: {response.status}")
                
                if response.status == 200:
                    print("🔄 Receiving streaming response...")
                    
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith('data: '):
                                chunk_data = line_str[6:]  # Remove 'data: ' prefix
                                if chunk_data != '[DONE]':
                                    try:
                                        chunk_json = json.loads(chunk_data)
                                        chunks.append(chunk_json)
                                        content = chunk_json.get('content', '')
                                        print(f"📝 Chunk: {content[:50]}...")
                                        print(f"🔍 Full chunk data: {chunk_json}")
                                    except json.JSONDecodeError:
                                        continue
                    
                    response_time = time.time() - start_time
                    print(f"✅ Streaming completed in {response_time:.2f}s")
                    print(f"📊 Total chunks received: {len(chunks)}")
                    
                    return {
                        "success": True,
                        "status_code": response.status,
                        "response_time": response_time,
                        "chunks": chunks,
                        "total_chunks": len(chunks)
                    }
                else:
                    error_text = await response.text()
                    response_time = time.time() - start_time
                    print(f"❌ Streaming request failed: {error_text}")
                    return {
                        "success": False,
                        "status_code": response.status,
                        "response_time": response_time,
                        "error": error_text
                    }
        
        except Exception as e:
            response_time = time.time() - start_time
            print(f"❌ Streaming request exception: {e}")
            return {
                "success": False,
                "status_code": None,
                "response_time": response_time,
                "error": str(e)
            }
    

    
    def print_summary(self, results: Dict[str, Any]):
        """Print test summary"""
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result.get("success") else "❌ FAILED"
            response_time = result.get("response_time", 0)
            print(f"{test_name}: {status} ({response_time:.2f}s)")
            
            if not result.get("success") and "error" in result:
                print(f"  Error: {result['error']}")
        
        print("="*60)


async def main():
    """Main test function"""
    print("🚀 Starting Chat API Stream Test")
    print("="*60)
    
    test_query = "淀粉人是什么？"
    results = {}
    
    async with ChatAPITester() as tester:
        
        # Test 1: Create session
        print("\n2️⃣  Creating session...")
        session_id = await tester.create_session()
        if not session_id:
            print("❌ Failed to create session. Cannot proceed with streaming test.")
            return
        results["Session Creation"] = {"success": True, "session_id": session_id}
        
        # Test 2: Streaming chat endpoint
        print("\n3️⃣  Testing streaming chat endpoint...")
        stream_result = await tester.test_stream_endpoint(test_query, session_id)
        results["Streaming Chat"] = stream_result
        
        # Print summary
        tester.print_summary(results)
        
        # Print detailed streaming response if available
        if stream_result.get("success") and "chunks" in stream_result:
            print("\n📄 DETAILED STREAMING RESPONSE:")
            print("-" * 60)
            chunks = stream_result["chunks"]
            print(f"Query: {test_query}")
            print(f"Total chunks: {len(chunks)}")
            
            # Combine all content from chunks
            full_response = ""
            status_messages = []
            
            for i, chunk in enumerate(chunks):
                chunk_type = chunk.get('type', '')
                if chunk_type == 'status':
                    message = chunk.get('message', '')
                    status_messages.append(message)
                    print(f"Status {i+1}: {message}")
                elif chunk_type == 'result':
                    response = chunk.get('response', '')
                    if response:
                        full_response += response
                        print(f"Response {i+1}: {response[:100]}{'...' if len(response) > 100 else ''}")
                elif chunk_type == 'end':
                    print(f"End signal received")
                else:
                    # Fallback for other content structures
                    content = chunk.get('content', '')
                    if content:
                        full_response += content
                        print(f"Content {i+1}: {content[:100]}{'...' if len(content) > 100 else ''}")
            
            print(f"\n📝 Status Messages: {'; '.join(status_messages)}")
            print(f"📝 Full Response: {full_response}")
            print(f"📊 Response length: {len(full_response)} characters")
            print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())