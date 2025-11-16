"""
Unit tests for compute_prediction function
Tests zero-division, clamping, and edge cases
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import compute_prediction
from datetime import datetime, timedelta

def test_insufficient_data():
    """Test with insufficient data (less than 2 points)"""
    session_data = {
        'history': [
            {
                'timestamp': datetime.now().isoformat(),
                'snapshot': {
                    'battery': {'level': 80},
                    'storage': {'storageSandboxUsagePercent': 50}
                }
            }
        ],
        'snapshot': {}
    }
    result = compute_prediction(session_data)
    assert result['status'] == 'insufficient_data'
    assert 'message' in result
    print("✅ Test 1 passed: Insufficient data handled")

def test_zero_division_battery():
    """Test zero-division protection in battery calculation"""
    now = datetime.now()
    session_data = {
        'history': [
            {
                'timestamp': (now - timedelta(hours=2)).isoformat(),
                'snapshot': {
                    'battery': {'level': 80},
                    'storage': {'storageSandboxUsagePercent': 50}
                }
            },
            {
                'timestamp': now.isoformat(),
                'snapshot': {
                    'battery': {'level': 80},  # Same level (zero slope)
                    'storage': {'storageSandboxUsagePercent': 50}
                }
            }
        ],
        'snapshot': {}
    }
    result = compute_prediction(session_data)
    assert result['status'] == 'success'
    assert len(result['time_series']['battery']) == 30
    # All values should be clamped 0-100
    assert all(0 <= val <= 100 for val in result['time_series']['battery'])
    print("✅ Test 2 passed: Zero-division protection in battery calculation")

def test_clamping_0_100():
    """Test that all predictions are clamped to 0-100"""
    now = datetime.now()
    session_data = {
        'history': [
            {
                'timestamp': (now - timedelta(hours=1)).isoformat(),
                'snapshot': {
                    'battery': {'level': 5},  # Very low, might go negative
                    'storage': {'storageSandboxUsagePercent': 95},  # Very high, might exceed 100
                    'responsiveness': {'index': 10}  # Low responsiveness
                }
            },
            {
                'timestamp': now.isoformat(),
                'snapshot': {
                    'battery': {'level': 3},  # Draining fast
                    'storage': {'storageSandboxUsagePercent': 98},  # Growing fast
                    'responsiveness': {'index': 8}  # Declining
                }
            }
        ],
        'snapshot': {}
    }
    result = compute_prediction(session_data)
    assert result['status'] == 'success'
    
    # Check clamping
    assert all(0 <= val <= 100 for val in result['time_series']['battery'])
    assert all(0 <= val <= 100 for val in result['time_series']['storage'])
    assert all(0 <= val <= 100 for val in result['time_series']['responsiveness'])
    assert 0 <= result['health_score_30_day'] <= 100
    assert 0 <= result['risk_scores']['thermal_stress'] <= 100
    print("✅ Test 3 passed: All values clamped to 0-100")

def test_empty_history():
    """Test with empty history"""
    session_data = {
        'history': [],
        'snapshot': {}
    }
    result = compute_prediction(session_data)
    assert result['status'] == 'insufficient_data'
    print("✅ Test 4 passed: Empty history handled")

def test_missing_fields():
    """Test with missing optional fields"""
    now = datetime.now()
    session_data = {
        'history': [
            {
                'timestamp': (now - timedelta(hours=1)).isoformat(),
                'snapshot': {
                    'battery': {'level': 80}
                    # Missing storage and responsiveness
                }
            },
            {
                'timestamp': now.isoformat(),
                'snapshot': {
                    'battery': {'level': 75}
                    # Missing storage and responsiveness
                }
            }
        ],
        'snapshot': {}
    }
    result = compute_prediction(session_data)
    assert result['status'] == 'success'
    # Should use fallback values for missing fields
    assert len(result['time_series']['storage']) == 30
    assert len(result['time_series']['responsiveness']) == 30
    print("✅ Test 5 passed: Missing fields handled with fallbacks")

def test_health_score_calculation():
    """Test health score calculation"""
    now = datetime.now()
    session_data = {
        'history': [
            {
                'timestamp': (now - timedelta(hours=1)).isoformat(),
                'snapshot': {
                    'battery': {'level': 90},
                    'storage': {'storageSandboxUsagePercent': 20},
                    'responsiveness': {'index': 80}
                }
            },
            {
                'timestamp': now.isoformat(),
                'snapshot': {
                    'battery': {'level': 88},
                    'storage': {'storageSandboxUsagePercent': 22},
                    'responsiveness': {'index': 78}
                }
            }
        ],
        'snapshot': {}
    }
    result = compute_prediction(session_data)
    assert result['status'] == 'success'
    assert 'health_score_30_day' in result
    assert 0 <= result['health_score_30_day'] <= 100
    print("✅ Test 6 passed: Health score calculated correctly")

def test_recommendations():
    """Test that recommendations are generated"""
    now = datetime.now()
    session_data = {
        'history': [
            {
                'timestamp': (now - timedelta(hours=1)).isoformat(),
                'snapshot': {
                    'battery': {'level': 25},  # Low battery
                    'storage': {'storageSandboxUsagePercent': 85},  # High storage
                    'responsiveness': {'index': 30}  # Low responsiveness
                }
            },
            {
                'timestamp': now.isoformat(),
                'snapshot': {
                    'battery': {'level': 20},  # Very low
                    'storage': {'storageSandboxUsagePercent': 88},  # Very high
                    'responsiveness': {'index': 25}  # Declining
                }
            }
        ],
        'snapshot': {}
    }
    result = compute_prediction(session_data)
    assert result['status'] == 'success'
    assert 'recommendations' in result
    assert len(result['recommendations']) > 0
    print("✅ Test 7 passed: Recommendations generated")

if __name__ == '__main__':
    print("Running prediction unit tests...\n")
    try:
        test_insufficient_data()
        test_zero_division_battery()
        test_clamping_0_100()
        test_empty_history()
        test_missing_fields()
        test_health_score_calculation()
        test_recommendations()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

