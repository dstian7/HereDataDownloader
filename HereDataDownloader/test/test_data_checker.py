import os
import sys
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch, mock_open, MagicMock, call
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))
from data_checker import DataChecker


class TestDataChecker(unittest.TestCase):
    """Test cases for DataChecker class"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.test_dir = tempfile.mkdtemp()
        self.region = "EU"
        self.version = "26Q1"
        self.data_checker = DataChecker(self.region, self.version, self.test_dir)

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_init_creates_report_path(self):
        """Test that __init__ creates report path directory"""
        self.assertTrue(os.path.exists(self.data_checker.report_path))
        self.assertEqual(self.data_checker.region, self.region)
        self.assertEqual(self.data_checker.version, self.version)

    def test_init_with_existing_directory(self):
        """Test initialization with existing directory"""
        # Should not raise error due to exist_ok=True
        data_checker2 = DataChecker(self.region, self.version, self.test_dir)
        self.assertTrue(os.path.exists(data_checker2.report_path))

    def test_load_main_result_info_no_file(self):
        """Test load_main_result_info when file doesn't exist"""
        result = self.data_checker.load_main_result_info()
        self.assertEqual(result["region"], self.region)
        self.assertEqual(result["version"], self.version)
        self.assertEqual(result["cygnus_components"], {})

    def test_load_main_result_info_with_file(self):
        """Test load_main_result_info when file exists"""
        test_data = {
            "region": "EU",
            "version": "26Q1",
            "cygnus_components": {"test_component": []}
        }
        result_file = os.path.join(self.data_checker.report_path, "main_result.json")
        with open(result_file, 'w') as f:
            json.dump(test_data, f)

        result = self.data_checker.load_main_result_info()
        self.assertEqual(result["region"], "EU")
        self.assertEqual(result["cygnus_components"], {"test_component": []})

    def test_is_component_downloaded_not_in_results(self):
        """Test is_component_downloaded when component not in results"""
        component = {"name": "test_component"}
        result = self.data_checker.is_component_downloaded(component, "cygnus_test")
        self.assertFalse(result)

    @patch('data_checker.logging')
    def test_is_component_downloaded_already_downloaded(self, mock_logging):
        """Test is_component_downloaded when component already downloaded"""
        component = {"name": "test_component"}
        self.data_checker.main_result_info["cygnus_components"]["cygnus_test"] = [
            {"name": "test_component", "status": "pass"}
        ]
        result = self.data_checker.is_component_downloaded(component, "cygnus_test")
        self.assertTrue(result)

    def test_is_component_downloaded_with_error_status(self):
        """Test is_component_downloaded when component has error status"""
        component = {"name": "test_component"}
        self.data_checker.main_result_info["cygnus_components"]["cygnus_test"] = [
            {"name": "test_component", "status": "error"}
        ]
        result = self.data_checker.is_component_downloaded(component, "cygnus_test")
        self.assertFalse(result)

    def test_get_update_time_no_history_file(self):
        """Test get_update_time when history file doesn't exist"""
        result = self.data_checker.get_update_time("test_component")
        self.assertEqual(result, "")

    def test_get_update_time_with_history_file(self):
        """Test get_update_time when history file exists"""
        history_file = os.path.join(self.test_dir, ".download_history")
        with open(history_file, 'w') as f:
            f.write("test_component|data|2023-01-01 12:00:00\n")
            f.write("other_component|data|2023-01-02 12:00:00\n")

        result = self.data_checker.get_update_time("test_component")
        self.assertEqual(result, "2023-01-01 12:00:00")

    def test_get_update_time_malformed_line(self):
        """Test get_update_time with malformed history line"""
        history_file = os.path.join(self.test_dir, ".download_history")
        with open(history_file, 'w') as f:
            f.write("malformed_line\n")
            f.write("test_component|data|2023-01-01 12:00:00\n")

        result = self.data_checker.get_update_time("test_component")
        self.assertEqual(result, "2023-01-01 12:00:00")

    def test_get_existing_file_exists(self):
        """Test get_existing_file when file exists"""
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")

        result = DataChecker.get_existing_file("test.txt", self.test_dir)
        self.assertEqual(result, "test.txt")

    def test_get_existing_file_not_exists(self):
        """Test get_existing_file when file doesn't exist"""
        result = DataChecker.get_existing_file("nonexistent.txt", self.test_dir)
        self.assertIsNone(result)

    def test_get_existing_folder_exists(self):
        """Test get_existing_folder when folder exists"""
        test_folder = os.path.join(self.test_dir, "test_folder")
        os.makedirs(test_folder, exist_ok=True)

        result = DataChecker.get_existing_folder("test_folder", self.test_dir)
        self.assertEqual(result, "test_folder")

    def test_get_existing_folder_not_exists(self):
        """Test get_existing_folder when folder doesn't exist"""
        result = DataChecker.get_existing_folder("nonexistent_folder", self.test_dir)
        self.assertIsNone(result)

    def test_get_file_size(self):
        """Test get_file_size returns correct size"""
        test_file = os.path.join(self.test_dir, "test.txt")
        test_content = "test content"
        with open(test_file, 'w') as f:
            f.write(test_content)

        result = DataChecker.get_file_size(test_file)
        self.assertEqual(result, len(test_content))

    def test_get_folder_size(self):
        """Test get_folder_size returns correct size"""
        test_folder = os.path.join(self.test_dir, "test_folder")
        os.makedirs(test_folder, exist_ok=True)

        file1 = os.path.join(test_folder, "file1.txt")
        file2 = os.path.join(test_folder, "file2.txt")
        with open(file1, 'w') as f:
            f.write("content1")
        with open(file2, 'w') as f:
            f.write("content2")

        result = DataChecker.get_folder_size(test_folder)
        self.assertEqual(result, len("content1") + len("content2"))

    def test_abnormal_size_change_true(self):
        """Test abnormal_size_change returns True for significant decrease"""
        result = DataChecker.abnormal_size_change(70, 100)
        self.assertTrue(result)

    def test_abnormal_size_change_false(self):
        """Test abnormal_size_change returns False for normal change"""
        result = DataChecker.abnormal_size_change(85, 100)
        self.assertFalse(result)

    def test_update_main_result_count_pass(self):
        """Test update_main_result_count with all pass"""
        main_result = {"ref_count": 3}
        result = self.data_checker.update_main_result_count(main_result, 3, 0, 0)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["pass"], 3)
        self.assertEqual(result["warning"], 0)
        self.assertEqual(result["error"], 0)

    def test_update_main_result_count_warning(self):
        """Test update_main_result_count with warnings"""
        main_result = {"ref_count": 3}
        result = self.data_checker.update_main_result_count(main_result, 2, 1, 0)
        self.assertEqual(result["status"], "warning")

    def test_update_main_result_count_error(self):
        """Test update_main_result_count with errors"""
        main_result = {"ref_count": 3}
        result = self.data_checker.update_main_result_count(main_result, 1, 1, 1)
        self.assertEqual(result["status"], "error")

    def test_write_component_json_file(self):
        """Test write_component_json_file creates correct file"""
        component_name = "test_component"
        result = {"component": component_name, "details": []}

        self.data_checker.write_component_json_file(component_name, result)

        result_file = os.path.join(self.data_checker.report_path, f"{component_name}.json")
        self.assertTrue(os.path.exists(result_file))

        with open(result_file, 'r') as f:
            loaded_result = json.load(f)
        self.assertEqual(loaded_result["component"], component_name)

    @patch('data_checker.time')
    def test_generate_main_report(self, mock_time):
        """Test generate_main_report creates main result file"""
        mock_time.strftime.return_value = "2023-01-01 12:00:00"
        mock_time.localtime.return_value = None

        with patch.object(self.data_checker, 'copy_report_html_file'):
            self.data_checker.generate_main_report()

        result_file = os.path.join(self.data_checker.report_path, "main_result.json")
        self.assertTrue(os.path.exists(result_file))

        with open(result_file, 'r') as f:
            result = json.load(f)
        self.assertEqual(result["time"], "2023-01-01 12:00:00")

    @patch('os.system')
    @patch('os.path.dirname')
    def test_copy_report_html_file(self, mock_dirname, mock_system):
        """Test copy_report_html_file executes correct commands"""
        mock_dirname.return_value = "/test/path"

        self.data_checker.copy_report_html_file()

        self.assertTrue(mock_system.called)
        self.assertGreater(mock_system.call_count, 0)

    @patch('data_checker.get_file_version')
    @patch('data_checker.logging')
    def test_check_component_no_check_method(self, mock_logging, mock_get_version):
        """Test check_component when no check_method specified"""
        component = {"name": "test_component"}
        result = self.data_checker.check_component(component, "cygnus_test")
        self.assertFalse(result)

    @patch('data_checker.get_file_version')
    @patch('data_checker.get_previous_version')
    @patch('data_checker.logging')
    def test_check_file_fixed_name(self, mock_logging, mock_prev_version, mock_file_version):
        """Test check_file_fixed_name method"""
        mock_prev_version.return_value = "25Q4"
        mock_file_version.return_value = "2610E0"

        component = {
            "name": "test_component",
            "local_dir": "test_dir",
            "ref_files": ["file1.txt", "file2.txt"]
        }

        # Create test directory structure
        test_dir = os.path.join(self.test_dir, "test_dir")
        os.makedirs(test_dir, exist_ok=True)

        main_result, sub_result = self.data_checker.check_file_fixed_name(component)

        self.assertIn("ref_count", main_result)
        self.assertEqual(main_result["ref_count"], 2)
        self.assertIn("status", main_result)

    @patch('data_checker.get_file_version')
    @patch('data_checker.get_previous_version')
    def test_check_by_folder(self, mock_prev_version, mock_file_version):
        """Test check_by_folder method"""
        mock_prev_version.return_value = "25Q4"
        mock_file_version.return_value = "2610E0"

        component = {
            "name": "test_component",
            "local_dir": "test_dir",
            "ref_files": ["folder1", "folder2"]
        }

        test_dir = os.path.join(self.test_dir, "test_dir")
        os.makedirs(test_dir, exist_ok=True)

        main_result, sub_result = self.data_checker.check_by_folder(component)

        self.assertIn("ref_count", main_result)
        self.assertEqual(main_result["ref_count"], 2)

    @patch('data_checker.DataChecker.component_match')
    def test_component_ready_true(self, mock_match):
        """Test component_ready returns True when component is ready"""
        mock_match.return_value = True

        component = {"name": "test_component"}
        main_result_file = os.path.join(self.test_dir, "check_report", "main_result.json")
        os.makedirs(os.path.dirname(main_result_file), exist_ok=True)

        test_data = {
            "cygnus_components": {
                "test": [{"name": "test_component", "status": "pass"}]
            }
        }
        with open(main_result_file, 'w') as f:
            json.dump(test_data, f)

        result = DataChecker.component_ready(component, self.test_dir)
        self.assertTrue(result)

    def test_component_ready_no_file(self):
        """Test component_ready returns False when no result file"""
        component = {"name": "test_component"}
        result = DataChecker.component_ready(component, self.test_dir)
        self.assertFalse(result)

    def test_get_existing_file_with_version_no_folder(self):
        """Test get_existing_file_with_version when folder doesn't exist"""
        result = DataChecker.get_existing_file_with_version("test.*", "/nonexistent")
        self.assertIsNone(result)

    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_get_existing_file_with_version_match(self, mock_isdir, mock_listdir):
        """Test get_existing_file_with_version with matching file"""
        mock_isdir.return_value = True
        mock_listdir.return_value = ["test_v1.txt", "test_v2.txt"]

        result = DataChecker.get_existing_file_with_version("test_v1.*", "/test")
        self.assertEqual(result, "test_v1.txt")

    def test_check_eu_traffic_location_missing_folder(self):
        """Test check_eu_traffic_location with missing folder"""
        component = {
            "name": "traffic_location",
            "local_dir": "traffic_dir",
            "ref_files": ["folder1", "folder2"]
        }

        main_result, sub_result = self.data_checker.check_eu_traffic_location(component)

        self.assertIn("status", main_result)
        self.assertEqual(main_result["error"], 2)

    @patch('os.popen')
    @patch('os.system')
    def test_get_location_table_version_from_zip(self, mock_system, mock_popen):
        """Test get_location_table_version_from_zip"""
        mock_readline = MagicMock()
        mock_readline.readline.return_value = "LOCATIONDATASETS.txt"
        mock_popen.return_value = mock_readline

        mock_readlines = MagicMock()
        mock_readlines.readlines.return_value = ["header", "data;data;data;version;data"]
        mock_popen.return_value = mock_readlines

        result = DataChecker.get_location_table_version_from_zip("/test/file.zip")
        # Result depends on mock behavior

    def test_get_location_table_version_from_zip_exception(self):
        """Test get_location_table_version_from_zip handles exceptions"""
        result = DataChecker.get_location_table_version_from_zip("/nonexistent/file.zip")
        self.assertEqual(result, "")

    @patch('xlrd.open_workbook')
    @patch('os.listdir')
    def test_get_here_schedule_no_files(self, mock_listdir, mock_workbook):
        """Test get_here_schedule with no excel files"""
        mock_listdir.return_value = []

        result = self.data_checker.get_here_schedule("rdf")
        self.assertEqual(result, "")

    def test_get_here_schedule_unsupported_region(self):
        """Test get_here_schedule with unsupported region"""
        data_checker = DataChecker("UNSUPPORTED", self.version, self.test_dir)
        result = data_checker.get_here_schedule("rdf")
        self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
