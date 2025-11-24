#!/usr/bin/env python3
"""
Quick test to check if qwen3-vl responds at all (no image, just text)
"""

import requests
import json

print("Testing qwen3-vl model response...")
print("=" * 60)

url = "http://192.168.10.200:11434/api/generate"

payload = {
    "model": "qwen3-vl:32b",
    "prompt": "What is 2+2? Answer in one sentence.",
    "stream": False
}

print("Sending simple text request (no image)...")
print("Timeout: 30 seconds\n")

try:
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    text_response = result.get('response', '')
    
    print("✅ SUCCESS!")
    print("=" * 60)
    print(f"Response: {text_response}")
    print("=" * 60)
    print("\nModel is responding. Issue might be with image processing.")
    
except requests.exceptions.Timeout:
    print("❌ TIMEOUT - Model took more than 30 seconds")
    print("The qwen3-vl:32b model might be too slow or server is overloaded")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
