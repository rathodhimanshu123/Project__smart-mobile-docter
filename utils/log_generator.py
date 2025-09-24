import json
import os
from datetime import datetime

def generate_device_log(device_info, ocr_results):
    """
    Generate a detailed log file containing device information and analysis results
    """
    log_content = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Header
    log_content.append("=== Smart Mobile Doctor - Device Analysis Log ===")
    log_content.append(f"Analysis Date: {timestamp}")
    log_content.append(f"Session ID: {device_info.get('sessionId', 'Unknown')}\n")
    
    # Device Information Section
    log_content.append("=== Device Information ===")
    if device_info:
        # Basic Device Info
        if 'deviceInfo' in device_info:
            log_content.append("\nBASIC DEVICE INFORMATION:")
            for key, value in device_info['deviceInfo'].items():
                log_content.append(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Battery Information
        if 'batteryInfo' in device_info:
            log_content.append("\nBATTERY INFORMATION:")
            for key, value in device_info['batteryInfo'].items():
                log_content.append(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Memory Information
        if 'memoryInfo' in device_info:
            log_content.append("\nMEMORY INFORMATION:")
            for key, value in device_info['memoryInfo'].items():
                log_content.append(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Storage Information
        if 'storageInfo' in device_info:
            log_content.append("\nSTORAGE INFORMATION:")
            for key, value in device_info['storageInfo'].items():
                log_content.append(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Network Information
        if 'networkInfo' in device_info:
            log_content.append("\nNETWORK INFORMATION:")
            for key, value in device_info['networkInfo'].items():
                log_content.append(f"  {key.replace('_', ' ').title()}: {value}")
                
        # Add any additional device information
        for key, value in device_info.items():
            if key not in ['deviceInfo', 'batteryInfo', 'memoryInfo', 'storageInfo', 'networkInfo', 'sessionId']:
                if isinstance(value, dict):
                    log_content.append(f"\n{key.upper()}:")
                    for sub_key, sub_value in value.items():
                        log_content.append(f"  {sub_key}: {sub_value}")
                elif not isinstance(value, (list, dict)):
                    log_content.append(f"{key}: {value}")
    
    # OCR Results Section
    log_content.append("\n=== OCR Analysis Results ===")
    if ocr_results:
        for key, value in ocr_results.items():
            log_content.append(f"{key}: {value}")
    
    # System Recommendations
    log_content.append("\n=== System Recommendations ===")
    if 'issue' in device_info:
        log_content.append(f"Detected Issue: {device_info['issue']}")
        log_content.append(f"Recommended Solution: {device_info.get('solution', 'Contact technical support')}")
    
    # Generate unique filename
    filename = f"device_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_path = os.path.join('static', 'logs', filename)
    
    # Ensure logs directory exists
    os.makedirs(os.path.join('static', 'logs'), exist_ok=True)
    
    try:
        # Write log file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_content))
        
        # Verify file was created
        if os.path.exists(file_path):
            return filename
        else:
            raise Exception("Log file was not created successfully")
    except Exception as e:
        print(f"Error creating log file: {str(e)}")
        return None

