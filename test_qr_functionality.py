#!/usr/bin/env python3
"""
Test script to verify QR code functionality
"""
import requests
import json
import time
import sys

def test_server_health():
    """Test if the server is running and healthy"""
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def test_qr_generation():
    """Test QR code generation"""
    try:
        # First create a session by uploading a test image
        print("Testing QR code generation...")
        
        # Test the QR debug endpoint
        response = requests.get('http://localhost:8080/qr_debug', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ QR debug endpoint working")
            print(f"   Session ID: {data.get('session_id', 'None')}")
            print(f"   Base URL: {data.get('base_url', 'None')}")
            print(f"   QR URL: {data.get('qr_url', 'None')}")
            return True
        else:
            print(f"❌ QR debug failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ QR generation test failed: {e}")
        return False

def test_mobile_endpoint():
    """Test mobile endpoint"""
    try:
        # Test with a dummy session ID
        test_session_id = "test-session-123"
        response = requests.get(f'http://localhost:8080/mobile/{test_session_id}', timeout=10)
        if response.status_code == 200:
            print("✅ Mobile endpoint working")
            return True
        else:
            print(f"❌ Mobile endpoint failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Mobile endpoint test failed: {e}")
        return False

def test_data_submission():
    """Test data submission endpoint"""
    try:
        test_data = {
            "session_id": "test-session-123",
            "phone_data": {
                "model": "Test Device",
                "manufacturer": "Test Manufacturer",
                "androidVersion": "10",
                "batteryLevel": "50%",
                "screenResolution": "1920x1080",
                "testData": True,
                "timestamp": time.time()
            }
        }
        
        response = requests.post(
            'http://localhost:8080/api/submit_phone_data',
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Data submission working")
            print(f"   Response: {result}")
            return True
        else:
            print(f"❌ Data submission failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Data submission test failed: {e}")
        return False

def main():
    print("🔍 Testing Smart Mobile Doctor QR Code Functionality")
    print("=" * 50)
    
    # Test server health
    if not test_server_health():
        print("\n❌ Server is not running or not accessible")
        print("Please start the server with: python app.py")
        sys.exit(1)
    
    print()
    
    # Test QR generation
    if not test_qr_generation():
        print("\n❌ QR code generation is not working")
        sys.exit(1)
    
    print()
    
    # Test mobile endpoint
    if not test_mobile_endpoint():
        print("\n❌ Mobile endpoint is not working")
        sys.exit(1)
    
    print()
    
    # Test data submission
    if not test_data_submission():
        print("\n❌ Data submission is not working")
        sys.exit(1)
    
    print()
    print("✅ All tests passed! QR code functionality should work properly.")
    print("\n📱 To test with a real device:")
    print("1. Start the server: python app.py")
    print("2. Open http://localhost:8080 in your browser")
    print("3. Upload an image and generate a QR code")
    print("4. Scan the QR code with your phone")
    print("5. The page should load and collect device information")

if __name__ == "__main__":
    main()
