#!/usr/bin/env python3
"""
Test if gemma3:27b supports vision input
"""

import requests
import json
import base64
from PIL import Image
import io

print("Testing if gemma3:27b supports vision...")
print("=" * 60)

# Create a simple test image (red square with text)
img = Image.new('RGB', (200, 200), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
test_image_bytes = img_bytes.getvalue()

# Encode to base64
image_b64 = base64.b64encode(test_image_bytes).decode('utf-8')

url = "http://192.168.10.200:11434/api/generate"

payload = {
    "model": "gemma3:27b",
    "prompt": "What color is this image? Answer in one word.",
    "images": [image_b64],
    "stream": False
}

print(f"Sending vision request to gemma3:27b...")
print(f"Image size: {len(test_image_bytes)} bytes")
print(f"Timeout: 30 seconds\n")

try:
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    text_response = result.get('response', '')
    
    print("✅ SUCCESS! gemma3:27b SUPPORTS VISION!")
    print("=" * 60)
    print(f"Response: {text_response}")
    print("=" * 60)
    print("\n🎉 We can use gemma3:27b for vision extraction!")
    print("This will be much faster than qwen3-vl:32b")
    
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print("❌ gemma3:27b does NOT support vision")
        print(f"Error: {e.response.text}")
    else:
        print(f"❌ HTTP Error: {e}")
        
except requests.exceptions.Timeout:
    print("⏳ Request timed out after 30 seconds")
    print("Model might support vision but is too slow")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
