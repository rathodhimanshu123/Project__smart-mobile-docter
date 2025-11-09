@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Training the model...
python models/train_model.py

echo Setup complete!