import os
import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Path to save the trained model
MODEL_PATH = os.path.join('models', 'phone_model.pkl')

# Function to create mock dataset
def create_mock_data():
    # Create directory if it doesn't exist
    os.makedirs('models', exist_ok=True)
    
    # Number of samples
    n_samples = 500
    
    # Generate random data
    ram_values = np.random.choice([2, 3, 4, 6, 8, 12, 16], size=n_samples)
    os_version_values = np.random.choice(range(7, 14), size=n_samples)  # Android 7-13
    storage_values = np.random.choice([16, 32, 64, 128, 256, 512], size=n_samples)
    battery_values = np.random.choice(range(2000, 5500, 500), size=n_samples)
    
    # Generate target issues (0-5 representing different issues)
    # Logic: Lower RAM and higher OS version might lead to performance issues
    #        Lower battery capacity might lead to battery drain issues
    #        etc.
    
    issues = []
    for i in range(n_samples):
        ram = ram_values[i]
        os_version = os_version_values[i]
        storage = storage_values[i]
        battery = battery_values[i]
        
        # Simplified logic for issue determination
        if battery < 3000:
            issue = 0  # Battery Draining Fast
        elif ram < 4 and os_version > 10:
            issue = 2  # Slow Performance
        elif storage < 64:
            issue = 3  # Storage Issues
        elif ram < 6 and os_version > 11:
            issue = 4  # App Crashes
        elif battery > 4000 and ram > 8:
            issue = 1  # Device Overheating
        else:
            issue = 5  # Connectivity Problems
        
        issues.append(issue)
    
    # Create DataFrame
    df = pd.DataFrame({
        'RAM': ram_values,
        'OS_Version': os_version_values,
        'Storage': storage_values,
        'Battery': battery_values,
        'Issue': issues
    })
    
    # Save to CSV
    csv_path = os.path.join('models', 'mock_data.csv')
    df.to_csv(csv_path, index=False)
    
    return df

# Function to train the model
def train_model():
    # Check if mock data exists, if not create it
    csv_path = os.path.join('models', 'mock_data.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        df = create_mock_data()
    
    # Prepare features and target
    X = df[['RAM', 'OS_Version', 'Storage', 'Battery']].values
    y = df['Issue'].values
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train Random Forest model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Print model accuracy
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.2f}")
    
    # Save the model
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    
    return model

# If run directly, train the model
if __name__ == "__main__":
    train_model()