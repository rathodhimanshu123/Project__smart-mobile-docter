import pytesseract
from PIL import Image
import re
import os

# Set Tesseract executable path - update this to your actual installation path
# Try to auto-detect common paths
_tesseract_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    '/usr/bin/tesseract',
    '/usr/local/bin/tesseract'
]

for path in _tesseract_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break

def _normalize_units(value_str, unit_type='GB'):
    """Normalize numeric values and remove trailing .00"""
    if not value_str:
        return None
    # Remove .00 suffix
    if value_str.endswith('.00'):
        value_str = value_str[:-3]
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return None

def _calculate_confidence(match, text, pattern):
    """Calculate confidence score based on match quality and context"""
    if not match:
        return 0.0
    
    confidence = 0.5  # Base confidence
    
    # Boost confidence if pattern is specific (contains keywords)
    if any(keyword in pattern.lower() for keyword in ['model', 'device', 'ram', 'storage', 'battery', 'android', 'cpu']):
        confidence += 0.2
    
    # Boost if match is near expected keywords
    match_start = match.start()
    context_start = max(0, match_start - 50)
    context_end = min(len(text), match_start + 50)
    context = text[context_start:context_end].lower()
    
    if any(keyword in context for keyword in ['model', 'device', 'name', 'ram', 'memory', 'storage', 'battery', 'android', 'version', 'cpu', 'processor']):
        confidence += 0.2
    
    # Boost if value looks reasonable
    matched_text = match.group(0)
    if re.search(r'\d+', matched_text):
        confidence += 0.1
    
    return min(1.0, confidence)

def extract_phone_info(image_path):
    """Extract phone information from image using OCR - legacy function for backward compatibility"""
    result = extract_about_device_info(image_path)
    # Convert to legacy format
    phone_info = {
        'model': result.get('device_name') or result.get('model') or 'Unknown',
        'ram': f"{result.get('ram_gb', 0)}GB" if result.get('ram_gb') else 'Unknown',
        'os_version': result.get('os_version') or 'Unknown',
        'storage': f"{result.get('storage_total_gb', 0)}GB" if result.get('storage_total_gb') else 'Unknown',
        'processor': result.get('cpu_model') or 'Unknown',
        'battery': f"{result.get('battery_capacity_mah', 0)}mAh" if result.get('battery_capacity_mah') else 'Unknown'
    }
    return phone_info

