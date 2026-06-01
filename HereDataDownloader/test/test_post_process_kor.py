import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, call, MagicMock
import zipfile
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

from post_process_kor import (
    extract_kor_zip,
    extract_kor_speed_camera,
    extract_and_remove_zip_files,
    remove_sub_directory,
    rename_kor_landmark_package,
    rename_kor_jv_package,
)


class TestPostProcessKor(unittest.TestCase):
    """Test suite for post_process_kor module functions."""

    def setUp(self):
        """Set up temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up temporary directory after each test."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_zip_file(self, filename, content_files=None):
        """Helper method to create a zip file with optional content."""
        zip_path = os.path.join(self.test_dir, filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            if content_files:
                for content_file in content_files:
                    zipf.writestr(content_file, f"content of {content_file}")
        return zip_path

    def test_extract_and_remove_zip_files_single_zip(self):
        """Test extracting and removing a single zip file."""
        self._create_zip_file("test.zip", ["file1.txt", "file2.txt"])

        with patch('os.system') as mock_system:
            extract_and_remove_zip_files()
            mock_system.assert_called_once_with("unzip 'test.zip';rm 'test.zip'")

    def test_extract_and_remove_zip_files_multiple_zips(self):
        """Test extracting and removing multiple zip files."""
        self._create_zip_file("test1.zip", ["file1.txt"])
        self._create_zip_file("test2.zip", ["file2.txt"])

        with patch('os.system') as mock_system:
            extract_and_remove_zip_files()
            # Check that system was called twice
            self.assertEqual(mock_system.call_count, 2)
            calls = [call[0][0] for call in mock_system.call_args_list]
            self.assertIn("unzip 'test1.zip';rm 'test1.zip'", calls)
            self.assertIn("unzip 'test2.zip';rm 'test2.zip'", calls)

    def test_extract_and_remove_zip_files_no_zips(self):
        """Test when no zip files are present."""
        # Create a non-zip file
        with open("test.txt", "w") as f:
            f.write("test content")

        with patch('os.system') as mock_system:
            extract_and_remove_zip_files()
            mock_system.assert_not_called()

    def test_extract_and_remove_zip_files_empty_directory(self):
        """Test with empty directory."""
        with patch('os.system') as mock_system:
            extract_and_remove_zip_files()
            mock_system.assert_not_called()

    def test_remove_sub_directory_single_directory(self):
        """Test removing a single subdirectory."""
        subdir = os.path.join(self.test_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)

        with patch('os.system') as mock_system:
            with patch('os.rmdir') as mock_rmdir:
                remove_sub_directory()
                mock_system.assert_called_once_with("mv subdir/* ./")
                mock_rmdir.assert_called_once_with("subdir")

    def test_remove_sub_directory_multiple_directories(self):
        """Test removing multiple subdirectories."""
        os.makedirs(os.path.join(self.test_dir, "subdir1"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "subdir2"), exist_ok=True)

        with patch('os.system') as mock_system:
            with patch('os.rmdir') as mock_rmdir:
                remove_sub_directory()
                self.assertEqual(mock_system.call_count, 2)
                self.assertEqual(mock_rmdir.call_count, 2)

    def test_remove_sub_directory_no_directories(self):
        """Test when no subdirectories are present."""
        with open("test.txt", "w") as f:
            f.write("test content")

        with patch('os.system') as mock_system:
            with patch('os.rmdir') as mock_rmdir:
                remove_sub_directory()
                mock_system.assert_not_called()
                mock_rmdir.assert_not_called()

    def test_remove_sub_directory_mixed_files_and_dirs(self):
        """Test with both files and directories present."""
        os.makedirs(os.path.join(self.test_dir, "subdir"), exist_ok=True)
        with open("test.txt", "w") as f:
            f.write("test content")

        with patch('os.system') as mock_system:
            with patch('os.rmdir') as mock_rmdir:
                remove_sub_directory()
                mock_system.assert_called_once_with("mv subdir/* ./")
                mock_rmdir.assert_called_once_with("subdir")

    def test_rename_kor_landmark_package_single_zip(self):
        """Test renaming a single zip file to KOR.zip."""
        self._create_zip_file("original.zip")

        with patch('os.system') as mock_system:
            rename_kor_landmark_package()
            mock_system.assert_called_once_with("mv original.zip KOR.zip")

    def test_rename_kor_landmark_package_multiple_zips(self):
        """Test renaming when multiple zip files exist."""
        self._create_zip_file("file1.zip")
        self._create_zip_file("file2.zip")

        with patch('os.system') as mock_system:
            rename_kor_landmark_package()
            # Should rename all zip files to KOR.zip (last one wins)
            self.assertEqual(mock_system.call_count, 2)

    def test_rename_kor_landmark_package_no_zips(self):
        """Test when no zip files are present."""
        with open("test.txt", "w") as f:
            f.write("test content")

        with patch('os.system') as mock_system:
            rename_kor_landmark_package()
            mock_system.assert_not_called()

    def test_rename_kor_jv_package_single_zip(self):
        """Test renaming a single zip file to KOR_JV.zip."""
        self._create_zip_file("original.zip")

        with patch('os.system') as mock_system:
            rename_kor_jv_package()
            mock_system.assert_called_once_with("mv original.zip KOR_JV.zip")

    def test_rename_kor_jv_package_multiple_zips(self):
        """Test renaming when multiple zip files exist."""
        self._create_zip_file("file1.zip")
        self._create_zip_file("file2.zip")

        with patch('os.system') as mock_system:
            rename_kor_jv_package()
            self.assertEqual(mock_system.call_count, 2)

    def test_rename_kor_jv_package_no_zips(self):
        """Test when no zip files are present."""
        with open("test.txt", "w") as f:
            f.write("test content")

        with patch('os.system') as mock_system:
            rename_kor_jv_package()
            mock_system.assert_not_called()

    @patch('post_process_kor.remove_sub_directory')
    @patch('post_process_kor.extract_and_remove_zip_files')
    def test_extract_kor_zip(self, mock_extract, mock_remove):
        """Test extract_kor_zip calls the correct functions."""
        extract_kor_zip()
        mock_extract.assert_called_once()
        mock_remove.assert_called_once()

    @patch('post_process_kor.remove_sub_directory')
    @patch('post_process_kor.extract_kor_zip')
    def test_extract_kor_speed_camera(self, mock_extract_zip, mock_remove):
        """Test extract_kor_speed_camera calls the correct functions."""
        extract_kor_speed_camera()
        mock_extract_zip.assert_called_once()
        mock_remove.assert_called_once()

    def test_extract_and_remove_zip_files_special_characters(self):
        """Test handling zip files with special characters in names."""
        self._create_zip_file("test file.zip")

        with patch('os.system') as mock_system:
            extract_and_remove_zip_files()
            mock_system.assert_called_once_with("unzip 'test file.zip';rm 'test file.zip'")

    def test_remove_sub_directory_special_characters(self):
        """Test handling directories with special characters."""
        subdir = os.path.join(self.test_dir, "sub dir")
        os.makedirs(subdir, exist_ok=True)

        with patch('os.system') as mock_system:
            with patch('os.rmdir') as mock_rmdir:
                remove_sub_directory()
                mock_system.assert_called_once_with("mv sub dir/* ./")
                mock_rmdir.assert_called_once_with("sub dir")

    def test_rename_kor_landmark_package_already_named(self):
        """Test renaming when file is already named KOR.zip."""
        self._create_zip_file("KOR.zip")

        with patch('os.system') as mock_system:
            rename_kor_landmark_package()
            mock_system.assert_called_once_with("mv KOR.zip KOR.zip")

    def test_rename_kor_jv_package_already_named(self):
        """Test renaming when file is already named KOR_JV.zip."""
        self._create_zip_file("KOR_JV.zip")

        with patch('os.system') as mock_system:
            rename_kor_jv_package()
            mock_system.assert_called_once_with("mv KOR_JV.zip KOR_JV.zip")


if __name__ == '__main__':
    unittest.main()