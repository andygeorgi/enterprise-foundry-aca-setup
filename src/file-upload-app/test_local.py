#!/usr/bin/env python3
"""
Local testing script for file upload app with Document Intelligence
This script helps test the app locally without deploying to Azure
"""

import requests
import json
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8080"

def test_health():
    """Test the health endpoint"""
    print("\n🏥 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_upload(file_path):
    """Test file upload"""
    print(f"\n📤 Uploading file: {file_path}")
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'rb') as f:
        files = {'files': f}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # If upload was successful and analysis is available, retrieve it
    if result.get('success') and result.get('results'):
        for file_result in result['results']:
            if file_result.get('processed') and file_result.get('json_file'):
                print(f"\n📊 Retrieving analysis: {file_result['json_file']}")
                analysis_response = requests.get(f"{BASE_URL}/analysis/{file_result['json_file']}")
                if analysis_response.status_code == 200:
                    analysis = analysis_response.json()
                    print(f"  ✅ Analysis retrieved:")
                    print(f"     - Pages: {len(analysis.get('pages', []))}")
                    print(f"     - Tables: {len(analysis.get('tables', []))}")
                    print(f"     - Key-Value Pairs: {len(analysis.get('key_value_pairs', []))}")
                    print(f"     - Content length: {len(analysis.get('content', ''))} characters")
    
    return response.status_code == 200

def test_list_files():
    """Test file listing"""
    print("\n📋 Listing all files...")
    response = requests.get(f"{BASE_URL}/files")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Total files: {result.get('count', 0)}")
    
    if result.get('files'):
        for file in result['files'][:5]:  # Show first 5
            print(f"  - {file['filename']} ({file['size']} bytes)")
            if file.get('has_analysis'):
                print(f"    ✅ Analysis available: {file['analysis_url']}")
    
    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 60)
    print("File Upload App - Local Testing")
    print("=" * 60)
    print(f"Target URL: {BASE_URL}")
    print("\nMake sure the app is running: python app.py")
    print("=" * 60)
    
    # Test health
    if not test_health():
        print("\n❌ Health check failed. Is the app running?")
        sys.exit(1)
    
    # Test upload if file provided
    if len(sys.argv) > 1:
        for file_path in sys.argv[1:]:
            test_upload(file_path)
    else:
        print("\n💡 Usage: python test_local.py <file1> [file2] ...")
        print("   Example: python test_local.py sample.pdf sample.png")
    
    # Test file listing
    test_list_files()
    
    print("\n" + "=" * 60)
    print("✅ Testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