def extract_about_device_info(image_path):
    """
    Extract comprehensive device information from "About device" screenshot.
    Returns dict with parsed fields and ocr_confidence per field.
    """
    # Open the image
    img = Image.open(image_path)
    
    # Perform OCR on the image
    text = pytesseract.image_to_string(img)
    
    # Also get detailed OCR data for confidence calculation
    try:
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except:
        ocr_data = None
    
    result = {
        'device_name': None,
        'model': None,
        'manufacturer': None,
        'ram_gb': None,
        'storage_total_gb': None,
        'storage_used_gb': None,
        'storage_used_percent': None,
        'battery_capacity_mah': None,
        'battery_percent': None,
        'os_version': None,
        'android_api_or_release': None,
        'screen_size_cm': None,
        'cpu_model': None,
        'camera_info': None,
        'ocr_text': text,  # Store raw OCR text for debugging
        'ocr_confidence': {}  # Per-field confidence scores
    }
    
    # Extract device name / model
    device_patterns = [
        (r'Device\s*name[:\s]*([^\n]+)', 0.9),
        (r'Model\s*name[:\s]*([^\n]+)', 0.9),
        (r'Model\s*number[:\s]*([^\n]+)', 0.85),
        (r'Model[:\s]*([A-Za-z0-9\s\-]+)', 0.8),
        (r'(Galaxy\s*\w+\s*\d+)', 0.75),
        (r'(iPhone\s*\d+\s*\w*)', 0.75),
        (r'(Pixel\s*\d+\s*\w*)', 0.75),
        (r'(OnePlus\s*\w+\s*\d+)', 0.75),
        (r'(Redmi\s*\w+\s*\d+)', 0.75),
        (r'(Mi\s*\w+\s*\d+)', 0.75)
    ]
    
    for pattern, base_conf in device_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if len(value) > 2 and len(value) < 50:  # Reasonable length
                result['device_name'] = value
                result['model'] = value
                result['ocr_confidence']['device_name'] = base_conf
                result['ocr_confidence']['model'] = base_conf
                break
    
    # Extract manufacturer
    manufacturer_patterns = [
        (r'Manufacturer[:\s]*([^\n]+)', 0.9),
        (r'Brand[:\s]*([^\n]+)', 0.85),
        (r'(Samsung|Apple|Google|OnePlus|Xiaomi|Redmi|Realme|Oppo|Vivo|Huawei|Motorola|LG|Sony)', 0.7)
    ]
    
    for pattern, base_conf in manufacturer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if len(value) < 30:
                result['manufacturer'] = value
                result['ocr_confidence']['manufacturer'] = base_conf
                break
    
    # Extract RAM (normalize to GB)
    ram_patterns = [
        (r'RAM[:\s]*(\d+(?:\.\d+)?)\s*GB', 0.9),
        (r'(\d+(?:\.\d+)?)\s*GB\s*RAM', 0.85),
        (r'Memory[:\s]*(\d+(?:\.\d+)?)\s*GB', 0.85),
        (r'RAM[:\s]*(\d+(?:\.\d+)?)\s*MB', 0.7)  # Will convert MB to GB
    ]
    
    for pattern, base_conf in ram_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = _normalize_units(match.group(1))
            if value:
                # Convert MB to GB if needed
                if 'MB' in pattern:
                    value = value / 1024.0
                result['ram_gb'] = value
                result['ocr_confidence']['ram_gb'] = base_conf
                break
    
    # Extract storage (total and used)
    storage_patterns = [
        (r'Storage[:\s]*(\d+(?:\.\d+)?)\s*GB\s*/\s*(\d+(?:\.\d+)?)\s*GB', 0.9),  # Used / Total
        (r'(\d+(?:\.\d+)?)\s*GB\s*/\s*(\d+(?:\.\d+)?)\s*GB', 0.85),
        (r'Total\s*storage[:\s]*(\d+(?:\.\d+)?)\s*GB', 0.85),
        (r'Storage[:\s]*(\d+(?:\.\d+)?)\s*GB', 0.8),
        (r'(\d+(?:\.\d+)?)\s*GB\s*(?:storage|memory|ROM)', 0.75)
    ]
    
    for pattern, base_conf in storage_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.lastindex and match.lastindex >= 2:
                # Pattern with used/total
                used = _normalize_units(match.group(1))
                total = _normalize_units(match.group(2))
                if used and total and total > 0:
                    result['storage_used_gb'] = used
                    result['storage_total_gb'] = total
                    result['storage_used_percent'] = (used / total) * 100
                    result['ocr_confidence']['storage_total_gb'] = base_conf
                    result['ocr_confidence']['storage_used_gb'] = base_conf
                    result['ocr_confidence']['storage_used_percent'] = base_conf
                    break
            else:
                # Only total
                total = _normalize_units(match.group(1))
                if total:
                    result['storage_total_gb'] = total
                    result['ocr_confidence']['storage_total_gb'] = base_conf
                    break
    
    # Extract battery capacity (mAh)
    battery_capacity_patterns = [
        (r'Battery\s*capacity[:\s]*(\d+)\s*mAh', 0.9),
        (r'(\d+)\s*mAh', 0.7),
        (r'Battery[:\s]*(\d+)\s*mAh', 0.8)
    ]
    
    for pattern, base_conf in battery_capacity_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 1000 <= value <= 10000:  # Reasonable range
                result['battery_capacity_mah'] = value
                result['ocr_confidence']['battery_capacity_mah'] = base_conf
                break
    
    # Extract battery percent
    battery_percent_patterns = [
        (r'Battery[:\s]*(\d+)\s*%', 0.9),
        (r'(\d+)\s*%\s*battery', 0.85),
        (r'Battery\s*level[:\s]*(\d+)\s*%', 0.9)
    ]
    
    for pattern, base_conf in battery_percent_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 0 <= value <= 100:
                result['battery_percent'] = value
                result['ocr_confidence']['battery_percent'] = base_conf
                break
    
    # Extract OS version
    os_patterns = [
        (r'Android\s*version[:\s]*(\d+(?:\.\d+)*)', 0.9),
        (r'Android\s*OS[:\s]*(\d+(?:\.\d+)*)', 0.9),
        (r'Android[:\s]*(\d+(?:\.\d+)*)', 0.85),
        (r'iOS[:\s]*(\d+(?:\.\d+)*)', 0.9),
        (r'OS\s*version[:\s]*(\d+(?:\.\d+)*)', 0.8)
    ]
    
    for pattern, base_conf in os_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            version = match.group(1)
            result['os_version'] = f"Android {version}" if 'android' in pattern.lower() else f"iOS {version}"
            result['ocr_confidence']['os_version'] = base_conf
            break
    
    # Extract Android API level
    api_patterns = [
        (r'Android\s*API\s*level[:\s]*(\d+)', 0.9),
        (r'API\s*level[:\s]*(\d+)', 0.85),
        (r'SDK\s*version[:\s]*(\d+)', 0.8)
    ]
    
    for pattern, base_conf in api_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['android_api_or_release'] = int(match.group(1))
            result['ocr_confidence']['android_api_or_release'] = base_conf
            break
    
    # Extract screen size (cm or inches)
    screen_patterns = [
        (r'Screen\s*size[:\s]*(\d+(?:\.\d+)?)\s*cm', 0.9),
        (r'Display\s*size[:\s]*(\d+(?:\.\d+)?)\s*cm', 0.9),
        (r'(\d+(?:\.\d+)?)\s*cm\s*(?:screen|display)', 0.85),
        (r'Screen\s*size[:\s]*(\d+(?:\.\d+)?)\s*inch', 0.85),  # Convert inches to cm
        (r'(\d+(?:\.\d+)?)\s*inch\s*(?:screen|display)', 0.8)
    ]
    
    for pattern, base_conf in screen_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = _normalize_units(match.group(1))
            if value:
                # Convert inches to cm if needed
                if 'inch' in pattern.lower():
                    value = value * 2.54
                result['screen_size_cm'] = value
                result['ocr_confidence']['screen_size_cm'] = base_conf
                break
    
    # Extract CPU/Processor model
    cpu_patterns = [
        (r'Processor[:\s]*([^\n]+)', 0.9),
        (r'CPU[:\s]*([^\n]+)', 0.85),
        (r'Chipset[:\s]*([^\n]+)', 0.85),
        (r'Snapdragon\s*(\d+)', 0.8),
        (r'Exynos\s*(\d+)', 0.8),
        (r'MediaTek\s*([^\s]+)', 0.8),
        (r'A(\d+)\s*Bionic', 0.8),
        (r'Kirin\s*(\d+)', 0.8)
    ]
    
    for pattern, base_conf in cpu_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if 'Snapdragon' in pattern:
                result['cpu_model'] = f"Snapdragon {match.group(1)}"
            elif 'Exynos' in pattern:
                result['cpu_model'] = f"Exynos {match.group(1)}"
            elif 'MediaTek' in pattern:
                result['cpu_model'] = f"MediaTek {match.group(1)}"
            elif 'Bionic' in pattern:
                result['cpu_model'] = f"A{match.group(1)} Bionic"
            elif 'Kirin' in pattern:
                result['cpu_model'] = f"Kirin {match.group(1)}"
            else:
                value = match.group(1).strip()
                if len(value) < 50:
                    result['cpu_model'] = value
            if result['cpu_model']:
                result['ocr_confidence']['cpu_model'] = base_conf
                break
    
    # Extract camera info
    camera_patterns = [
        (r'Camera[:\s]*([^\n]+)', 0.8),
        (r'Rear\s*camera[:\s]*([^\n]+)', 0.85),
        (r'(\d+(?:\.\d+)?)\s*MP', 0.7)
    ]
    
    for pattern, base_conf in camera_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if len(value) < 100:
                result['camera_info'] = value
                result['ocr_confidence']['camera_info'] = base_conf
                break
    
    # Calculate overall confidence for fields that were found
    for field in result['ocr_confidence']:
        if result['ocr_confidence'][field] < 0.8:
            # Adjust confidence based on field presence and context
            if result.get(field) is not None:
                result['ocr_confidence'][field] = min(1.0, result['ocr_confidence'][field] + 0.1)
    
    return result