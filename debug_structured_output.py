#!/usr/bin/env python3
"""Debug script to verify structured output format and functionality"""

import json
import time
from github_issues_devin_automation.clients.devin_client import DevinClient

def debug_structured_output():
    client = DevinClient()
    
    print("Creating test session with structured output...")
    prompt = '''Test structured output functionality. Please update the structured output in this exact JSON format:
{
  "confidence": "High",
  "analysis": "This is a simple test to verify structured output works correctly"
}

Please respond with "Confidence: High" and update the structured output immediately.'''
    
    session = client.create_session(prompt)
    session_id = session['session_id']
    
    print(f"Session ID: {session_id}")
    print(f"Session URL: {session['url']}")
    
    print("\nWaiting 30 seconds for Devin to respond...")
    time.sleep(30)
    
    print("\nChecking structured output...")
    session_data = client.get_session(session_id)
    structured_output = session_data.get('structured_output', {})
    
    print(f"Session status: {session_data.get('status_enum', 'unknown')}")
    print(f"Structured output: {json.dumps(structured_output, indent=2)}")
    
    if structured_output:
        print("\n✅ Structured output found!")
        if 'confidence' in structured_output:
            print(f"✅ Confidence field: {structured_output['confidence']}")
        if 'analysis' in structured_output:
            print(f"✅ Analysis field: {structured_output['analysis']}")
    else:
        print("\n❌ No structured output found")
        
    print(f"\nFull session keys: {list(session_data.keys())}")

if __name__ == '__main__':
    debug_structured_output()
