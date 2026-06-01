import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

from global_downloader import GlobalDownloader
from configparser import ConfigParser

class TestGlobalDownloader(unittest.TestCase):
    """Test cases for GlobalDownloader class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.region = "EU"
        self.quarterly_version = "22Q3"
        self.monthly_version = "22M06W1"
        self.config_dir = os.path.join(self.test_dir, "config")
        os.makedirs(self.config_dir)
        self.create_mock_config_files()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_mock_config_files(self):
        """Create mock configuration files for testing"""
        config = ConfigParser()
        config.add_section('GLOBAL')
        config.set('GLOBAL', 'local_path', self.test_dir)

        with open(os.path.join(self.config_dir, "data_path.cfg"), 'w') as f:
            config.write(f)

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_init_quarterly_version(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                                    mock_realpath, mock_dirname):
        """Test initialization with quarterly version"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.side_effect = lambda section, key: {
            ('GLOBAL', 'local_path'): '/local/path',
            ('GLOBAL', 's3_path'): '/s3/path',
            ('GLOBAL', 'doc_path'): '/doc/path'
        }[(section, key)]
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)

        self.assertEqual(downloader.region, self.region)
        self.assertEqual(downloader.version, self.quarterly_version)
        self.assertEqual(downloader.version_type, GlobalDownloader.VERSION_TYPE_QUARTERLY)
        self.assertEqual(downloader.config_file_name, "components_config.json")
        self.assertEqual(downloader.mode, "all")

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_init_monthly_version(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                                  mock_realpath, mock_dirname):
        """Test initialization with monthly version"""
        mock_is_month.return_value = True
        mock_is_quarter.return_value = False
        mock_config_instance = Mock()
        mock_config_instance.get.side_effect = lambda section, key: {
            ('GLOBAL', 'local_path'): '/local/path',
            ('GLOBAL', 's3_path'): '/s3/path',
            ('GLOBAL', 'doc_path'): '/doc/path'
        }[(section, key)]
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = GlobalDownloader(self.region, self.monthly_version, None, None)

        self.assertEqual(downloader.version_type, GlobalDownloader.VERSION_TYPE_MONTHLY)
        self.assertEqual(downloader.config_file_name, "components_config_monthly.json")

    @patch('global_downloader.DataChecker')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.sys.exit')
    @patch('global_downloader.logging')
    def test_init_invalid_version(self, mock_logging, mock_exit, mock_is_quarter, mock_is_month, mock_checker):
        """Test initialization with invalid version"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = False

        mock_exit.side_effect = SystemExit(-1)
        with self.assertRaises(SystemExit) as cm:
            GlobalDownloader(self.region, "INVALID", None, None)
        self.assertEqual(cm.exception.code, -1)
        mock_exit.assert_called_once_with(-1)

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_set_path(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                      mock_realpath, mock_dirname):
        """Test set_path method"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.side_effect = lambda section, key: {
            ('GLOBAL', 'local_path'): '/local/path',
            ('GLOBAL', 's3_path'): '/s3/path',
            ('GLOBAL', 'doc_path'): '/doc/path'
        }[(section, key)]
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)

        expected_vendor = f"{self.region}_HERE_{self.quarterly_version}"
        self.assertEqual(downloader.main_data_path, f"/local/path/{expected_vendor}")
        self.assertEqual(downloader.s3_data_path, f"/s3/path/{expected_vendor}")
        self.assertEqual(downloader.main_doc_path, f"/doc/path/{self.quarterly_version}")

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_start_quarterly(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                             mock_realpath, mock_dirname):
        """Test start method with quarterly version"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        downloader.start_quarterly = Mock()

        downloader.start()

        downloader.start_quarterly.assert_called_once()

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_start_monthly(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                           mock_realpath, mock_dirname):
        """Test start method with monthly version"""
        mock_is_month.return_value = True
        mock_is_quarter.return_value = False
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = GlobalDownloader(self.region, self.monthly_version, None, None)
        downloader.start_monthly = Mock()

        downloader.start()

        downloader.start_monthly.assert_called_once()

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.os.system')
    @patch('global_downloader.requests.post')
    @patch('global_downloader.requests.get')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_create_cygnus_data(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                                mock_get, mock_post, mock_system, mock_realpath, mock_dirname):
        """Test create_cygnus_data method"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_response = Mock()
        mock_response.content = json.dumps({}).encode()
        mock_get.return_value = mock_response

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        downloader.create_cygnus_data("TEST_COMPONENT")

        mock_post.assert_called_once()
        self.assertTrue(mock_system.called)

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.os.system')
    @patch('global_downloader.os.path.isdir')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_create_cygnus_data_link(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                                     mock_isdir, mock_system, mock_realpath, mock_dirname):
        """Test create_cygnus_data_link method"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_isdir.side_effect = [False, True]
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {
            "name": "test_component",
            "local_dir": "components/test"
        }

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        downloader.create_cygnus_data_link(component, "TEST_COMPONENT")

        mock_system.assert_called_once()

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.os.system')
    @patch('global_downloader.os.path.isdir')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_create_cygnus_data_link_skip_3rd_party_traffic(self, mock_config, mock_checker, mock_downloader,
                                                            mock_is_quarter, mock_is_month, mock_isdir, mock_system,
                                                            mock_realpath, mock_dirname):
        """Test create_cygnus_data_link skips 3rd party traffic location"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {
            "name": "traffic_location",
            "local_dir": "components/other_traffic"
        }

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        downloader.create_cygnus_data_link(component, "TEST_COMPONENT")

        mock_system.assert_not_called()

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.requests.put')
    @patch('global_downloader.requests.get')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_update_cygnus_data_status_released(self, mock_config, mock_checker, mock_downloader, mock_is_quarter,
                                                mock_is_month, mock_get, mock_put, mock_realpath, mock_dirname):
        """Test update_cygnus_data_status with released status"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_response = Mock()
        mock_response.content = json.dumps({
            "data": {"status": "in-progress"}
        }).encode()
        mock_get.return_value = mock_response

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        downloader.data_checker.main_result_info = {
            "cygnus_components": {
                "TEST_COMPONENT": [
                    {"status": "pass"}
                ]
            }
        }
        downloader.data_checker.CHECK_STATUS_PASS = "pass"
        downloader.data_checker.CHECK_STATUS_ERROR = "error"
        downloader.data_checker.CHECK_STATUS_NOT_READY = "not ready"
        downloader.data_checker.CHECK_STATUS_WARNING = "warning"

        downloader.update_cygnus_data_status("TEST_COMPONENT")

        self.assertTrue(mock_put.called)

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.requests.get')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_update_cygnus_data_status_skip_raw_rdf(self, mock_config, mock_checker, mock_downloader, mock_is_quarter,
                                                    mock_is_month, mock_get, mock_realpath, mock_dirname):
        """Test update_cygnus_data_status skips RAW-RDF+ component"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        downloader.data_checker.main_result_info = {"cygnus_components": {}}

        downloader.update_cygnus_data_status("RAW-RDF+")

        mock_get.assert_not_called()

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.get_version')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_download_quarterly_success(self, mock_config, mock_checker, mock_downloader_class, mock_is_quarter,
                                        mock_is_month, mock_get_version, mock_realpath, mock_dirname):
        """Test download_quarterly with successful download"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_get_version.return_value = ("2022.09", "S20221", "S20221_G")
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_downloader_instance = Mock()
        mock_downloader_instance.download_data.return_value = 1  # DOWNLOAD_STATUS_SUCCESS
        mock_downloader_class.return_value = mock_downloader_instance

        component = {
            "name": "test_component",
            "local_dir": "components/test",
            "here_product": "TEST_PRODUCT",
            "here_release": ["Release1"]
        }

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        with patch('global_downloader.os.system'):
            status = downloader.download_quarterly(component)

        self.assertEqual(status, 1)

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_download_quarterly_skipped_no_product(self, mock_config, mock_checker, mock_downloader,
                                                   mock_is_quarter, mock_is_month, mock_realpath, mock_dirname):
        """Test download_quarterly skips when no here_product"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_downloader.DOWNLOAD_STATUS_SKIPPED = 0
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {
            "name": "test_component",
            "local_dir": "components/test"
        }

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        status = downloader.download_quarterly(component)

        self.assertEqual(status, 0)  # DOWNLOAD_STATUS_SKIPPED

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.get_monthly_version')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_download_monthly_success(self, mock_config, mock_checker, mock_downloader_class, mock_is_quarter,
                                      mock_is_month, mock_get_monthly_version, mock_realpath, mock_dirname):
        """Test download_monthly with successful download"""
        mock_is_month.return_value = True
        mock_is_quarter.return_value = False
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_get_monthly_version.return_value = ("2022.06", "S20221_06")
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_downloader_instance = Mock()
        mock_downloader_instance.download_data.return_value = 1
        mock_downloader_class.return_value = mock_downloader_instance

        component = {
            "name": "test_component",
            "local_dir": "components/test",
            "here_product": "TEST_PRODUCT",
            "here_release": ["Release {v}"]
        }

        downloader = GlobalDownloader(self.region, self.monthly_version, None, None)
        with patch('global_downloader.os.system'):
            with patch('global_downloader.get_rdf_quarter', return_value=None):
                status = downloader.download_monthly(component)

        self.assertEqual(status, 1)

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.os.system')
    @patch('global_downloader.os.makedirs')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_download_monthly_reuse(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                                    mock_makedirs, mock_system, mock_realpath, mock_dirname):
        """Test download_monthly with reuse action"""
        mock_is_month.return_value = True
        mock_is_quarter.return_value = False
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {
            "name": "test_component",
            "local_dir": "components/test",
            "action": "reuse"
        }

        downloader = GlobalDownloader(self.region, self.monthly_version, None, None)
        downloader.get_reuse_version = Mock(return_value="22Q2")

        with patch('global_downloader.os.path.isdir', return_value=False):
            with patch('global_downloader.logging'):
                version = downloader.download_monthly(component)

        self.assertEqual(version, "22Q2")
        mock_system.assert_called()

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.get_base_quarter')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.ConfigParser')
    def test_get_reuse_version_default(self, mock_config, mock_downloader, mock_is_quarter, mock_is_month,
                                       mock_checker_class, mock_get_base_quarter, mock_realpath, mock_dirname):
        """Test get_reuse_version returns default version"""
        mock_is_month.return_value = True
        mock_is_quarter.return_value = False
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_get_base_quarter.return_value = "22Q2"
        mock_checker_class.component_ready.return_value = True
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {"name": "test_component"}

        downloader = GlobalDownloader(self.region, self.monthly_version, None, None)
        with patch('global_downloader.logging'):
            version = downloader.get_reuse_version(component)

        self.assertEqual(version, "22Q2")

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.post_process')
    @patch('global_downloader.os.chdir')
    @patch('global_downloader.os.makedirs')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_post_process(self, mock_config, mock_checker, mock_downloader, mock_is_quarter, mock_is_month,
                          mock_makedirs, mock_chdir, mock_post_process_module, mock_realpath, mock_dirname):
        """Test post_process method"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_method = Mock()
        mock_post_process_module.test_method = mock_method

        component = {
            "name": "test_component",
            "local_dir": "components/test",
            "post_process_method": "test_method"
        }

        downloader = GlobalDownloader(self.region, self.quarterly_version, None, None)
        with patch('global_downloader.logging'):
            downloader.post_process(component)

        mock_method.assert_called_once()

    @patch('global_downloader.logging')
    @patch('global_downloader.sys.exit')
    @patch('global_downloader.optparse.OptionParser')
    def test_main_missing_arguments(self, mock_parser, mock_exit, mock_logging):
        """Test main function with missing arguments"""
        mock_options = Mock()
        mock_options.region = None
        mock_options.version = None
        mock_options.cygnus_component = None
        mock_options.mode = None

        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = (mock_options, [])
        mock_parser.return_value = mock_parser_instance
        mock_exit.side_effect = SystemExit(-1)

        from global_downloader import main
        with self.assertRaises(SystemExit) as cm:
            main()

        mock_exit.assert_called_once_with(-1)

    @patch('global_downloader.GlobalDownloader')
    @patch('global_downloader.logging')
    @patch('global_downloader.optparse.OptionParser')
    def test_main_with_valid_arguments(self, mock_parser, mock_logging, mock_downloader_class):
        """Test main function with valid arguments"""
        mock_options = Mock()
        mock_options.region = "EU"
        mock_options.version = "22Q3"
        mock_options.cygnus_component = None
        mock_options.mode = None

        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = (mock_options, [])
        mock_parser.return_value = mock_parser_instance

        mock_downloader_instance = Mock()
        mock_downloader_class.return_value = mock_downloader_instance

        from global_downloader import main
        main()

        mock_downloader_instance.start.assert_called_once()

    @patch('global_downloader.json.load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('global_downloader.sys.exit')
    @patch('global_downloader.logging')
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_start_quarterly_invalid_region(self, mock_config, mock_checker, mock_downloader,
                                            mock_is_quarter, mock_is_month, mock_logging,
                                            mock_exit, mock_file, mock_json_load):
        """Test start_quarterly with invalid region"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_json_load.return_value = {"NA": {}}
        mock_exit.side_effect = SystemExit(-1)

        with self.assertRaises(SystemExit) as cm:
            downloader = GlobalDownloader("INVALID", self.quarterly_version, None, None)
            downloader.start_quarterly()

        mock_exit.assert_called_once_with(-1)

    @patch('global_downloader.os.path.dirname')
    @patch('global_downloader.os.path.realpath')
    @patch('global_downloader.os.system')
    @patch('global_downloader.json.load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('global_downloader.is_month')
    @patch('global_downloader.is_quarter')
    @patch('global_downloader.HttpDownloader')
    @patch('global_downloader.DataChecker')
    @patch('global_downloader.ConfigParser')
    def test_start_quarterly_with_component_filter(self, mock_config, mock_checker, mock_downloader, mock_is_quarter,
                                                   mock_is_month, mock_file, mock_json_load, mock_system,
                                                   mock_realpath, mock_dirname):
        """Test start_quarterly with specific component filter"""
        mock_is_month.return_value = False
        mock_is_quarter.return_value = True
        mock_config_instance = Mock()
        mock_config_instance.get.return_value = self.test_dir
        mock_config.return_value = mock_config_instance
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_json_load.return_value = {
            "EU": {
                "COMPONENT1": [{"name": "comp1"}],
                "COMPONENT2": [{"name": "comp2"}]
            }
        }

        mock_checker_instance = Mock()
        mock_checker_instance.is_component_downloaded.return_value = True
        mock_checker_instance.check_component.return_value = True
        mock_checker_instance.main_result_info = {"cygnus_components": {}}
        mock_checker.return_value = mock_checker_instance

        downloader = GlobalDownloader(self.region, self.quarterly_version, "COMPONENT1", None)
        downloader.create_cygnus_data = Mock()
        downloader.update_cygnus_data_status = Mock()

        downloader.start_quarterly()

        # Should only process COMPONENT1
        self.assertEqual(downloader.create_cygnus_data.call_count, 1)


if __name__ == '__main__':
    unittest.main()