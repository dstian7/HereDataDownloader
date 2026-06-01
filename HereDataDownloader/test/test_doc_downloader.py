import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, mock_open, call
from configparser import ConfigParser
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

# Import the class to test
from doc_downloader import DocDownloader, main


class TestDocDownloader(unittest.TestCase):
    """Test cases for DocDownloader class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_quarter = "22Q3"
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)

        # Create mock config files
        self.create_mock_config_files()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_mock_config_files(self):
        """Create mock configuration files for testing"""
        # Create doc_config.json
        doc_config = {
            "release_note": [
                {
                    "here_product": "Product1",
                    "here_release": "Release1",
                    "local_dir": "release_notes"
                }
            ],
            "ctrg": {
                "here_product": "CTRG_Product",
                "here_release": "CTRG_Release",
                "local_dir": "ctrg"
            },
            "tnm": {
                "here_product": "TNM_Product",
                "here_release": "TNM_Release",
                "local_dir": "tnm"
            },
            "product_available_dates": {
                "here_product": "PAD_Product",
                "local_dir": "pad"
            }
        }

        with open(os.path.join(self.config_dir, "doc_config.json"), 'w') as f:
            json.dump(doc_config, f)

        # Create data_path.cfg
        config = ConfigParser()
        config.add_section('GLOBAL')
        config.set('GLOBAL', 'doc_path', self.temp_dir)

        with open(os.path.join(self.config_dir, "data_path.cfg"), 'w') as f:
            config.write(f)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    def test_init(self, mock_realpath, mock_dirname, mock_get_version):
        """Test DocDownloader initialization"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        downloader = DocDownloader(self.test_quarter)

        self.assertEqual(downloader.quarter, self.test_quarter)
        self.assertEqual(downloader.doc_version, "add_v1")
        self.assertEqual(downloader.doc_full_version, "add_full_v1")
        self.assertIsNotNone(downloader.config_dict)
        mock_get_version.assert_called_once_with(self.test_quarter)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    def test_set_path(self, mock_realpath, mock_dirname, mock_get_version):
        """Test set_path method"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        downloader = DocDownloader(self.test_quarter)

        self.assertEqual(downloader.main_doc_path, self.temp_dir)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.DocDownloader.download_ctrg')
    @patch('doc_downloader.DocDownloader.download_release_notes')
    @patch('doc_downloader.DocDownloader.download_tnm')
    @patch('doc_downloader.DocDownloader.download_product_available_dates')
    def test_start(self, mock_pad, mock_tnm, mock_release, mock_ctrg,
                   mock_realpath, mock_dirname, mock_get_version):
        """Test start method calls all download methods"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        downloader = DocDownloader(self.test_quarter)
        downloader.start()

        mock_ctrg.assert_called_once()
        mock_release.assert_called_once()
        mock_tnm.assert_called_once()
        mock_pad.assert_called_once()

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.version_config_generator.get_normal_file_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.os.makedirs')
    @patch('doc_downloader.os.chdir')
    @patch('doc_downloader.os.popen')
    @patch('doc_downloader.logging')
    def test_download_release_notes_skip_existing(self, mock_logging, mock_popen,
                                                  mock_chdir, mock_makedirs,
                                                  mock_realpath, mock_dirname,
                                                  mock_file_version, mock_get_version):
        """Test download_release_notes skips when files exist"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")
        mock_file_version.return_value = "file_v1"

        # Mock popen to return 2 files found
        mock_popen_obj = Mock()
        mock_popen_obj.read.return_value.strip.return_value = "2"
        mock_popen.return_value = mock_popen_obj

        downloader = DocDownloader(self.test_quarter)
        downloader.download_release_notes()

        mock_logging.info.assert_called()

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.os.system')
    @patch('doc_downloader.os.listdir')
    def test_post_release_notes_download(self, mock_listdir, mock_system,
                                         mock_realpath, mock_dirname, mock_get_version):
        """Test __post_release_notes_download static method"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        mock_listdir.return_value = ["file_v1.tar", "other.tar"]

        with patch('doc_downloader.os.path.isdir', return_value=True):
            DocDownloader._DocDownloader__post_release_notes_download("file_v1", "/test/dir")

        self.assertTrue(mock_system.called)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.os.makedirs')
    @patch('doc_downloader.os.listdir')
    @patch('doc_downloader.logging')
    def test_download_ctrg_skip_existing(self, mock_logging, mock_listdir,
                                         mock_makedirs, mock_realpath,
                                         mock_dirname, mock_get_version):
        """Test download_ctrg skips when files exist"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")
        mock_listdir.return_value = ["file" + str(i) for i in range(15)]

        downloader = DocDownloader(self.test_quarter)
        downloader.download_ctrg()

        mock_logging.info.assert_called_with("CTRG exists, skip download")

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.os.makedirs')
    @patch('doc_downloader.os.listdir')
    @patch('doc_downloader.os.chdir')
    @patch('doc_downloader.os.system')
    @patch('doc_downloader.HttpDownloader')
    def test_download_ctrg_success(self, mock_http, mock_system, mock_chdir,
                                   mock_listdir, mock_makedirs, mock_realpath,
                                   mock_dirname, mock_get_version):
        """Test download_ctrg successful download"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")
        mock_listdir.return_value = ["file1"]

        downloader = DocDownloader(self.test_quarter)
        mock_downloader = Mock()
        mock_downloader.download_data.return_value = 1  # DOWNLOAD_STATUS_SUCCESS
        mock_http.DOWNLOAD_STATUS_SUCCESS = 1
        downloader.downloader = mock_downloader

        downloader.download_ctrg()

        mock_downloader.download_data.assert_called_once()
        self.assertTrue(mock_system.called)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.DocDownloader.create_cygnus_tnm_node')
    @patch('doc_downloader.os.makedirs')
    @patch('doc_downloader.os.listdir')
    @patch('doc_downloader.os.system')
    @patch('doc_downloader.os.chdir')
    @patch('doc_downloader.summarize_tnm')
    def test_download_tnm_success(self, mock_summarize, mock_chdir, mock_system,
                                  mock_listdir, mock_makedirs, mock_create_node,
                                  mock_realpath, mock_dirname, mock_get_version):
        """Test download_tnm successful download"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        # Mock directory structure
        mock_listdir.side_effect = [
            ["TNM-1", "TNM-2"],  # First call for tnm_dir
            [],  # Second call for latest_folder check
            ["file.pdf"]  # Third call for file listing
        ]

        with patch('doc_downloader.os.path.join', side_effect=os.path.join):
            downloader = DocDownloader(self.test_quarter)
            mock_downloader = Mock()
            mock_downloader.download_data.return_value = 1  # SUCCESS
            downloader.downloader = mock_downloader

            downloader.download_tnm()

            mock_create_node.assert_called_once()

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.requests.get')
    @patch('doc_downloader.requests.post')
    @patch('doc_downloader.requests.put')
    @patch('doc_downloader.requests.head')
    def test_create_cygnus_tnm_node(self, mock_head, mock_put, mock_post,
                                    mock_get, mock_realpath, mock_dirname,
                                    mock_get_version):
        """Test create_cygnus_tnm_node method"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        # Mock response without data
        mock_response = Mock()
        mock_response.content = json.dumps({"status": "not_found"}).encode()
        mock_get.return_value = mock_response

        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head.return_value = mock_head_response

        downloader = DocDownloader(self.test_quarter)
        downloader.create_cygnus_tnm_node()

        # Should be called for each region
        self.assertEqual(mock_get.call_count, 11)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.version_config_generator.get_last_quarter_split')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.os.chdir')
    @patch('doc_downloader.os.system')
    def test_download_product_available_dates(self, mock_system, mock_chdir,
                                              mock_realpath, mock_dirname,
                                              mock_quarter_split, mock_get_version):
        """Test download_product_available_dates method"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")
        mock_quarter_split.return_value = (22, 3)

        downloader = DocDownloader(self.test_quarter)
        mock_downloader = Mock()
        mock_downloader.download_data.return_value = 1  # SUCCESS
        downloader.downloader = mock_downloader

        downloader.download_product_available_dates()

        mock_downloader.download_data.assert_called_once()
        mock_quarter_split.assert_called_once_with(self.test_quarter)

    @patch('doc_downloader.logging.basicConfig')
    @patch('doc_downloader.optparse.OptionParser')
    @patch('doc_downloader.DocDownloader')
    @patch('doc_downloader.sys.exit')
    def test_main_no_version(self, mock_exit, mock_downloader_class,
                             mock_parser_class, mock_logging):
        """Test main function without version argument"""
        mock_parser = Mock()
        mock_options = Mock()
        mock_options.version = None
        mock_parser.parse_args.return_value = (mock_options, [])
        mock_parser_class.return_value = mock_parser

        main()

        mock_exit.assert_called_once_with(-1)

    @patch('doc_downloader.logging.basicConfig')
    @patch('doc_downloader.optparse.OptionParser')
    @patch('doc_downloader.DocDownloader')
    def test_main_with_version(self, mock_downloader_class, mock_parser_class,
                               mock_logging):
        """Test main function with version argument"""
        mock_parser = Mock()
        mock_options = Mock()
        mock_options.version = "22Q3"
        mock_parser.parse_args.return_value = (mock_options, [])
        mock_parser_class.return_value = mock_parser

        mock_downloader = Mock()
        mock_downloader_class.return_value = mock_downloader

        main()

        mock_downloader_class.assert_called_once_with("22Q3")
        mock_downloader.start.assert_called_once()

    @patch('doc_downloader.sys.exit')
    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    def test_init_with_invalid_config(self, mock_realpath, mock_dirname,
                                      mock_get_version, mock_exit):
        """Test initialization with invalid config file"""
        mock_realpath.return_value = "/invalid/path"
        mock_dirname.return_value = "/invalid/path"
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        mock_exit.side_effect = SystemExit(-1)
        with self.assertRaises(SystemExit) as cm:
            DocDownloader(self.test_quarter)
        self.assertEqual(cm.exception.code, -1)
        mock_exit.assert_called_once_with(-1)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    @patch('doc_downloader.os.makedirs')
    @patch('doc_downloader.os.listdir')
    def test_download_ctrg_edge_case_exactly_10_files(self, mock_listdir,
                                                      mock_makedirs, mock_realpath,
                                                      mock_dirname, mock_get_version):
        """Test download_ctrg with exactly 10 files (boundary condition)"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")
        mock_listdir.return_value = ["file" + str(i) for i in range(10)]

        downloader = DocDownloader(self.test_quarter)
        downloader.download_ctrg()

        # Should skip download with exactly 10 files
        self.assertEqual(mock_listdir.call_count, 1)

    @patch('doc_downloader.version_config_generator.get_version')
    @patch('doc_downloader.os.path.dirname')
    @patch('doc_downloader.os.path.realpath')
    def test_config_dict_structure(self, mock_realpath, mock_dirname,
                                   mock_get_version):
        """Test that config_dict has expected structure"""
        mock_realpath.return_value = self.temp_dir
        mock_dirname.return_value = self.temp_dir
        mock_get_version.return_value = ("rdf_v1", "add_v1", "add_full_v1")

        downloader = DocDownloader(self.test_quarter)

        self.assertIn("release_note", downloader.config_dict)
        self.assertIn("ctrg", downloader.config_dict)
        self.assertIn("tnm", downloader.config_dict)
        self.assertIn("product_available_dates", downloader.config_dict)


if __name__ == '__main__':
    unittest.main()
