import pytesseract
from PIL import Image
import re
import os

# Set Tesseract executable path - update this to your actual installation path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Verify this path

# Function to extract phone information from image using OCR
def extract_phone_info(image_path):
    # Open the image
    img = Image.open(image_path)
    
    # Perform OCR on the image
    text = pytesseract.image_to_string(img)
    
    # Initialize dictionary to store extracted information
    phone_info = {
        'model': 'Unknown',
        'ram': 'Unknown',
        'os_version': 'Unknown',
        'storage': 'Unknown',
        'processor': 'Unknown',
        'battery': 'Unknown'
    }
    
    # Extract model name (look for common patterns)
    model_patterns = [
        r'Model[:\s]*(\w+\s*\w*\s*\d*\s*\w*)',
        r'Device[:\s]*(\w+\s*\w*\s*\d*\s*\w*)',
        r'(Galaxy\s*\w+\s*\d*)',
        r'(iPhone\s*\d+\s*\w*)',
        r'(Redmi\s*\w+\s*\d*)',
        r'(Mi\s*\w+\s*\d*)',
        r'(Pixel\s*\d+\s*\w*)',
        r'(OnePlus\s*\w+\s*\d*)'
    ]
    
    for pattern in model_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            phone_info['model'] = match.group(1).strip()
            break
    
    # Extract RAM
    ram_pattern = r'(\d+)\s*GB\s*RAM'
    ram_match = re.search(ram_pattern, text, re.IGNORECASE)
    if ram_match:
        phone_info['ram'] = f"{ram_match.group(1)}GB"
    
    # Extract OS version
    android_pattern = r'Android\s*(\d+(?:\.\d+)*)'  # Android version pattern
    ios_pattern = r'iOS\s*(\d+(?:\.\d+)*)'  # iOS version pattern
    
    android_match = re.search(android_pattern, text, re.IGNORECASE)
    ios_match = re.search(ios_pattern, text, re.IGNORECASE)
    
    if android_match:
        phone_info['os_version'] = f"Android {android_match.group(1)}"
    elif ios_match:
        phone_info['os_version'] = f"iOS {ios_match.group(1)}"
    
    # Extract storage
    storage_pattern = r'(\d+)\s*GB\s*(?:storage|memory)'
    storage_match = re.search(storage_pattern, text, re.IGNORECASE)
    if storage_match:
        phone_info['storage'] = f"{storage_match.group(1)}GB"
    
    # Extract processor information
    processor_patterns = [
        r'Processor[:\s]*(\w+\s*\w*\s*\d*\s*\w*)',
        r'CPU[:\s]*(\w+\s*\w*\s*\d*\s*\w*)',
        r'Snapdragon\s*(\d+)',
        r'Exynos\s*(\d+)',
        r'A(\d+)\s*Bionic'
    ]
    
    for pattern in processor_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if 'Snapdragon' in pattern:
                phone_info['processor'] = f"Snapdragon {match.group(1)}"
            elif 'Exynos' in pattern:
                phone_info['processor'] = f"Exynos {match.group(1)}"
            elif 'Bionic' in pattern:
                phone_info['processor'] = f"A{match.group(1)} Bionic"
            else:
                phone_info['processor'] = match.group(1).strip()
            break
    
    # Extract battery information
    battery_pattern = r'(\d+)\s*mAh'
    battery_match = re.search(battery_pattern, text, re.IGNORECASE)
    if battery_match:
        phone_info['battery'] = f"{battery_match.group(1)}mAh"
    
    return phone_info