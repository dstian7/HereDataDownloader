import unittest
from unittest.mock import Mock, MagicMock, patch, call
import os
import stat
import paramiko
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))
from sftp_downloader import SftpDownloader


class TestSftpDownloader(unittest.TestCase):
    """Test cases for SftpDownloader class"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.mock_ssh = Mock(spec=paramiko.SSHClient)
        self.mock_sftp = Mock(spec=paramiko.SFTPClient)
        self.mock_ssh.open_sftp.return_value = self.mock_sftp

    @patch('paramiko.SSHClient')
    def test_init_with_default_parameters(self, mock_ssh_class):
        """Test initialization with default parameters"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        downloader = SftpDownloader()

        mock_ssh_instance.set_missing_host_key_policy.assert_called_once()
        mock_ssh_instance.connect.assert_called_once_with(
            "kor-download.ext.here.com", 7222, "telenav", "GT2r7qTlRUadYM", timeout=5
        )
        mock_ssh_instance.open_sftp.assert_called_once()
        self.assertEqual(downloader.ssh, mock_ssh_instance)
        self.assertEqual(downloader.sftp, mock_sftp_instance)

    @patch('paramiko.SSHClient')
    def test_init_with_custom_parameters(self, mock_ssh_class):
        """Test initialization with custom parameters"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        downloader = SftpDownloader(
            sftp_host="custom.host.com",
            sftp_port=22,
            sftp_user="testuser",
            sftp_password="testpass"
        )

        mock_ssh_instance.connect.assert_called_once_with(
            "custom.host.com", 22, "testuser", "testpass", timeout=5
        )

    @patch('paramiko.SSHClient')
    def test_del_closes_connections(self, mock_ssh_class):
        """Test that __del__ closes SFTP and SSH connections"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        downloader = SftpDownloader()
        downloader.__del__()

        mock_sftp_instance.close.assert_called_once()
        mock_ssh_instance.close.assert_called_once()

    @patch('paramiko.SSHClient')
    def test_del_with_none_connections(self, mock_ssh_class):
        """Test __del__ when connections are None"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        downloader = SftpDownloader()
        downloader.sftp = None
        downloader.ssh = None

        # Should not raise any exception
        downloader.__del__()

    @patch('paramiko.SSHClient')
    def test_isdir_returns_true_for_directory(self, mock_ssh_class):
        """Test isdir returns True for a directory"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        mock_stat = Mock()
        mock_stat.st_mode = stat.S_IFDIR | 0o755
        mock_sftp_instance.stat.return_value = mock_stat

        downloader = SftpDownloader()
        result = downloader.isdir("/test/dir")

        self.assertTrue(result)
        mock_sftp_instance.stat.assert_called_once_with("/test/dir")

    @patch('paramiko.SSHClient')
    def test_isdir_returns_false_for_file(self, mock_ssh_class):
        """Test isdir returns False for a file"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        mock_stat = Mock()
        mock_stat.st_mode = stat.S_IFREG | 0o644
        mock_sftp_instance.stat.return_value = mock_stat

        downloader = SftpDownloader()
        result = downloader.isdir("/test/file.txt")

        self.assertFalse(result)

    @patch('paramiko.SSHClient')
    def test_isdir_returns_false_on_exception(self, mock_ssh_class):
        """Test isdir returns False when stat raises exception"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        mock_sftp_instance.stat.side_effect = IOError("File not found")

        downloader = SftpDownloader()
        result = downloader.isdir("/nonexistent/path")

        self.assertFalse(result)

    @patch('paramiko.SSHClient')
    @patch('logging.info')
    @patch('logging.error')
    def test_download_file_success(self, mock_log_error, mock_log_info, mock_ssh_class):
        """Test successful file download"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        downloader = SftpDownloader()
        downloader.download_file("/remote/path/file.txt", "/local/dest")

        mock_sftp_instance.get.assert_called_once_with(
            "/remote/path/file.txt", "/local/dest/file.txt"
        )
        mock_log_info.assert_called_once()
        mock_log_error.assert_not_called()

    @patch('paramiko.SSHClient')
    @patch('logging.info')
    @patch('logging.error')
    def test_download_file_with_ioerror(self, mock_log_error, mock_log_info, mock_ssh_class):
        """Test file download with IOError"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        mock_sftp_instance.get.side_effect = IOError("Connection error")

        downloader = SftpDownloader()
        downloader.download_file("/remote/path/file.txt", "/local/dest")

        mock_log_error.assert_called_once()
        mock_log_info.assert_called_once()

    @patch('paramiko.SSHClient')
    @patch('os.makedirs')
    def test_download_directory_creates_destination(self, mock_makedirs, mock_ssh_class):
        """Test that download_directory creates destination directory"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        mock_sftp_instance.listdir.return_value = []

        downloader = SftpDownloader()
        downloader.download_directory("/remote/dir", "/local/dest")

        mock_makedirs.assert_called_once_with("/local/dest", exist_ok=True)

    @patch('paramiko.SSHClient')
    @patch('os.makedirs')
    @patch('logging.info')
    def test_download_directory_with_files(self, mock_log_info, mock_makedirs, mock_ssh_class):
        """Test downloading directory with files"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        mock_sftp_instance.listdir.return_value = ["file1.txt", "file2.txt"]

        mock_stat1 = Mock()
        mock_stat1.st_mode = stat.S_IFREG | 0o644
        mock_stat2 = Mock()
        mock_stat2.st_mode = stat.S_IFREG | 0o644

        mock_sftp_instance.stat.side_effect = [mock_stat1, mock_stat2]

        downloader = SftpDownloader()
        downloader.download_directory("/remote/dir", "/local/dest")

        self.assertEqual(mock_sftp_instance.get.call_count, 2)

    @patch('paramiko.SSHClient')
    @patch('os.makedirs')
    def test_download_directory_recursive(self, mock_makedirs, mock_ssh_class):
        """Test recursive directory download"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        # First call returns a subdirectory and a file
        # Second call (for subdirectory) returns empty
        mock_sftp_instance.listdir.side_effect = [["subdir", "file.txt"], []]

        mock_stat_dir = Mock()
        mock_stat_dir.st_mode = stat.S_IFDIR | 0o755
        mock_stat_file = Mock()
        mock_stat_file.st_mode = stat.S_IFREG | 0o644

        mock_sftp_instance.stat.side_effect = [mock_stat_dir, mock_stat_file]

        downloader = SftpDownloader()
        downloader.download_directory("/remote/dir", "/local/dest")

        # Should create main directory and subdirectory
        self.assertEqual(mock_makedirs.call_count, 2)

    @patch('paramiko.SSHClient')
    @patch('os.makedirs')
    @patch('logging.info')
    def test_download_directory_with_mixed_content(self, mock_log_info, mock_makedirs, mock_ssh_class):
        """Test downloading directory with mixed files and subdirectories"""
        mock_ssh_instance = Mock()
        mock_sftp_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp_instance

        mock_sftp_instance.listdir.side_effect = [
            ["file1.txt", "subdir1", "file2.txt"],
            []  # subdir1 is empty
        ]

        mock_stat_file1 = Mock()
        mock_stat_file1.st_mode = stat.S_IFREG | 0o644
        mock_stat_dir = Mock()
        mock_stat_dir.st_mode = stat.S_IFDIR | 0o755
        mock_stat_file2 = Mock()
        mock_stat_file2.st_mode = stat.S_IFREG | 0o644

        mock_sftp_instance.stat.side_effect = [
            mock_stat_file1, mock_stat_dir, mock_stat_file2
        ]

        downloader = SftpDownloader()
        downloader.download_directory("/remote/dir", "/local/dest")

        # Should download 2 files
        self.assertEqual(mock_sftp_instance.get.call_count, 2)
        # Should create 2 directories (main and subdir1)
        self.assertEqual(mock_makedirs.call_count, 2)

    @patch('paramiko.SSHClient')
    def test_connection_timeout(self, mock_ssh_class):
        """Test connection with timeout"""
        mock_ssh_instance = Mock()
        mock_ssh_class.return_value = mock_ssh_instance
        mock_ssh_instance.connect.side_effect = paramiko.SSHException("Connection timeout")

        with self.assertRaises(paramiko.SSHException):
            downloader = SftpDownloader()


if __name__ == '__main__':
    unittest.main()