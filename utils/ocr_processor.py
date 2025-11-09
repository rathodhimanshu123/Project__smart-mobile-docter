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
    
    # Extract RAM (handle formats like "8 GB RAM" and "RAM 8.00 GB")
    ram_patterns = [
        r'RAM\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*GB',
        r'(\d+(?:\.\d+)?)\s*GB\s*RAM'
    ]
    for pattern in ram_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            # Normalize 8.00 -> 8
            if value.endswith('.00'):
                value = value[:-3]
            phone_info['ram'] = f"{value}GB"
            break
    
    # Extract OS version (handle 'Android 14' and 'Android version 14', also capture Realme UI)
    android_patterns = [
        r'Android\s*(?:version\s*)?(\d+(?:\.\d+)*)',
        r'Android\s*OS\s*(\d+(?:\.\d+)*)'
    ]
    ios_pattern = r'iOS\s*(\d+(?:\.\d+)*)'
    realme_ui_pattern = r'realme\s*UI\s*(\d+(?:\.\d+)*)'

    android_match = None
    for pattern in android_patterns:
        android_match = re.search(pattern, text, re.IGNORECASE)
        if android_match:
            break
    ios_match = re.search(ios_pattern, text, re.IGNORECASE)
    realme_match = re.search(realme_ui_pattern, text, re.IGNORECASE)

    if android_match:
        phone_info['os_version'] = f"Android {android_match.group(1)}"
    elif ios_match:
        phone_info['os_version'] = f"iOS {ios_match.group(1)}"
    elif realme_match:
        phone_info['os_version'] = f"realme UI {realme_match.group(1)}"
    
    # Extract storage (support '124 GB / 128 GB', take total as capacity)
    storage_patterns = [
        r'Storage\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*GB\s*/\s*(\d+(?:\.\d+)?)\s*GB',
        r'(\d+(?:\.\d+)?)\s*GB\s*/\s*(\d+(?:\.\d+)?)\s*GB',
        r'Storage\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*GB',
        r'(\d+(?:\.\d+)?)\s*GB\s*(?:storage|memory|ROM)'
    ]
    for pattern in storage_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.lastindex and match.lastindex >= 2:
                # pattern with used/total; choose total (group 2)
                total = match.group(2)
                if total.endswith('.00'):
                    total = total[:-3]
                phone_info['storage'] = f"{total}GB"
            else:
                value = match.group(1)
                if value.endswith('.00'):
                    value = value[:-3]
                phone_info['storage'] = f"{value}GB"
            break
    
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