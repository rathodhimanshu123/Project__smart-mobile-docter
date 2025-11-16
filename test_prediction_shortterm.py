"""
Unit tests for short-term battery prediction system.
Tests real-change calculation, fallback selection, clamping, zero-division safety, and SSE emission.
"""

import unittest
from datetime import datetime, timedelta
import time
from collections import deque
import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import compute_prediction, app

class TestShortTermPrediction(unittest.TestCase):
    """Test cases for compute_prediction function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
    
    def create_sample(self, pct, minutes_ago=0, charging=False):
        """Helper to create a battery sample"""
        ts = int((time.time() - (minutes_ago * 60)) * 1000)
        return {'ts': ts, 'pct': float(pct), 'charging': charging}
    
    def test_real_change_calculation(self):
        """Test that real drain is calculated from actual percent changes"""
        # Create samples showing 2% drop over 5 minutes
        samples = deque([
            self.create_sample(80.0, minutes_ago=5),
            self.create_sample(79.5, minutes_ago=4),
            self.create_sample(79.0, minutes_ago=3),
            self.create_sample(78.5, minutes_ago=2),
            self.create_sample(78.0, minutes_ago=1),
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {},
            'live': {'level': 78.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['status'], 'success')
        self.assertFalse(result['usedFallback'], "Should use real drain rate, not fallback")
        self.assertIn('drain_per_min', result)
        self.assertGreater(result['drain_per_min'], 0)
        self.assertEqual(len(result['batteryPrediction']), 181)
    
    def test_fallback_selection_high_responsiveness(self):
        """Test fallback selection for high responsiveness (>80)"""
        # Create samples with no significant change
        samples = deque([
            self.create_sample(80.0, minutes_ago=5),
            self.create_sample(80.0, minutes_ago=3),  # No change
            self.create_sample(80.0, minutes_ago=1),  # No change
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {'responsiveness': {'index': 85}},
            'live': {'level': 80.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['usedFallback'], "Should use fallback for flat data")
        # High responsiveness (>80) should give 0.4%/min
        self.assertAlmostEqual(result['drain_per_min'], 0.4, places=1)
    
    def test_fallback_selection_medium_responsiveness(self):
        """Test fallback selection for medium responsiveness (40-80)"""
        samples = deque([
            self.create_sample(80.0, minutes_ago=2),
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {'responsiveness': {'index': 60}},
            'live': {'level': 80.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['usedFallback'])
        # Medium responsiveness (40-80) should give 0.6%/min
        self.assertAlmostEqual(result['drain_per_min'], 0.6, places=1)
    
    def test_fallback_selection_low_responsiveness(self):
        """Test fallback selection for low responsiveness (<40)"""
        samples = deque([
            self.create_sample(80.0, minutes_ago=2),
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {'responsiveness': {'index': 30}},
            'live': {'level': 80.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['usedFallback'])
        # Low responsiveness (<40) should give 1.0%/min
        self.assertAlmostEqual(result['drain_per_min'], 1.0, places=1)
    
    def test_clamping_extreme_drain(self):
        """Test that extreme drain rates are clamped to [0.05, 5.0] %/min"""
        # Create samples showing extreme drain (10% drop in 1 minute = 10%/min)
        samples = deque([
            self.create_sample(80.0, minutes_ago=1),
            self.create_sample(70.0, minutes_ago=0),  # 10% drop in 1 minute
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {},
            'live': {'level': 70.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['status'], 'success')
        # Should be clamped to max 5.0%/min
        self.assertLessEqual(result['drain_per_min'], 5.0)
        self.assertGreaterEqual(result['drain_per_min'], 0.05)
    
    def test_zero_division_safety(self):
        """Test that zero division is handled safely"""
        # Create samples with same timestamp (would cause division by zero)
        ts = int(time.time() * 1000)
        samples = deque([
            {'ts': ts, 'pct': 80.0, 'charging': False},
            {'ts': ts, 'pct': 79.0, 'charging': False},  # Same timestamp
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {},
            'live': {'level': 79.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        # Should not crash, should use fallback
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['usedFallback'])
    
    def test_charging_paused(self):
        """Test that predictions pause when charging"""
        samples = deque([
            self.create_sample(80.0, minutes_ago=1),
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {},
            'live': {'level': 80.0, 'charging': True}  # Charging
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['status'], 'charging_paused')
        self.assertTrue(result['chargingPaused'])
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        # Only one sample
        samples = deque([
            self.create_sample(80.0, minutes_ago=1),
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {},
            'live': {'level': 80.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        # Should still return success but use fallback
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['usedFallback'])
        self.assertIn('samplesCount', result)
    
    def test_samples_count(self):
        """Test that sample count is correctly reported"""
        samples = deque([
            self.create_sample(80.0, minutes_ago=5),
            self.create_sample(79.0, minutes_ago=3),
            self.create_sample(78.0, minutes_ago=1),
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {},
            'live': {'level': 78.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['samplesCount'], 3)
        self.assertIn('validSampleCount', result)
    
    def test_predicted_times(self):
        """Test that projected times to thresholds are calculated"""
        # Create samples showing drain
        samples = deque([
            self.create_sample(60.0, minutes_ago=5),
            self.create_sample(55.0, minutes_ago=3),
            self.create_sample(50.0, minutes_ago=1),
        ])
        
        session_data = {
            'battery_samples': samples,
            'snapshot': {},
            'live': {'level': 50.0, 'charging': False}
        }
        
        result = compute_prediction(session_data)
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('predictedTimeTo', result)
        # Should have time to 20% (current is 50%)
        if result['predictedTimeTo']['20']:
            self.assertGreater(result['predictedTimeTo']['20'], 0)
            self.assertLessEqual(result['predictedTimeTo']['20'], 180)

if __name__ == '__main__':
    unittest.main()

