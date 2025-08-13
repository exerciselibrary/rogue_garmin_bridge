#!/usr/bin/env python3
import pytest
import tempfile
import os
import sys
import shutil
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.fit.fit_converter import FITConverter

class TestFITConverter:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.fit_converter = FITConverter(output_dir=self.temp_dir)
        
        self.sample_bike_data = {
            "workout_type": "bike",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "total_duration": 1800.0,
            "total_distance": 15000.0,
            "total_calories": 300,
            "avg_power": 150,
            "max_power": 250,
            "avg_heart_rate": 140,
            "max_heart_rate": 165,
            "avg_cadence": 85,
            "max_cadence": 110,
            "avg_speed": 30.0,
            "max_speed": 45.0,
            "normalized_power": 160,
            "serial_number": 123456789,
            "software_version_scaled": 100.0,
            "hardware_version": 1,
            "data_series": {
                "absolute_timestamps": [
                    (datetime.now(timezone.utc) + timedelta(seconds=i)).isoformat() 
                    for i in range(0, 1800, 10)
                ],
                "powers": [150 + (i % 50) for i in range(180)],
                "heart_rates": [140 + (i % 25) for i in range(180)],
                "cadences": [85 + (i % 15) for i in range(180)],
                "speeds": [30.0 + (i % 10) for i in range(180)],
                "distances": [float(i * 83.33) for i in range(180)]
            }
        }
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_fit_file_creation_bike_workout(self):
        result = self.fit_converter.convert_workout(self.sample_bike_data)
        assert result is not None
        assert os.path.exists(result)
        assert result.endswith('.fit')
        assert os.path.getsize(result) > 0
    
    def test_fit_file_structure_validation(self):
        with patch('src.fit.fit_converter.FitFileBuilder') as mock_builder:
            mock_instance = Mock()
            mock_builder.return_value = mock_instance
            mock_fit_file = Mock()
            mock_instance.build.return_value = mock_fit_file
            
            result = self.fit_converter.convert_workout(self.sample_bike_data)
            
            add_calls = mock_instance.add.call_args_list
            message_types = [call[0][0].__class__.__name__ for call in add_calls]
            
            required_messages = [
                'FileIdMessage', 'DeviceInfoMessage', 'EventMessage', 
                'RecordMessage', 'LapMessage', 'SessionMessage', 'ActivityMessage'
            ]
            
            for msg_type in required_messages:
                assert any(msg_type in msg for msg in message_types), f"{msg_type} should be present in FIT file"
    
    def test_data_mapping_bike_metrics(self):
        with patch('src.fit.fit_converter.FitFileBuilder') as mock_builder:
            mock_instance = Mock()
            mock_builder.return_value = mock_instance
            mock_fit_file = Mock()
            mock_instance.build.return_value = mock_fit_file
            
            self.fit_converter.convert_workout(self.sample_bike_data)
            
            add_calls = mock_instance.add.call_args_list
            record_calls = [call for call in add_calls if 'RecordMessage' in str(call[0][0].__class__.__name__)]
            
            assert len(record_calls) > 0, "Should have record messages"
            
            first_record = record_calls[0][0][0]
            assert hasattr(first_record, 'power'), "Record should have power field"
            assert hasattr(first_record, 'heart_rate'), "Record should have heart_rate field"
            assert hasattr(first_record, 'cadence'), "Record should have cadence field"
            assert hasattr(first_record, 'speed'), "Record should have speed field"
    
    def test_device_identification_bike(self):
        with patch('src.fit.fit_converter.FitFileBuilder') as mock_builder:
            mock_instance = Mock()
            mock_builder.return_value = mock_instance
            mock_fit_file = Mock()
            mock_instance.build.return_value = mock_fit_file
            
            self.fit_converter.convert_workout(self.sample_bike_data)
            
            add_calls = mock_instance.add.call_args_list
            file_id_calls = [call for call in add_calls if 'FileIdMessage' in str(call[0][0].__class__.__name__)]
            device_info_calls = [call for call in add_calls if 'DeviceInfoMessage' in str(call[0][0].__class__.__name__)]
            
            assert len(file_id_calls) > 0, "Should have FileIdMessage"
            assert len(device_info_calls) > 0, "Should have DeviceInfoMessage"
            
            file_id_msg = file_id_calls[0][0][0]
            device_info_msg = device_info_calls[0][0][0]
            
            assert hasattr(file_id_msg, 'manufacturer'), "FileId should have manufacturer"
            assert hasattr(file_id_msg, 'product'), "FileId should have product"
            assert hasattr(file_id_msg, 'serial_number'), "FileId should have serial_number"
            
            assert hasattr(device_info_msg, 'manufacturer'), "DeviceInfo should have manufacturer"
            assert hasattr(device_info_msg, 'product'), "DeviceInfo should have product"
            assert hasattr(device_info_msg, 'serial_number'), "DeviceInfo should have serial_number"
    
    def test_training_load_fields_present(self):
        with patch('src.fit.fit_converter.FitFileBuilder') as mock_builder:
            mock_instance = Mock()
            mock_builder.return_value = mock_instance
            mock_fit_file = Mock()
            mock_instance.build.return_value = mock_fit_file
            
            self.fit_converter.convert_workout(self.sample_bike_data)
            
            add_calls = mock_instance.add.call_args_list
            session_calls = [call for call in add_calls if 'SessionMessage' in str(call[0][0].__class__.__name__)]
            
            if session_calls:
                session_msg = session_calls[0][0][0]
                assert hasattr(session_msg, 'avg_power'), "Session should have avg_power for training load"
                assert hasattr(session_msg, 'max_power'), "Session should have max_power for training load"
                assert hasattr(session_msg, 'normalized_power'), "Session should have normalized_power for training load"
                assert hasattr(session_msg, 'avg_heart_rate'), "Session should have avg_heart_rate for training load"
    
    def test_timestamp_validation(self):
        result = self.fit_converter.convert_workout(self.sample_bike_data)
        assert result is not None, "FIT file should be created successfully"
        
        invalid_data = self.sample_bike_data.copy()
        invalid_data['data_series']['absolute_timestamps'] = []
        
        result = self.fit_converter.convert_workout(invalid_data)
        assert result is None, "Should fail with invalid timestamps"
    
    def test_missing_data_handling(self):
        incomplete_data = self.sample_bike_data.copy()
        incomplete_data['data_series']['powers'] = [None, 150, None, 200]
        incomplete_data['data_series']['heart_rates'] = [140, None, 145, None]
        
        result = self.fit_converter.convert_workout(incomplete_data)
        assert result is not None, "Should handle missing data gracefully"
    
    def test_file_naming_convention(self):
        result = self.fit_converter.convert_workout(self.sample_bike_data)
        
        assert result is not None, "FIT file should be created"
        filename = os.path.basename(result)
        
        assert filename.startswith('bike_'), "Filename should start with workout type"
        assert filename.endswith('.fit'), "Filename should end with .fit"
        assert len(filename.split('_')) >= 3, "Filename should include timestamp"
    
    def test_empty_workout_data(self):
        empty_data = {}
        result = self.fit_converter.convert_workout(empty_data)
        assert result is None, "Should return None for empty data"
    
    def test_array_length_normalization(self):
        short_array = [1, 2, 3]
        result = self.fit_converter._ensure_array_exists(short_array, 5)
        assert len(result) == 5, "Should pad array to expected length"
        assert result[:3] == [1, 2, 3], "Should preserve original values"
        assert result[3:] == [None, None], "Should pad with None values"
        
        long_array = [1, 2, 3, 4, 5, 6, 7]
        result = self.fit_converter._ensure_array_exists(long_array, 5)
        assert len(result) == 5, "Should truncate array to expected length"
        assert result == [1, 2, 3, 4, 5], "Should keep first N values"
        
        empty_array = []
        result = self.fit_converter._ensure_array_exists(empty_array, 3)
        assert len(result) == 3, "Should create array of expected length"
        assert result == [None, None, None], "Should fill with None values"
    
    @patch('src.fit.fit_converter.FitFileBuilder')
    def test_fit_builder_exception_handling(self, mock_builder):
        mock_builder.side_effect = Exception("FIT builder error")
        
        result = self.fit_converter.convert_workout(self.sample_bike_data)
        assert result is None, "Should return None when FIT builder fails"
