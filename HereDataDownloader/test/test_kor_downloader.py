import os
import sys
import json
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import tempfile
import shutil
from configparser import ConfigParser
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

# Import the class to test
from kor_downloader import KORDownloader, main


class TestKORDownloader(unittest.TestCase):
    """Test cases for KORDownloader class"""

    def setUp(self):
        """Set up test fixtures"""
        self.quarter = "22Q3"
        self.cygnus_component = None
        self.mode = None
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, "config")
        config = ConfigParser()
        config.add_section('GLOBAL')
        config.set('GLOBAL', 'local_path', self.test_dir)
        os.makedirs(self.config_dir)
        with open(os.path.join(self.config_dir, "data_path.cfg"), 'w') as f:
            config.write(f)

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_init(self, mock_config_parser, mock_sftp, mock_realpath, mock_dirname):
        """Test KORDownloader initialization"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): '/tmp/local',
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, self.cygnus_component, self.mode)

        self.assertEqual(downloader.region, "KOR")
        self.assertEqual(downloader.quarter, "22Q3")
        self.assertEqual(downloader.vendor, "KOR_HERE_22Q3")
        self.assertIsNotNone(downloader.downloader)
        self.assertEqual(downloader.cygnus_component, None)
        self.assertEqual(downloader.mode, None)

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_init_with_component_and_mode(self, mock_config_parser, mock_sftp, mock_realpath, mock_dirname):
        """Test KORDownloader initialization with component and mode"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): '/tmp/local',
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader("23Q1", "TOLLCOST", "check")

        self.assertEqual(downloader.quarter, "23Q1")
        self.assertEqual(downloader.cygnus_component, "TOLLCOST")
        self.assertEqual(downloader.mode, "check")

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_set_path(self, mock_config_parser, mock_sftp, mock_realpath, mock_dirname):
        """Test set_path method"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): '/data/local',
            ('KOR', 's3_path'): 's3://test-bucket'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, None)

        self.assertEqual(downloader.main_data_path, '/data/local/KOR_HERE_22Q3')
        self.assertEqual(downloader.main_backup_path, 's3://test-bucket/KOR_HERE_22Q3')

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.version_config_generator.get_quarter_split')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    @patch('sys.exit')
    def test_download_packages_not_ready(self, mock_exit, mock_config_parser, mock_sftp, mock_quarter_split,
                                         mock_realpath, mock_dirname):
        """Test download_packages when data is not ready"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): '/tmp/local',
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_quarter_split.return_value = (2022, 3)
        mock_sftp_instance = Mock()
        mock_sftp_instance.isdir.return_value = False
        mock_sftp.return_value = mock_sftp_instance

        downloader = KORDownloader(self.quarter, None, None)
        downloader.download_packages()

        mock_exit.assert_called_once_with(0)

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.version_config_generator.get_quarter_split')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_download_packages_success(self, mock_config_parser, mock_sftp, mock_quarter_split,
                                       mock_realpath, mock_dirname):
        """Test download_packages when data is ready"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): '/tmp/local',
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_quarter_split.return_value = (2022, 3)
        mock_sftp_instance = Mock()
        mock_sftp_instance.isdir.return_value = True
        mock_sftp.return_value = mock_sftp_instance

        downloader = KORDownloader(self.quarter, None, None)
        downloader.download_packages()

        self.assertEqual(mock_sftp_instance.download_directory.call_count, 2)

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('os.system')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_backup_packages(self, mock_config_parser, mock_sftp, mock_system, mock_realpath, mock_dirname):
        """Test backup_packages method"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): '/tmp/local',
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, None)
        downloader.backup_packages()

        expected_cmd = "aws s3 sync /tmp/local/KOR_HERE_22Q3 s3://bucket/path/KOR_HERE_22Q3"
        mock_system.assert_called_once_with(expected_cmd)

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('os.makedirs')
    @patch('os.system')
    @patch('os.listdir')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_move_zip_file(self, mock_config_parser, mock_sftp, mock_listdir, mock_system, mock_makedirs,
                           mock_realpath, mock_dirname):
        """Test move_zip_file method"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_listdir.return_value = ['test_file.zip', 'other_file.txt']

        component = {
            "name": "TestComponent",
            "zip_name": "test_file",
            "local_dir": "test_dir"
        }

        downloader = KORDownloader(self.quarter, None, None)
        downloader.move_zip_file(component)

        mock_makedirs.assert_called()
        self.assertTrue(mock_system.call_count >= 1)

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.post_process_kor')
    @patch('os.chdir')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_post_process_with_method(self, mock_config_parser, mock_sftp, mock_chdir, mock_post_process,
                                      mock_realpath, mock_dirname):
        """Test post_process method when post_process_method exists"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_method = Mock()
        mock_post_process.extract_kor_zip = mock_method

        component = {
            "name": "TestComponent",
            "local_dir": "test_dir",
            "post_process_method": "extract_kor_zip"
        }

        downloader = KORDownloader(self.quarter, None, None)
        downloader.post_process(component)

        mock_method.assert_called_once()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_post_process_without_method(self, mock_config_parser, mock_sftp, mock_realpath, mock_dirname):
        """Test post_process method when post_process_method doesn't exist"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {
            "name": "TestComponent",
            "local_dir": "test_dir"
        }

        downloader = KORDownloader(self.quarter, None, None)
        # Should not raise exception
        downloader.post_process(component)

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('os.makedirs')
    @patch('os.system')
    @patch('kor_downloader.requests')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_create_cygnus_data_new(self, mock_config_parser, mock_sftp, mock_requests, mock_system, mock_makedirs,
                                    mock_realpath, mock_dirname):
        """Test create_cygnus_data when data doesn't exist"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_response = Mock()
        mock_response.content = json.dumps({}).encode()
        mock_requests.get.return_value = mock_response

        downloader = KORDownloader(self.quarter, None, None)
        downloader.create_cygnus_data("TESTCOMPONENT")

        mock_requests.post.assert_called_once()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('os.makedirs')
    @patch('os.system')
    @patch('kor_downloader.requests')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_create_cygnus_data_existing(self, mock_config_parser, mock_sftp, mock_requests, mock_system,
                                         mock_makedirs, mock_realpath, mock_dirname):
        """Test create_cygnus_data when data already exists"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf

        mock_response = Mock()
        mock_response.content = json.dumps({"data": {"status": "released"}}).encode()
        mock_requests.get.return_value = mock_response
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, None)
        downloader.create_cygnus_data("TESTCOMPONENT")

        mock_requests.post.assert_not_called()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('os.path.getsize')
    @patch('os.listdir')
    @patch('os.system')
    @patch('kor_downloader.requests')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_create_tollcost_data(self, mock_config_parser, mock_sftp, mock_requests, mock_system, mock_listdir,
                                  mock_getsize, mock_realpath, mock_dirname):
        """Test create_tollcost_data method"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf

        mock_response = Mock()
        mock_response.content = json.dumps({}).encode()
        mock_requests.get.return_value = mock_response
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_listdir.return_value = ['tollcost_data.zip']
        mock_getsize.return_value = 1024

        tollcost_config = {
            "s3_dir": "s3://test-bucket",
            "zip_name": "tollcost"
        }

        downloader = KORDownloader(self.quarter, None, None)
        downloader.create_tollcost_data(tollcost_config)

        mock_requests.post.assert_called_once()
        mock_requests.put.assert_called_once()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('os.path.isdir')
    @patch('os.system')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_create_cygnus_data_link_tollcost(self, mock_config_parser, mock_sftp, mock_system, mock_isdir,
                                              mock_realpath, mock_dirname):
        """Test create_cygnus_data_link for TOLLCOST component"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {"local_dir": "test_dir"}

        downloader = KORDownloader(self.quarter, None, None)
        downloader.create_cygnus_data_link(component, "TOLLCOST")

        mock_system.assert_not_called()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('os.path.isdir')
    @patch('os.system')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_create_cygnus_data_link_non_tollcost(self, mock_config_parser, mock_sftp, mock_system, mock_isdir,
                                                  mock_realpath, mock_dirname):
        """Test create_cygnus_data_link for non-TOLLCOST component"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf

        mock_isdir.side_effect = [False, True]
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        component = {"local_dir": "test_dir"}

        downloader = KORDownloader(self.quarter, None, None)
        downloader.create_cygnus_data_link(component, "TESTCOMPONENT")

        mock_system.assert_called_once()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.requests')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_update_cygnus_data_status_raw_rdf_plus(self, mock_config_parser, mock_sftp, mock_requests,
                                                    mock_realpath, mock_dirname):
        """Test update_cygnus_data_status for RAW-RDF+ component"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, None)
        downloader.data_checker = Mock()
        downloader.data_checker.main_result_info = {"cygnus_components": {}}

        downloader.update_cygnus_data_status("RAW-RDF+")

        mock_requests.put.assert_not_called()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.requests')
    @patch('kor_downloader.DataChecker')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_update_cygnus_data_status_error(self, mock_config_parser, mock_sftp, mock_data_checker, mock_requests,
                                             mock_realpath, mock_dirname):
        """Test update_cygnus_data_status with error status"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_get_response = Mock()
        mock_get_response.content = json.dumps({
            "data": {"status": "in-progress"}
        }).encode()
        mock_requests.get.return_value = mock_get_response

        downloader = KORDownloader(self.quarter, None, None)
        downloader.data_checker = Mock()
        downloader.data_checker.CHECK_STATUS_ERROR = "error"
        downloader.data_checker.main_result_info = {
            "cygnus_components": {
                "TESTCOMPONENT": [{"status": "error"}]
            }
        }

        downloader.update_cygnus_data_status("TESTCOMPONENT")

        mock_requests.put.assert_called()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.requests')
    @patch('kor_downloader.DataChecker')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_update_cygnus_data_status_no_data(self, mock_config_parser, mock_sftp, mock_data_checker, mock_requests,
                                               mock_realpath, mock_dirname):
        """Test update_cygnus_data_status when data doesn't exist"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        mock_get_response = Mock()
        mock_get_response.content = json.dumps({}).encode()
        mock_requests.get.return_value = mock_get_response

        downloader = KORDownloader(self.quarter, None, None)
        downloader.data_checker = Mock()
        downloader.data_checker.main_result_info = {
            "cygnus_components": {"TESTCOMPONENT": []}
        }

        downloader.update_cygnus_data_status("TESTCOMPONENT")

        mock_requests.put.assert_not_called()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.KORDownloader.process_data')
    @patch('kor_downloader.KORDownloader.backup_packages')
    @patch('kor_downloader.KORDownloader.download_packages')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_start(self, mock_config_parser, mock_sftp, mock_download, mock_backup, mock_process,
                   mock_realpath, mock_dirname):
        """Test start method"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, None)
        downloader.start()

        mock_download.assert_called_once()
        mock_backup.assert_called_once()
        mock_process.assert_called_once()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.KORDownloader.process_data')
    @patch('kor_downloader.KORDownloader.backup_packages')
    @patch('kor_downloader.KORDownloader.download_packages')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_start_check_mode_skips_download_and_backup(self, mock_config_parser, mock_sftp, mock_download, mock_backup,
                                                       mock_process, mock_realpath, mock_dirname):
        """In check mode, start should skip download and backup but still process."""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, "check")
        downloader.start()

        mock_download.assert_not_called()
        mock_backup.assert_not_called()
        mock_process.assert_called_once()

    @patch('sys.exit')
    @patch('sys.argv', ['kor_downloader.py'])
    @patch('kor_downloader.logging')
    def test_main_no_quarter(self, mock_logging, mock_exit):
        """Test main function without quarter parameter"""
        mock_exit.side_effect = SystemExit(-1)
        with self.assertRaises(SystemExit) as cm:
            main()
            main()
        mock_exit.assert_called_with(-1)

    @patch('kor_downloader.KORDownloader')
    @patch('sys.argv', ['kor_downloader.py', '-q', '22Q3'])
    def test_main_with_quarter(self, mock_downloader_class):
        """Test main function with quarter parameter"""
        mock_instance = Mock()
        mock_downloader_class.return_value = mock_instance

        main()

        mock_downloader_class.assert_called_once_with('22Q3', None, None)
        mock_instance.start.assert_called_once()

    @patch('kor_downloader.KORDownloader')
    @patch('sys.argv', ['kor_downloader.py', '-q', '22Q3', '-c', 'TOLLCOST', '-m', 'check'])
    def test_main_with_all_parameters(self, mock_downloader_class):
        """Test main function with all parameters"""
        mock_instance = Mock()
        mock_downloader_class.return_value = mock_instance

        main()

        mock_downloader_class.assert_called_once_with('22Q3', 'TOLLCOST', 'check')
        mock_instance.start.assert_called_once()

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_history_file_name(self, mock_config_parser, mock_sftp, mock_realpath, mock_dirname):
        """Test history file name is set correctly"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, None)

        self.assertEqual(downloader.history_file_name, ".download_history")

    @patch('kor_downloader.os.path.dirname')
    @patch('kor_downloader.os.path.realpath')
    @patch('kor_downloader.SftpDownloader')
    @patch('kor_downloader.ConfigParser')
    def test_cygnus_data_api_url(self, mock_config_parser, mock_sftp, mock_realpath, mock_dirname):
        """Test Cygnus data API URL is set correctly"""
        mock_conf = Mock()
        mock_conf.get.side_effect = lambda section, key: {
            ('KOR', 'local_path'): self.test_dir,
            ('KOR', 's3_path'): 's3://bucket/path'
        }.get((section, key))
        mock_config_parser.return_value = mock_conf
        mock_realpath.return_value = self.test_dir
        mock_dirname.return_value = self.test_dir

        downloader = KORDownloader(self.quarter, None, None)

        self.assertEqual(downloader.cygnus_data_api_url, "http://cygnus.telenav.com/api/data")


if __name__ == '__main__':
    unittest.main()