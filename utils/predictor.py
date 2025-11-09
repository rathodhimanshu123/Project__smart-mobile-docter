import os
import pickle
import numpy as np
import re  # Add this import
from sklearn.ensemble import RandomForestClassifier

# Path to the trained model
MODEL_PATH = os.path.join('models', 'phone_model.pkl')

# Function to load the trained model
def load_model():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        return model
    else:
        # If model doesn't exist, train a new one
        from models.train_model import train_model
        return train_model()

# Function to preprocess phone info for prediction
def preprocess_phone_info(phone_info):
    # Extract numerical values from RAM (e.g., "4GB" -> 4)
    ram = 0
    if phone_info['ram'] != 'Unknown':
        ram_match = re.search(r'(\d+)', phone_info['ram'])
        if ram_match:
            ram = int(ram_match.group(1))
    
    # Extract OS version number
    os_version = 0
    if phone_info['os_version'] != 'Unknown':
        os_match = re.search(r'(\d+)', phone_info['os_version'])
        if os_match:
            os_version = int(os_match.group(1))
    
    # Extract storage value
    storage = 0
    if phone_info['storage'] != 'Unknown':
        storage_match = re.search(r'(\d+)', phone_info['storage'])
        if storage_match:
            storage = int(storage_match.group(1))
    
    # Extract battery capacity
    battery = 0
    if phone_info['battery'] != 'Unknown':
        battery_match = re.search(r'(\d+)', phone_info['battery'])
        if battery_match:
            battery = int(battery_match.group(1))
    
    # Create feature vector
    features = np.array([ram, os_version, storage, battery]).reshape(1, -1)
    
    return features

# Function to predict issue and solution based on phone info
def _parse_numeric_from_string(text, default=0):
    if not isinstance(text, str):
        try:
            return int(text)
        except Exception:
            return default
    m = re.search(r'(\d+(?:\.\d+)?)', text)
    if not m:
        return default
    try:
        v = float(m.group(1))
        return int(v) if v.is_integer() else v
    except Exception:
        return default


def _is_connectivity_bad(context: dict) -> bool:
    on_line = context.get('onLine') or context.get('online')
    if isinstance(on_line, str):
        on_line = on_line.strip().lower() in ('yes', 'true', '1')
    if on_line is False:
        return True

    speed_text = context.get('networkSpeed') or context.get('speed')
    speed_mbps = _parse_numeric_from_string(speed_text, default=None) if speed_text else None
    if isinstance(speed_mbps, (int, float)) and speed_mbps < 1:
        return True

    conn_type = (context.get('networkType') or context.get('type') or '').strip().lower()
    if conn_type in ('offline', 'none'):
        return True

    return False


