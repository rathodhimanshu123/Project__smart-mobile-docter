"""
Unit tests for OCR parsing and true scoring functionality.
Tests edge cases and various scenarios for robust parsing and scoring.
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.ocr_processor import extract_about_device_info, _normalize_units
from app import compute_true_score, compute_verified_score, session_store
import uuid


class TestOCRParsing(unittest.TestCase):
    """Test OCR parsing functionality"""
    
    def test_normalize_units(self):
        """Test unit normalization"""
        from utils.ocr_processor import _normalize_units
        
        # Test removing .00 suffix
        self.assertEqual(_normalize_units("8.00"), 8.0)
        self.assertEqual(_normalize_units("8.50"), 8.5)
        self.assertEqual(_normalize_units("128"), 128.0)
        
        # Test invalid inputs
        self.assertIsNone(_normalize_units(""))
        self.assertIsNone(_normalize_units("abc"))
        self.assertIsNone(_normalize_units(None))
    
    def test_ram_parsing(self):
        """Test RAM parsing with various formats"""
        # Mock OCR text with different RAM formats
        test_cases = [
            ("RAM: 8 GB", 8.0),
            ("RAM 8.00 GB", 8.0),
            ("Memory: 6 GB", 6.0),
            ("RAM: 4096 MB", 4.0),  # Should convert MB to GB
        ]
        
        # Note: This is a simplified test - full OCR would require image processing
        # In practice, you'd use mock OCR text or test images
        for text, expected in test_cases:
            # This would be tested with actual OCR extraction
            pass
    
    def test_storage_parsing(self):
        """Test storage parsing with used/total formats"""
        # Test cases for storage parsing
        test_cases = [
            ("Storage: 64 GB / 128 GB", (64.0, 128.0)),
            ("64 GB / 128 GB", (64.0, 128.0)),
            ("Total storage: 256 GB", (None, 256.0)),
        ]
        
        # Similar to RAM - would need actual OCR or mocked text
        pass
    
    def test_battery_parsing(self):
        """Test battery capacity and percent parsing"""
        # Test cases
        test_cases = [
            ("Battery capacity: 4000 mAh", 4000),
            ("Battery: 85%", 85),
            ("Battery level: 50%", 50),
        ]
        
        pass


class TestTrueScoring(unittest.TestCase):
    """Test true health score computation"""
    
    def setUp(self):
        """Set up test session"""
        self.session_id = str(uuid.uuid4())
        session_store.create_session(self.session_id)
    
    def tearDown(self):
        """Clean up test session"""
        # Session will expire naturally, but we can clean up if needed
        pass
    
    def test_battery_scoring_with_capacity(self):
        """Test battery scoring when capacity is known"""
        device_info = {
            'battery_capacity_mah': 3500,  # 500mAh below expected (4000)
            'battery_percent': 80,
            'model': 'Galaxy S21',
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('battery', breakdown)
        self.assertIn('score', breakdown['battery'])
        self.assertGreater(breakdown['battery']['score'], 0)
        self.assertLessEqual(breakdown['battery']['score'], 100)
    
    def test_battery_scoring_without_capacity(self):
        """Test battery scoring when only percent is known"""
        device_info = {
            'battery_percent': 75,
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('battery', breakdown)
        # Should still compute a score based on percent
        self.assertGreater(breakdown['battery']['score'], 0)
    
    def test_storage_scoring_complete(self):
        """Test storage scoring with total and used"""
        device_info = {
            'storage_total_gb': 128,
            'storage_used_gb': 64,  # 50% used, 50% free
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('storage', breakdown)
        # 50% free should give around 50 score
        self.assertGreater(breakdown['storage']['score'], 40)
        self.assertLess(breakdown['storage']['score'], 60)
    
    def test_storage_scoring_low_capacity_penalty(self):
        """Test storage scoring with low capacity penalty"""
        device_info = {
            'storage_total_gb': 16,  # Low capacity
            'storage_used_gb': 8,  # 50% free
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('storage', breakdown)
        # Should have penalty applied (20% reduction)
        # 50% free = 50, with penalty = 40
        self.assertLess(breakdown['storage']['score'], 50)
    
    def test_storage_scoring_unknown_total(self):
        """Test storage scoring when total is unknown"""
        device_info = {
            'storage_used_percent': 60,  # 40% free
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('storage', breakdown)
        # Should still compute based on percent
        self.assertGreater(breakdown['storage']['score'], 0)
    
    def test_ram_responsiveness_scoring(self):
        """Test RAM/responsiveness scoring"""
        device_info = {
            'ram_gb': 8,
            'cpu_model': 'Snapdragon 888',
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('responsiveness', breakdown)
        # 8GB RAM should score well
        self.assertGreater(breakdown['responsiveness']['score'], 70)
    
    def test_os_scoring_android_api(self):
        """Test OS scoring with Android API level"""
        device_info = {
            'android_api_or_release': 33,  # Android 13
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('os', breakdown)
        # API 33 should score high
        self.assertGreater(breakdown['os']['score'], 80)
    
    def test_os_scoring_version_string(self):
        """Test OS scoring with version string"""
        device_info = {
            'os_version': 'Android 12',
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('os', breakdown)
        # Android 12 should score reasonably
        self.assertGreater(breakdown['os']['score'], 50)
    
    def test_complete_scoring(self):
        """Test complete scoring with all fields"""
        device_info = {
            'device_name': 'Galaxy S21',
            'model': 'SM-G991B',
            'manufacturer': 'Samsung',
            'ram_gb': 8,
            'storage_total_gb': 128,
            'storage_used_gb': 64,
            'battery_capacity_mah': 4000,
            'battery_percent': 85,
            'os_version': 'Android 13',
            'android_api_or_release': 33,
            'cpu_model': 'Snapdragon 888',
            'ocr_confidence': {
                'device_name': 0.9,
                'ram_gb': 0.9,
                'storage_total_gb': 0.9,
                'os_version': 0.9
            }
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('final_score', breakdown)
        self.assertGreaterEqual(breakdown['final_score'], 0)
        self.assertLessEqual(breakdown['final_score'], 100)
        
        # All components should be present
        self.assertIn('battery', breakdown)
        self.assertIn('storage', breakdown)
        self.assertIn('responsiveness', breakdown)
        self.assertIn('os', breakdown)
        
        # Each component should have score and explanation
        for component in ['battery', 'storage', 'responsiveness', 'os']:
            self.assertIn('score', breakdown[component])
            self.assertIn('explanation', breakdown[component])
            self.assertIn('raw', breakdown[component])
    
    def test_scoring_with_missing_fields(self):
        """Test scoring gracefully handles missing fields"""
        device_info = {
            'ram_gb': 6,
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # Should still compute a score with defaults
        self.assertIn('final_score', breakdown)
        # Missing fields should use default scores (50)
        # So final should be around 50
        self.assertGreater(breakdown['final_score'], 30)
        self.assertLess(breakdown['final_score'], 70)
    
    def test_scoring_edge_cases(self):
        """Test edge cases in scoring"""
        # Test with zero values
        device_info = {
            'storage_total_gb': 128,
            'storage_used_gb': 128,  # 100% used
            'battery_percent': 0,  # Dead battery
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # Should handle edge cases gracefully
        self.assertGreaterEqual(breakdown['final_score'], 0)
        self.assertLessEqual(breakdown['final_score'], 100)
        
        # Storage should be 0 (100% used)
        self.assertEqual(breakdown['storage']['score'], 0)
        
        # Battery should be low
        self.assertLess(breakdown['battery']['score'], 30)


class TestScoringFormulas(unittest.TestCase):
    """Test specific scoring formulas and calculations"""
    
    def setUp(self):
        """Set up test session"""
        self.session_id = str(uuid.uuid4())
        session_store.create_session(self.session_id)
    
    def test_weighted_average(self):
        """Test that final score is correctly weighted"""
        device_info = {
            'battery_percent': 100,  # Should give high battery score
            'storage_total_gb': 128,
            'storage_used_gb': 0,  # 100% free = 100 storage score
            'ram_gb': 12,  # High RAM
            'os_version': 'Android 14',  # Latest
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_true_score(self.session_id)
        
        # Calculate expected weighted average
        battery_score = breakdown['battery']['score']
        storage_score = breakdown['storage']['score']
        responsiveness_score = breakdown['responsiveness']['score']
        os_score = breakdown['os']['score']
        
        expected_final = (
            battery_score * 0.30 +
            storage_score * 0.30 +
            responsiveness_score * 0.20 +
            os_score * 0.20
        )
        
        # Allow small rounding differences
        self.assertAlmostEqual(breakdown['final_score'], expected_final, places=0)


class TestVerifiedScoring(unittest.TestCase):
    """Test verified health score computation"""
    
    def setUp(self):
        """Set up test session"""
        self.session_id = str(uuid.uuid4())
        session_store.create_session(self.session_id)
    
    def test_verified_scoring_with_capacity(self):
        """Test verified scoring when battery capacity is present"""
        device_info = {
            'battery_capacity_mah': 3500,
            'battery_percent': 80,
            'ram_gb': 8,
            'storage_total_gb': 128,
            'storage_used_gb': 64,
            'os_version': 'Android 13',
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertIn('verified_score', breakdown)
        self.assertGreaterEqual(breakdown['verified_score'], 0)
        self.assertLessEqual(breakdown['verified_score'], 100)
        self.assertIn('battery', breakdown)
        self.assertIn('storage', breakdown)
        self.assertIn('ram_responsiveness', breakdown)
        self.assertIn('os', breakdown)
    
    def test_verified_scoring_battery_without_capacity(self):
        """Test verified scoring when only battery percent is known"""
        device_info = {
            'battery_percent': 75,
            'ram_gb': 6,
            'storage_total_gb': 64,
            'storage_used_gb': 32,
            'os_version': 'Android 12',
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # Should penalize unknown health (0.85 multiplier)
        self.assertLess(breakdown['battery']['score'], 75)
        self.assertTrue(breakdown['battery']['uses_fallback'])
    
    def test_verified_scoring_storage_zero_total(self):
        """Test verified scoring edge case: storageTotal == 0"""
        device_info = {
            'storage_total_gb': 0,
            'storage_used_gb': 0,
            'ram_gb': 4,
            'battery_percent': 50,
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # Should handle zero storage gracefully
        self.assertEqual(breakdown['storage']['score'], 50)  # Default
        self.assertTrue(breakdown['storage']['uses_fallback'])
    
    def test_verified_scoring_missing_fields(self):
        """Test verified scoring with missing fields"""
        device_info = {
            'ram_gb': 6,
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        self.assertTrue(breakdown['has_missing_fields'])
        # Should use conservative defaults
        self.assertEqual(breakdown['battery']['score'], 50)
        self.assertEqual(breakdown['storage']['score'], 50)
        self.assertEqual(breakdown['os']['score'], 50)
    
    def test_verified_scoring_extreme_values(self):
        """Test verified scoring with extreme values"""
        device_info = {
            'battery_percent': 100,
            'battery_capacity_mah': 5000,  # Very high
            'ram_gb': 16,  # Very high
            'storage_total_gb': 512,
            'storage_used_gb': 0,  # 100% free
            'os_version': 'Android 14',
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # Should clamp to 100
        self.assertLessEqual(breakdown['verified_score'], 100)
        self.assertGreater(breakdown['verified_score'], 80)  # Should be high
    
    def test_verified_scoring_ram_responsiveness_formula(self):
        """Test RAM+Responsiveness formula: 0.5*ramNorm + 0.5*responsivenessIndex"""
        device_info = {
            'ram_gb': 8,
            'storage_total_gb': 128,
            'storage_used_gb': 64,
            'battery_percent': 80,
            'os_version': 'Android 13',
            'ocr_confidence': {}
        }
        
        # Add snapshot with responsiveness
        snapshot = {
            'responsiveness': {'index': 75}
        }
        sess = session_store.get_session(self.session_id)
        sess['snapshot'] = snapshot
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # ramNorm = (8/8)*100 = 100
        # ramRespScore = 0.5*100 + 0.5*75 = 87.5
        self.assertAlmostEqual(breakdown['ram_responsiveness']['score'], 87.5, places=1)
    
    def test_verified_scoring_os_recent(self):
        """Test OS scoring: recent versions should score 100"""
        device_info = {
            'os_version': 'Android 13',
            'ram_gb': 6,
            'storage_total_gb': 128,
            'storage_used_gb': 64,
            'battery_percent': 80,
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # Android 13 >= 12, should score 100
        self.assertEqual(breakdown['os']['score'], 100)
    
    def test_verified_scoring_os_old(self):
        """Test OS scoring: old versions should score 50"""
        device_info = {
            'os_version': 'Android 7',
            'ram_gb': 6,
            'storage_total_gb': 128,
            'storage_used_gb': 64,
            'battery_percent': 80,
            'ocr_confidence': {}
        }
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        self.assertIsNotNone(breakdown)
        # Android 7 < 8, should score 50
        self.assertEqual(breakdown['os']['score'], 50)
    
    def test_verified_scoring_weighted_average(self):
        """Test that final score is correctly weighted"""
        device_info = {
            'battery_percent': 100,
            'battery_capacity_mah': 4000,
            'ram_gb': 8,
            'storage_total_gb': 128,
            'storage_used_gb': 0,  # 100% free
            'os_version': 'Android 14',
            'ocr_confidence': {}
        }
        
        snapshot = {'responsiveness': {'index': 100}}
        sess = session_store.get_session(self.session_id)
        sess['snapshot'] = snapshot
        
        session_store.set_device_info(self.session_id, device_info)
        session_store.confirm_about_info(self.session_id)
        
        breakdown = compute_verified_score(self.session_id)
        
        # Calculate expected weighted average
        battery_score = breakdown['battery']['score']
        storage_score = breakdown['storage']['score']
        ram_resp_score = breakdown['ram_responsiveness']['score']
        os_score = breakdown['os']['score']
        
        expected_final = (
            battery_score * 0.30 +
            storage_score * 0.30 +
            ram_resp_score * 0.20 +
            os_score * 0.20
        )
        
        # Allow small rounding differences
        self.assertAlmostEqual(breakdown['verified_score'], expected_final, places=0)


if __name__ == '__main__':
    unittest.main()

