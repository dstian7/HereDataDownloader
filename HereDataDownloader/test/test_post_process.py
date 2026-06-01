import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

from post_process import (
    extract_landmark,
    extract_speed_camera,
    extract_speed_pattern,
    extract_junction,
    extract_gjv,
    extract_postal_code,
    extract_postal_address,
    package_eu_traffic_location,
    extract_and_remove_tar_files,
    extract_and_remove_zip_files,
)


class TestPostProcess(unittest.TestCase):
    """Test cases for post_process.py functions"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
        self.doc_dir = os.path.join(self.test_dir, "docs")
        os.makedirs(self.doc_dir, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        os.chdir(self.original_dir)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('post_process.os.system')
    @patch('post_process.extract_and_remove_tar_files')
    def test_extract_landmark(self, mock_extract_tar, mock_system):
        """Test extract_landmark function"""
        extract_landmark(self.doc_dir)

        mock_extract_tar.assert_called_once()
        expected_cmd = "mv *.pdf {}/;mv *.csv {}/;mv *.xlsx {}/".format(
            self.doc_dir, self.doc_dir, self.doc_dir
        )
        mock_system.assert_called_once_with(expected_cmd)

    @patch('post_process.os.system')
    @patch('post_process.extract_and_remove_tar_files')
    def test_extract_speed_camera(self, mock_extract_tar, mock_system):
        """Test extract_speed_camera function"""
        extract_speed_camera(self.doc_dir)

        mock_extract_tar.assert_called_once()
        self.assertEqual(mock_system.call_count, 2)
        mock_system.assert_any_call("mv *.pdf {}/".format(self.doc_dir))
        mock_system.assert_any_call("rm -rf DOCUMENTATION;rm Release*")

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    @patch('post_process.os.path.isdir')
    @patch('post_process.extract_and_remove_zip_files')
    @patch('post_process.extract_and_remove_tar_files')
    def test_extract_speed_pattern(self, mock_extract_tar, mock_extract_zip,
                                   mock_isdir, mock_listdir, mock_system):
        """Test extract_speed_pattern function"""
        mock_listdir.side_effect = [
            ['dir1', 'file.txt'],  # First call
            ['dir2', 'file2.txt']  # Second call
        ]
        mock_isdir.return_value = True

        extract_speed_pattern(self.doc_dir)

        mock_extract_tar.assert_called_once()
        mock_extract_zip.assert_called_once()
        self.assertTrue(mock_system.call_count > 0)

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_junction(self, mock_listdir, mock_system):
        """Test extract_junction function"""
        mock_listdir.return_value = ['file1.tar', 'file2.txt', 'file3.tar']

        extract_junction(self.doc_dir)

        # Should process 2 tar files
        self.assertEqual(mock_system.call_count, 4)  # 2 tar files * 2 commands each

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_junction_no_tar_files(self, mock_listdir, mock_system):
        """Test extract_junction with no tar files"""
        mock_listdir.return_value = ['file1.txt', 'file2.pdf']

        extract_junction(self.doc_dir)

        mock_system.assert_not_called()

    @patch('post_process.os.system')
    @patch('post_process.os.makedirs')
    @patch('post_process.os.listdir')
    @patch('post_process.extract_junction')
    def test_extract_gjv(self, mock_extract_junction, mock_listdir,
                         mock_makedirs, mock_system):
        """Test extract_gjv function"""
        mock_listdir.return_value = ['file1.tar', 'file2.txt']

        extract_gjv(self.doc_dir)

        mock_extract_junction.assert_called_once_with(self.doc_dir)
        mock_makedirs.assert_called_once_with("../../GJV", exist_ok=True)
        self.assertEqual(mock_system.call_count, 2)  # 1 tar file * 2 commands

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    @patch('post_process.extract_and_remove_tar_files')
    def test_extract_postal_code(self, mock_extract_tar, mock_listdir, mock_system):
        """Test extract_postal_code function"""
        mock_listdir.side_effect = [
            ['file1.zip', 'file2.txt'],  # First call for zip files
            ['AB_CD_file.txt', 'EF_GH_file2.txt']  # Second call for txt files
        ]

        extract_postal_code(self.doc_dir)

        mock_extract_tar.assert_called_once()
        self.assertTrue(mock_system.call_count > 0)

    @patch('post_process.os.system')
    @patch('post_process.extract_and_remove_zip_files')
    @patch('post_process.extract_and_remove_tar_files')
    def test_extract_postal_address(self, mock_extract_tar, mock_extract_zip, mock_system):
        """Test extract_postal_address function"""
        extract_postal_address(self.doc_dir)

        mock_extract_tar.assert_called_once()
        mock_extract_zip.assert_called_once()
        mock_system.assert_called_once_with("mv *.pdf {}".format(self.doc_dir))

    @patch('post_process.time.strftime')
    @patch('post_process.time.localtime')
    @patch('post_process.os.system')
    @patch('post_process.os.mkdir')
    @patch('post_process.os.chdir')
    @patch('post_process.os.path.isdir')
    @patch('post_process.os.listdir')
    @patch('post_process.extract_and_remove_tar_files')
    def test_package_eu_traffic_location(self, mock_extract_tar, mock_listdir,
                                         mock_isdir, mock_chdir, mock_mkdir,
                                         mock_system, mock_localtime, mock_strftime):
        """Test package_eu_traffic_location function"""
        doc_dir = "/path/to/data/folder1/folder2/folder3/folder4/folder5/Q1_2023/docs"
        mock_listdir.side_effect = [
            ['folder1', 'file.tar'],  # Initial folder list
            [],  # Inside folder1
            [],  # After moving to package
            []  # Inside package for Slovakia check
        ]
        mock_isdir.side_effect = [True, False, False]
        mock_strftime.return_value = "20230101"

        package_eu_traffic_location(doc_dir)

        mock_extract_tar.assert_called()
        mock_mkdir.assert_called_once()
        self.assertTrue(mock_system.call_count > 0)

    @patch('post_process.time.strftime')
    @patch('post_process.os.system')
    @patch('post_process.os.mkdir')
    @patch('post_process.os.chdir')
    @patch('post_process.os.path.isdir')
    @patch('post_process.os.listdir')
    @patch('post_process.extract_and_remove_tar_files')
    def test_package_eu_traffic_location_with_slovakia(self, mock_extract_tar,
                                                       mock_listdir, mock_isdir,
                                                       mock_chdir, mock_mkdir,
                                                       mock_system, mock_strftime):
        """Test package_eu_traffic_location with Slovakia folder"""
        doc_dir = "/path/to/data/folder1/folder2/folder3/folder4/folder5/Q1_2023/docs"
        mock_listdir.side_effect = [
            ['Slovakia'],  # Inside package - has Slovakia
            ['data.zip']  # Inside Slovakia folder
        ]
        mock_isdir.side_effect = [True, True, True]
        mock_strftime.return_value = "20230101"

        package_eu_traffic_location(doc_dir)

        self.assertTrue(mock_system.call_count > 0)

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_and_remove_tar_files(self, mock_listdir, mock_system):
        """Test extract_and_remove_tar_files function"""
        mock_listdir.return_value = ['file1.tar', 'file2.txt', 'file3.tar']

        extract_and_remove_tar_files()

        self.assertEqual(mock_system.call_count, 2)
        mock_system.assert_any_call("tar -xvf 'file1.tar';rm 'file1.tar'")
        mock_system.assert_any_call("tar -xvf 'file3.tar';rm 'file3.tar'")

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_and_remove_tar_files_no_tar(self, mock_listdir, mock_system):
        """Test extract_and_remove_tar_files with no tar files"""
        mock_listdir.return_value = ['file1.txt', 'file2.pdf']

        extract_and_remove_tar_files()

        mock_system.assert_not_called()

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_and_remove_zip_files(self, mock_listdir, mock_system):
        """Test extract_and_remove_zip_files function"""
        mock_listdir.return_value = ['file1.zip', 'file2.txt', 'file3.zip']

        extract_and_remove_zip_files()

        self.assertEqual(mock_system.call_count, 2)
        mock_system.assert_any_call("unzip 'file1.zip';rm 'file1.zip'")
        mock_system.assert_any_call("unzip 'file3.zip';rm 'file3.zip'")

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_and_remove_zip_files_no_zip(self, mock_listdir, mock_system):
        """Test extract_and_remove_zip_files with no zip files"""
        mock_listdir.return_value = ['file1.txt', 'file2.tar']

        extract_and_remove_zip_files()

        mock_system.assert_not_called()

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_and_remove_tar_files_with_special_chars(self, mock_listdir, mock_system):
        """Test extract_and_remove_tar_files with special characters in filename"""
        mock_listdir.return_value = ["file with spaces.tar", "file'quote.tar"]

        extract_and_remove_tar_files()

        self.assertEqual(mock_system.call_count, 2)

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_and_remove_zip_files_with_special_chars(self, mock_listdir, mock_system):
        """Test extract_and_remove_zip_files with special characters in filename"""
        mock_listdir.return_value = ["file with spaces.zip", "file'quote.zip"]

        extract_and_remove_zip_files()

        self.assertEqual(mock_system.call_count, 2)

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    def test_extract_postal_code_empty_directory(self, mock_listdir, mock_system):
        """Test extract_postal_code with empty directory"""
        mock_listdir.side_effect = [[], []]

        with patch('post_process.extract_and_remove_tar_files'):
            extract_postal_code(self.doc_dir)

        # Should still call the mv commands even with empty directory
        self.assertTrue(mock_system.call_count > 0)

    @patch('post_process.os.system')
    @patch('post_process.os.listdir')
    @patch('post_process.extract_and_remove_tar_files')
    def test_extract_postal_code_file_rename(self, mock_extract_tar, mock_listdir, mock_system):
        """Test extract_postal_code file renaming logic"""
        mock_listdir.side_effect = [
            [],  # First call for zip files
            ['AB_CD_EF_file.txt', 'GH_IJ_KL_data.txt']  # Second call for txt files
        ]

        extract_postal_code(self.doc_dir)

        # Verify file renaming commands are called
        self.assertTrue(any('mv' in str(call) for call in mock_system.call_args_list))


if __name__ == '__main__':
    unittest.main()