def predict_issue_and_solution(phone_info):
    # Load the model
    model = load_model()
    
    # Preprocess the phone info
    features = preprocess_phone_info(phone_info)
    
    # Make prediction
    issue_id = model.predict(features)[0]
    proba = None
    if hasattr(model, 'predict_proba'):
        try:
            proba = model.predict_proba(features)[0]
        except Exception:
            proba = None
    
    # Map issue ID to issue and solution
    issues_solutions = {
        0: {
            'issue': 'Battery Draining Fast',
            'solution': 'Check for battery-intensive apps, reduce screen brightness, disable unused connectivity features (Bluetooth, WiFi, GPS), and consider battery replacement if the device is older than 2 years.'
        },
        1: {
            'issue': 'Device Overheating',
            'solution': 'Close background apps, remove phone case while charging, avoid using phone while charging, update software, and avoid direct sunlight exposure.'
        },
        2: {
            'issue': 'Slow Performance',
            'solution': 'Clear cache, uninstall unused apps, check for available storage space, restart your device regularly, and consider factory reset if problems persist.'
        },
        3: {
            'issue': 'Storage Issues',
            'solution': 'Delete unused apps and media, clear app caches, move photos/videos to cloud storage, and use file manager apps to identify large files.'
        },
        4: {
            'issue': 'App Crashes',
            'solution': 'Update apps to latest versions, clear app cache, ensure sufficient storage space, and reinstall problematic apps.'
        },
        5: {
            'issue': 'Connectivity Problems',
            'solution': 'Toggle airplane mode, restart device, reset network settings, update software, and check for carrier outages.'
        },
        6: {
            'issue': 'No Major Issues Detected',
            'solution': 'Your device appears healthy based on available indicators. Keep your software up to date, clear cache periodically, and monitor battery and storage for best performance.'
        },
        7: {
            'issue': 'Minor Optimization Opportunities',
            'solution': 'Your device is generally healthy. For best responsiveness, clear cache, remove rarely used apps, keep at least 20% storage free, and reboot periodically.'
        }
    }
    
    # Heuristic post-processing to avoid implausible predictions
    # 1) If model predicts Connectivity but no network indicators suggest problems, pick next best label
    if issue_id == 5 and not _is_connectivity_bad(phone_info):
        if proba is not None and len(proba) >= len(issues_solutions):
            # choose highest-prob non-connectivity class
            sorted_labels = np.argsort(proba)[::-1]
            for lbl in sorted_labels:
                if int(lbl) != 5:
                    issue_id = int(lbl)
                    break
        else:
            # fall back to Storage Issues or Slow Performance based on simple device stats
            storage_gb = _parse_numeric_from_string(phone_info.get('storage', '0'))
            ram_gb = _parse_numeric_from_string(phone_info.get('ram', '0'))
            if storage_gb <= 32:
                issue_id = 3  # Storage Issues
            elif ram_gb <= 3:
                issue_id = 2  # Slow Performance
            else:
                issue_id = 2

    # 2) If storage capacity is clearly high (> 64GB), avoid Storage Issues unless model very confident
    if issue_id == 3:
        storage_gb = _parse_numeric_from_string(phone_info.get('storage', '0'))
        if storage_gb > 64:
            if proba is None or (max(proba) < 0.6):
                issue_id = 2

    # 3) If device looks generally healthy, prefer "No Major Issues Detected"
    ram_gb = _parse_numeric_from_string(phone_info.get('ram', '0'))
    os_ver = _parse_numeric_from_string(phone_info.get('os_version', '0'))
    storage_gb = _parse_numeric_from_string(phone_info.get('storage', '0'))
    battery_mah = _parse_numeric_from_string(phone_info.get('battery', '0'))
    looks_healthy = (
        (ram_gb >= 6 or os_ver >= 12) and storage_gb >= 64 and battery_mah >= 4000
    )
    if looks_healthy:
        high_conf = False
        if proba is not None:
            try:
                high_conf = float(np.max(proba)) >= 0.8
            except Exception:
                high_conf = False
        if not high_conf:
            issue_id = 6

    # Compute a simple performance score (0-100) aligned with the diagnosis
    # Weights: RAM 30%, Storage capacity 25%, Battery 25%, OS recency 20%
    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    ram_score = clamp((ram_gb / 12.0) * 100, 0, 100)  # 12GB+ considered full score
    storage_score = clamp((storage_gb / 128.0) * 100, 0, 100)  # 128GB full
    battery_score = clamp((battery_mah / 5000.0) * 100, 0, 100)  # 5000mAh full
    os_score = clamp(((os_ver - 8) / 6.0) * 100, 0, 100)  # Android 14 ~= full

    performance_score = int(round(0.30 * ram_score + 0.25 * storage_score + 0.25 * battery_score + 0.20 * os_score))

    # If performance score is strong, avoid negative diagnoses unless model is highly confident
    if performance_score >= 80:
        strong_conf = False
        if proba is not None:
            try:
                strong_conf = float(np.max(proba)) >= 0.85
            except Exception:
                strong_conf = False
        if not strong_conf:
            issue_id = 6

    # Final consistency rule: do not report "Slow Performance" with a high score
    if performance_score >= 85:
        issue_id = 6
    elif performance_score >= 70 and int(issue_id) == 2:
        # Reframe as minor optimization instead of a problem
        issue_id = 7

    # Get issue and solution
    issue_data = issues_solutions.get(int(issue_id), {
        'issue': 'Unknown Issue',
        'solution': 'Please consult with a professional technician for diagnosis.'
    })
    
    return issue_data['issue'], issue_data['solution'], performance_score