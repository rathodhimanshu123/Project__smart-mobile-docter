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
def predict_issue_and_solution(phone_info):
    # Load the model
    model = load_model()
    
    # Preprocess the phone info
    features = preprocess_phone_info(phone_info)
    
    # Make prediction
    issue_id = model.predict(features)[0]
    
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
        }
    }
    
    # Get issue and solution
    issue_data = issues_solutions.get(issue_id, {
        'issue': 'Unknown Issue',
        'solution': 'Please consult with a professional technician for diagnosis.'
    })
    
    return issue_data['issue'], issue_data['solution']