import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

from tn_toll_cost_validator import TnTollCostValidator


class TestTnTollCostValidator(unittest.TestCase):
    """Test cases for TnTollCostValidator class"""

    def setUp(self):
        self.region = "KOR"
        self.version = "26Q1"
        self.data_path = "/var/www/html/data/KOR_HERE_26Q1/RAW-TOLLCOST/RAW-TOLLCOST_KOR_HERE_26Q1"

    @patch('tn_toll_cost_validator.os.chdir')
    @patch('tn_toll_cost_validator.os.getcwd')
    @patch('tn_toll_cost_validator.os.system')
    def test_init_sets_data_path_and_xml_file(self, mock_system, mock_getcwd, mock_chdir):
        """Constructor should accept data_path and derive tollcost_xml_file from it."""
        mock_getcwd.return_value = "/some/dir"

        validator = TnTollCostValidator(self.region, self.version, self.data_path)

        self.assertEqual(validator.region, self.region)
        self.assertEqual(validator.version, self.version)
        self.assertEqual(validator.vendor, "KOR_HERE_26Q1")
        self.assertEqual(validator.data_path, self.data_path)
        self.assertEqual(validator.tollcost_xml_file,
                         os.path.join(self.data_path, "tn_toll_cost.xml"))
        self.assertEqual(validator.s3_raw_data_path,
                         "s3://tnavmapdata/raw_data/gemini/KOR_HERE_26Q1")

    @patch('tn_toll_cost_validator.os.chdir')
    @patch('tn_toll_cost_validator.os.getcwd')
    @patch('tn_toll_cost_validator.os.system')
    @patch('tn_toll_cost_validator.os.path.exists')
    def test_validate_returns_not_ready_when_xml_missing(self, mock_exists, mock_system,
                                                        mock_getcwd, mock_chdir):
        """validate() should return 'not ready' if the tollcost xml file is missing."""
        mock_exists.return_value = False
        mock_getcwd.return_value = "/some/dir"

        validator = TnTollCostValidator(self.region, self.version, self.data_path)
        main_result, sub_result = validator.validate()

        self.assertEqual(main_result, {"status": "not ready"})
        self.assertEqual(sub_result["component"], "toll_cost")

    @patch('tn_toll_cost_validator.os.chdir')
    @patch('tn_toll_cost_validator.os.getcwd')
    @patch('tn_toll_cost_validator.os.system')
    @patch('tn_toll_cost_validator.subprocess.call')
    @patch('tn_toll_cost_validator.os.path.exists')
    def test_validate_returns_not_ready_when_rdf_marker_missing(self, mock_exists, mock_call,
                                                                mock_system, mock_getcwd,
                                                                mock_chdir):
        """validate() should return 'not ready' if the S3 .rdf_ready marker isn't present."""
        mock_exists.return_value = True
        mock_call.return_value = 1
        mock_getcwd.return_value = "/some/dir"

        validator = TnTollCostValidator(self.region, self.version, self.data_path)
        main_result, _ = validator.validate()

        self.assertEqual(main_result, {"status": "not ready"})

    @patch('tn_toll_cost_validator.io.open', new_callable=mock_open, read_data="here_1 Toll A\n")
    @patch('tn_toll_cost_validator.ET.parse')
    @patch('tn_toll_cost_validator.os.chdir')
    @patch('tn_toll_cost_validator.os.getcwd')
    @patch('tn_toll_cost_validator.os.system')
    def test_generate_report_copies_to_s3_on_pass(self, mock_system, mock_getcwd, mock_chdir,
                                                  mock_parse, mock_file):
        """generate_report should copy data to S3 when pass threshold reached."""
        mock_getcwd.return_value = "/some/dir"

        # Build an XML with a single Toll element matching the CSV row
        toll = MagicMock()
        toll.get.side_effect = lambda key: {"ID": "tn_1", "Name": "Toll A"}.get(key)
        toll.find.return_value = None  # no aliases
        root = MagicMock()
        root.findall.return_value = [toll]
        tree = MagicMock()
        tree.getroot.return_value = root
        mock_parse.return_value = tree

        validator = TnTollCostValidator(self.region, self.version, self.data_path)
        mock_system.reset_mock()

        main_result, _ = validator.generate_report()

        expected_cmd = "aws s3 cp {} {} --recursive".format(
            self.data_path, validator.s3_raw_data_path)
        s3_calls = [c for c in mock_system.call_args_list if c.args and c.args[0] == expected_cmd]
        self.assertEqual(len(s3_calls), 1)
        self.assertEqual(main_result["status"], "pass")

    @patch('tn_toll_cost_validator.io.open', new_callable=mock_open, read_data="id_a name_a\n")
    @patch('tn_toll_cost_validator.ET.parse')
    @patch('tn_toll_cost_validator.os.chdir')
    @patch('tn_toll_cost_validator.os.getcwd')
    @patch('tn_toll_cost_validator.os.system')
    def test_generate_report_does_not_copy_on_fail(self, mock_system, mock_getcwd, mock_chdir,
                                                   mock_parse, mock_file):
        """generate_report should NOT copy data to S3 when match rate is below threshold."""
        mock_getcwd.return_value = "/some/dir"

        # XML has no entries → no matches → match_rate 0% → FAIL
        root = MagicMock()
        root.findall.return_value = []
        tree = MagicMock()
        tree.getroot.return_value = root
        mock_parse.return_value = tree

        validator = TnTollCostValidator(self.region, self.version, self.data_path)
        mock_system.reset_mock()

        main_result, _ = validator.generate_report()

        expected_cmd_prefix = "aws s3 cp {}".format(self.data_path)
        s3_calls = [c for c in mock_system.call_args_list
                    if c.args and c.args[0].startswith(expected_cmd_prefix)]
        self.assertEqual(len(s3_calls), 0)
        self.assertEqual(main_result["status"], "error")


if __name__ == "__main__":
    unittest.main()
