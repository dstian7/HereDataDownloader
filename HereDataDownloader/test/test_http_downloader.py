import os
import sys
import unittest
from unittest.mock import Mock, MagicMock, patch, mock_open, call
import tempfile
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

from http_downloader import HttpDownloader


class TestHttpDownloader(unittest.TestCase):
    """Test cases for HttpDownloader class"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.downloader = HttpDownloader()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test method"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if self.downloader.session:
            self.downloader.session.close()

    def test_init(self):
        """Test HttpDownloader initialization"""
        downloader = HttpDownloader()
        self.assertIsNone(downloader.session)
        self.assertIsNone(downloader.home_page)
        self.assertEqual(downloader.product_name, "")
        self.assertIsNone(downloader.product_page)
        self.assertIsNone(downloader.product_page_previous_releases)
        self.assertIsNone(downloader.release_page)

    def test_init_removes_proxy_env_vars(self):
        """Test that initialization removes proxy environment variables"""
        os.environ['https_proxy'] = 'http://proxy.example.com'
        os.environ['http_proxy'] = 'http://proxy.example.com'
        downloader = HttpDownloader()
        self.assertNotIn('https_proxy', os.environ)
        self.assertNotIn('http_proxy', os.environ)

    @patch('http_downloader.requests.Session')
    @patch('http_downloader.BeautifulSoup')
    def test_switch_to_product_success(self, mock_bs, mock_session):
        """Test successful product switch"""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_post_response = Mock()
        mock_post_response.text = '<html></html>'
        mock_session_instance.post.return_value = mock_post_response

        mock_product_item = MagicMock()
        mock_product_item.__getitem__.return_value = 'product_link'
        mock_bs_instance = Mock()
        mock_bs_instance.find.return_value = mock_product_item
        mock_bs.return_value = mock_bs_instance

        result = self.downloader.switch_to_product('TestProduct')

        self.assertTrue(result)
        self.assertEqual(self.downloader.product_name, 'TestProduct')
        self.assertIsNotNone(self.downloader.session)

    @patch('http_downloader.requests.Session')
    @patch('http_downloader.BeautifulSoup')
    def test_switch_to_product_not_found(self, mock_bs, mock_session):
        """Test product switch when product not found"""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_post_response = Mock()
        mock_post_response.text = '<html></html>'
        mock_session_instance.post.return_value = mock_post_response

        mock_bs_instance = Mock()
        mock_bs_instance.find.return_value = None
        mock_bs.return_value = mock_bs_instance

        result = self.downloader.switch_to_product('NonExistentProduct')

        self.assertFalse(result)

    @patch('http_downloader.requests.Session')
    @patch('http_downloader.BeautifulSoup')
    def test_switch_to_release_success(self, mock_bs, mock_session):
        """Test successful release switch"""
        # Setup mock session
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        self.downloader.session = mock_session_instance

        # Setup mock product pages
        self.downloader.product_page = Mock()
        self.downloader.product_page.text = '<html></html>'
        self.downloader.product_page_previous_releases = Mock()
        self.downloader.product_page_previous_releases.text = '<html></html>'

        # Setup mock BeautifulSoup structure
        mock_td_version = Mock()
        mock_td_version.string = 'v1.0'

        mock_a_release = MagicMock()
        mock_a_release.string = 'Release_Name_Test'
        mock_a_release.__getitem__.return_value = 'release_link'

        mock_td_release = Mock()
        mock_td_release.a = mock_a_release

        mock_tr = Mock()
        mock_tr.find_all.return_value = [mock_td_version, mock_td_release, Mock()]

        mock_tbody = Mock()
        mock_tbody.tr = mock_tr

        mock_table = Mock()
        mock_table.find_all.return_value = [mock_tbody]

        mock_bs_instance = Mock()
        mock_bs_instance.find.return_value = mock_table
        mock_bs.return_value = mock_bs_instance

        result = self.downloader.switch_to_release('Release_Name', 'v1.0')

        self.assertTrue(result)
        self.assertIsNotNone(self.downloader.release_page)

    @patch('http_downloader.requests.Session')
    @patch('http_downloader.BeautifulSoup')
    def test_switch_to_release_not_found(self, mock_bs, mock_session):
        """Test release switch when release not found"""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        self.downloader.session = mock_session_instance

        self.downloader.product_page = Mock()
        self.downloader.product_page.text = '<html></html>'
        self.downloader.product_page_previous_releases = Mock()
        self.downloader.product_page_previous_releases.text = '<html></html>'

        mock_table = Mock()
        mock_table.find_all.return_value = []

        mock_bs_instance = Mock()
        mock_bs_instance.find.return_value = mock_table
        mock_bs.return_value = mock_bs_instance

        result = self.downloader.switch_to_release('NonExistent', 'v1.0')

        self.assertFalse(result)

    @patch('http_downloader.os.system')
    @patch('http_downloader.BeautifulSoup')
    def test_download_from_release_success(self, mock_bs, mock_system):
        """Test successful download from release"""
        self.downloader.release_page = Mock()
        self.downloader.release_page.text = '<html></html>'

        # Setup mock file structure
        mock_download_link = MagicMock()
        mock_download_link.string = 'test_file.zip'
        mock_download_link.__getitem__.return_value = 'http://example.com/file.zip'

        mock_th = Mock()
        mock_th.string = 'MD5 Signature'
        mock_td = Mock()
        mock_td.string = 'd41d8cd98f00b204e9800998ecf8427e'
        mock_tr = Mock()
        mock_tr.find.side_effect = [mock_th, mock_td]

        mock_feat_table = Mock()
        mock_feat_table.findAll.return_value = [mock_tr]

        mock_file_container = Mock()
        mock_file_container.find.side_effect = [mock_download_link, mock_feat_table]

        mock_bs_instance = Mock()
        mock_bs_instance.findAll.return_value = [mock_file_container]
        mock_bs.return_value = mock_bs_instance

        with patch.object(self.downloader, 'check_md5', return_value=True):
            result = self.downloader.download_from_release(self.test_dir)

        self.assertEqual(result, HttpDownloader.DOWNLOAD_STATUS_SUCCESS)

    @patch('http_downloader.os.system')
    @patch('http_downloader.BeautifulSoup')
    def test_download_from_release_creates_directory(self, mock_bs, mock_system):
        """Test that download creates directory if it doesn't exist"""
        new_dir = os.path.join(self.test_dir, 'new_subdir')
        self.assertFalse(os.path.exists(new_dir))

        self.downloader.release_page = Mock()
        self.downloader.release_page.text = '<html></html>'

        mock_bs_instance = Mock()
        mock_bs_instance.findAll.return_value = []
        mock_bs.return_value = mock_bs_instance

        result = self.downloader.download_from_release(new_dir)

        self.assertTrue(os.path.exists(new_dir))

    @patch('http_downloader.os.system')
    @patch('http_downloader.BeautifulSoup')
    def test_download_from_release_md5_mismatch(self, mock_bs, mock_system):
        """Test download failure due to MD5 mismatch"""
        self.downloader.release_page = Mock()
        self.downloader.release_page.text = '<html></html>'

        mock_download_link = MagicMock()
        mock_download_link.string = 'test_file.zip'
        mock_download_link.__getitem__.return_value = 'http://example.com/file.zip'

        mock_th = Mock()
        mock_th.string = 'MD5 Signature'
        mock_td = Mock()
        mock_td.string = 'd41d8cd98f00b204e9800998ecf8427e'
        mock_tr = Mock()
        mock_tr.find.side_effect = [mock_th, mock_td]

        mock_feat_table = Mock()
        mock_feat_table.findAll.return_value = [mock_tr]

        mock_file_container = Mock()
        mock_file_container.find.side_effect = [mock_download_link, mock_feat_table]

        mock_bs_instance = Mock()
        mock_bs_instance.findAll.return_value = [mock_file_container]
        mock_bs.return_value = mock_bs_instance

        with patch.object(self.downloader, 'check_md5', side_effect=[False, False]):
            result = self.downloader.download_from_release(self.test_dir)

        self.assertEqual(result, HttpDownloader.DOWNLOAD_STATUS_ERROR)

    @patch('http_downloader.os.system')
    @patch('http_downloader.BeautifulSoup')
    def test_download_from_release_skip_existing(self, mock_bs, mock_system):
        """Test that existing files with matching MD5 are skipped"""
        self.downloader.release_page = Mock()
        self.downloader.release_page.text = '<html></html>'

        mock_download_link = MagicMock()
        mock_download_link.string = 'test_file.zip'
        mock_download_link.__getitem__.return_value = 'http://example.com/file.zip'

        mock_th = Mock()
        mock_th.string = 'MD5 Signature'
        mock_td = Mock()
        mock_td.string = 'd41d8cd98f00b204e9800998ecf8427e'
        mock_tr = Mock()
        mock_tr.find.side_effect = [mock_th, mock_td]

        mock_feat_table = Mock()
        mock_feat_table.findAll.return_value = [mock_tr]

        mock_file_container = Mock()
        mock_file_container.find.side_effect = [mock_download_link, mock_feat_table]

        mock_bs_instance = Mock()
        mock_bs_instance.findAll.return_value = [mock_file_container]
        mock_bs.return_value = mock_bs_instance

        with patch.object(self.downloader, 'check_md5', return_value=True):
            result = self.downloader.download_from_release(self.test_dir)

        mock_system.assert_not_called()
        self.assertEqual(result, HttpDownloader.DOWNLOAD_STATUS_SUCCESS)

    def test_check_md5_match(self):
        """Test MD5 check with matching hash"""
        with patch.object(self.downloader, 'get_md5', return_value='abc123'):
            result = self.downloader.check_md5('test_file', 'abc123')
        self.assertTrue(result)

    def test_check_md5_mismatch(self):
        """Test MD5 check with non-matching hash"""
        with patch.object(self.downloader, 'get_md5', return_value='abc123'):
            result = self.downloader.check_md5('test_file', 'def456')
        self.assertFalse(result)

    @patch('http_downloader.os.popen')
    @patch('http_downloader.os.path.isdir')
    def test_get_md5_file(self, mock_isdir, mock_popen):
        """Test get_md5 for a file"""
        mock_isdir.return_value = False
        mock_output = Mock()
        mock_output.read.return_value = 'd41d8cd98f00b204e9800998ecf8427e  test_file'
        mock_popen.return_value = mock_output

        result = HttpDownloader.get_md5('test_file')

        self.assertEqual(result, 'd41d8cd98f00b204e9800998ecf8427e')
        mock_popen.assert_called_once_with("md5sum 'test_file'")

    @patch('http_downloader.os.popen')
    @patch('http_downloader.os.path.isdir')
    def test_get_md5_directory(self, mock_isdir, mock_popen):
        """Test get_md5 for a directory"""
        mock_isdir.return_value = True
        mock_output = Mock()
        mock_output.read.return_value = 'd41d8cd98f00b204e9800998ecf8427e  -'
        mock_popen.return_value = mock_output

        result = HttpDownloader.get_md5('test_dir')

        self.assertEqual(result, 'd41d8cd98f00b204e9800998ecf8427e')
        mock_popen.assert_called_once_with("tar cf - 'test_dir' | md5sum")

    @patch('http_downloader.os.popen')
    @patch('http_downloader.os.path.isdir')
    def test_get_md5_invalid(self, mock_isdir, mock_popen):
        """Test get_md5 with invalid output"""
        mock_isdir.return_value = False
        mock_output = Mock()
        mock_output.read.return_value = 'invalid output'
        mock_popen.return_value = mock_output

        result = HttpDownloader.get_md5('test_file')

        self.assertEqual(result, 'false')

    def test_download_data_product_switch_error(self):
        """Test download_data when product switch fails"""
        with patch.object(self.downloader, 'switch_to_product', return_value=False):
            result = self.downloader.download_data('Product', 'Release', 'v1.0', self.test_dir)
        self.assertEqual(result, HttpDownloader.DOWNLOAD_STATUS_ERROR)

    def test_download_data_release_switch_skipped(self):
        """Test download_data when release switch fails"""
        self.downloader.product_name = 'Product'
        with patch.object(self.downloader, 'switch_to_release', return_value=False):
            result = self.downloader.download_data('Product', 'Release', 'v1.0', self.test_dir)
        self.assertEqual(result, HttpDownloader.DOWNLOAD_STATUS_SKIPPED)

    def test_download_data_success(self):
        """Test successful download_data"""
        self.downloader.product_name = 'Product'
        with patch.object(self.downloader, 'switch_to_release', return_value=True), \
                patch.object(self.downloader, 'download_from_release',
                             return_value=HttpDownloader.DOWNLOAD_STATUS_SUCCESS):
            result = self.downloader.download_data('Product', 'Release', 'v1.0', self.test_dir)
        self.assertEqual(result, HttpDownloader.DOWNLOAD_STATUS_SUCCESS)

    def test_data_exist_product_switch_fails(self):
        """Test data_exist when product switch fails"""
        with patch.object(self.downloader, 'switch_to_product', return_value=False):
            result = self.downloader.data_exist('Product', 'Release', 'v1.0')
        self.assertFalse(result)

    def test_data_exist_release_not_found(self):
        """Test data_exist when release not found"""
        self.downloader.product_name = 'Product'
        with patch.object(self.downloader, 'switch_to_release', return_value=False):
            result = self.downloader.data_exist('Product', 'Release', 'v1.0')
        self.assertFalse(result)

    def test_data_exist_success(self):
        """Test data_exist when data exists"""
        self.downloader.product_name = 'Product'
        with patch.object(self.downloader, 'switch_to_release', return_value=True):
            result = self.downloader.data_exist('Product', 'Release', 'v1.0')
        self.assertTrue(result)

    def test_constants(self):
        """Test class constants"""
        self.assertEqual(HttpDownloader.DOWNLOAD_STATUS_SUCCESS, 1)
        self.assertEqual(HttpDownloader.DOWNLOAD_STATUS_SKIPPED, 0)
        self.assertEqual(HttpDownloader.DOWNLOAD_STATUS_ERROR, -1)

    def test_credential_and_url(self):
        """Test credential and URL configuration"""
        self.assertIn('username', HttpDownloader.credential)
        self.assertIn('password', HttpDownloader.credential)
        self.assertTrue(HttpDownloader.url_prefix.startswith('https://'))
        self.assertEqual(HttpDownloader.timeout, 30)


if __name__ == '__main__':
    unittest.main()