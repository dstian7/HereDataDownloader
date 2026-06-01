import unittest
import sys
import os
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

from version_config_generator import (
    parse_data_quarter,
    get_last_quarter_split,
    get_quarter_split,
    get_monthly_split,
    get_previous_version,
    get_version,
    get_quarterly_version,
    get_monthly_version,
    get_file_version,
    get_normal_file_version,
    get_standalone_file_version,
    get_monthly_file_version,
    is_month,
    is_quarter,
    get_base_quarter,
    get_rdf_quarter,
    get_jv_quarter,
    QUARTER_NUMBER_CHAR_DICT,
    STANDALONE_QUARTER_NUMBER_CHAR_DICT,
    MONTHLY_VERSION_CONFIG
)


class TestParseDataQuarter(unittest.TestCase):
    """Test parse_data_quarter function"""

    def test_parse_data_quarter_valid(self):
        """Test parsing valid data quarter"""
        year, quarter = parse_data_quarter("17Q4")
        self.assertEqual(year, 17)
        self.assertEqual(quarter, 4)

    def test_parse_data_quarter_all_quarters(self):
        """Test parsing all valid quarters"""
        for q in range(1, 5):
            year, quarter = parse_data_quarter(f"20Q{q}")
            self.assertEqual(year, 20)
            self.assertEqual(quarter, q)

    def test_parse_data_quarter_invalid_format(self):
        """Test parsing invalid data quarter format"""
        with self.assertRaises(SystemExit) as cm:
            parse_data_quarter("invalid")
        self.assertEqual(cm.exception.code, -1)

    def test_parse_data_quarter_invalid_quarter_number(self):
        """Test parsing invalid quarter number"""
        with self.assertRaises(SystemExit):
            parse_data_quarter("17Q5")


class TestGetLastQuarterSplit(unittest.TestCase):
    """Test get_last_quarter_split function"""

    def test_get_last_quarter_split_middle_quarter(self):
        """Test getting last quarter for middle quarters"""
        year, quarter = get_last_quarter_split("17Q2")
        self.assertEqual(year, 17)
        self.assertEqual(quarter, 1)

    def test_get_last_quarter_split_first_quarter(self):
        """Test getting last quarter for Q1 (wraps to previous year Q4)"""
        year, quarter = get_last_quarter_split("17Q1")
        self.assertEqual(year, 16)
        self.assertEqual(quarter, 4)

    def test_get_last_quarter_split_q4(self):
        """Test getting last quarter for Q4"""
        year, quarter = get_last_quarter_split("20Q4")
        self.assertEqual(year, 20)
        self.assertEqual(quarter, 3)


class TestGetQuarterSplit(unittest.TestCase):
    """Test get_quarter_split function"""

    def test_get_quarter_split_valid(self):
        """Test splitting valid quarter"""
        year, quarter = get_quarter_split("18Q3")
        self.assertEqual(year, 18)
        self.assertEqual(quarter, 3)

    def test_get_quarter_split_invalid(self):
        """Test splitting invalid quarter"""
        with self.assertRaises(SystemExit):
            get_quarter_split("invalid")


class TestGetMonthlySplit(unittest.TestCase):
    """Test get_monthly_split function"""

    def test_get_monthly_split_valid(self):
        """Test splitting valid monthly version"""
        year, month = get_monthly_split("25M11")
        self.assertEqual(year, "25")
        self.assertEqual(month, "11")

    def test_get_monthly_split_lowercase(self):
        """Test splitting monthly version with lowercase m"""
        year, month = get_monthly_split("25m01")
        self.assertEqual(year, "25")
        self.assertEqual(month, "01")

    def test_get_monthly_split_all_months(self):
        """Test splitting all valid months"""
        for m in range(1, 13):
            month_str = str(m).zfill(2)
            year, month = get_monthly_split(f"20M{month_str}")
            self.assertEqual(year, "20")
            self.assertEqual(month, month_str)

    def test_get_monthly_split_invalid(self):
        """Test splitting invalid monthly version"""
        with self.assertRaises(SystemExit):
            get_monthly_split("invalid")

    def test_get_monthly_split_invalid_month(self):
        """Test splitting invalid month number"""
        with self.assertRaises(SystemExit):
            get_monthly_split("25M13")


class TestGetPreviousVersion(unittest.TestCase):
    """Test get_previous_version function"""

    def test_get_previous_version_quarter(self):
        """Test getting previous version for quarter"""
        prev = get_previous_version("17Q2")
        self.assertEqual(prev, "17Q1")

    def test_get_previous_version_quarter_wrap_year(self):
        """Test getting previous version for Q1 (wraps to previous year)"""
        prev = get_previous_version("17Q1")
        self.assertEqual(prev, "16Q4")

    def test_get_previous_version_month(self):
        """Test getting previous version for month"""
        prev = get_previous_version("25M11W1")
        self.assertEqual(prev, "25M10W1")

    def test_get_previous_version_month_january(self):
        """Test getting previous version for January (wraps to previous year)"""
        prev = get_previous_version("25M01W1")
        self.assertEqual(prev, "24M12W1")

    def test_get_previous_version_invalid(self):
        """Test getting previous version for invalid format"""
        result = get_previous_version("invalid")
        self.assertIsNone(result)


class TestGetVersion(unittest.TestCase):
    """Test get_version function"""

    def test_get_version_quarter(self):
        """Test getting version for quarter"""
        result = get_version("17Q2")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    def test_get_version_quarter_standalone(self):
        """Test getting standalone version for quarter"""
        result = get_version("17Q2", is_standalone=True)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    def test_get_version_month(self):
        """Test getting version for month"""
        result = get_version("25M11W1")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_get_version_invalid(self):
        """Test getting version for invalid format"""
        result = get_version("invalid")
        self.assertIsNone(result)


class TestGetQuarterlyVersion(unittest.TestCase):
    """Test get_quarterly_version function"""

    def test_get_quarterly_version_normal(self):
        """Test getting quarterly version"""
        map_version, add_version, add_full_version = get_quarterly_version("17Q2")
        self.assertEqual(map_version, "S171R1")
        self.assertEqual(add_version, "S171")
        self.assertEqual(add_full_version, "S171_E")

    def test_get_quarterly_version_standalone(self):
        """Test getting standalone quarterly version"""
        map_version, add_version, add_full_version = get_quarterly_version("17Q2", is_standalone=True)
        self.assertEqual(map_version, "S171R1")
        self.assertEqual(add_version, "S171")
        self.assertEqual(add_full_version, "S171_P")

    def test_get_quarterly_version_all_quarters(self):
        """Test getting quarterly version for all quarters"""
        for q in range(1, 5):
            result = get_quarterly_version(f"20Q{q}")
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 3)


class TestGetMonthlyVersion(unittest.TestCase):
    """Test get_monthly_version function"""

    def test_get_monthly_version_valid(self):
        """Test getting monthly version"""
        add_version, full_version = get_monthly_version("25M11W1")
        self.assertEqual(add_version, "S251")
        self.assertEqual(full_version, "S251_35")

    def test_get_monthly_version_with_year_change(self):
        """Test getting monthly version with year change"""
        add_version, full_version = get_monthly_version("25M01W1")
        self.assertEqual(add_version, "S241")
        self.assertEqual(full_version, "S241_44")

    def test_get_monthly_version_invalid(self):
        """Test getting monthly version for invalid version"""
        result = get_monthly_version("25M13W1")
        self.assertEqual(result, "")


class TestGetFileVersion(unittest.TestCase):
    """Test get_file_version function"""

    def test_get_file_version_quarter_normal(self):
        """Test getting file version for quarter"""
        result = get_file_version("17Q2")
        self.assertEqual(result, "171E0")

    def test_get_file_version_quarter_standalone(self):
        """Test getting standalone file version for quarter"""
        result = get_file_version("17Q2", is_standalone=True)
        self.assertEqual(result, "171P0")

    def test_get_file_version_month(self):
        """Test getting file version for month"""
        result = get_file_version("25M11W1")
        self.assertEqual(result, "25135")

    def test_get_file_version_month_standalone(self):
        """Test getting standalone file version for month"""
        result = get_file_version("25M03W1", is_standalone=True)
        self.assertEqual(result, "251P0")


class TestGetNormalFileVersion(unittest.TestCase):
    """Test get_normal_file_version function"""

    def test_get_normal_file_version(self):
        """Test getting normal file version"""
        result = get_normal_file_version("17Q2")
        self.assertEqual(result, "171E0")

    def test_get_normal_file_version_all_quarters(self):
        """Test getting normal file version for all quarters"""
        expected = {1: "H", 2: "E", 3: "F", 4: "G"}
        for q in range(1, 5):
            result = get_normal_file_version(f"20Q{q}")
            self.assertIn(expected[q], result)


class TestGetStandaloneFileVersion(unittest.TestCase):
    """Test get_standalone_file_version function"""

    def test_get_standalone_file_version(self):
        """Test getting standalone file version"""
        result = get_standalone_file_version("17Q2")
        self.assertEqual(result, "171P0")

    def test_get_standalone_file_version_all_quarters(self):
        """Test getting standalone file version for all quarters"""
        expected = {1: "S", 2: "P", 3: "Q", 4: "R"}
        for q in range(1, 5):
            result = get_standalone_file_version(f"20Q{q}")
            self.assertIn(expected[q], result)


class TestGetMonthlyFileVersion(unittest.TestCase):
    """Test get_monthly_file_version function"""

    def test_get_monthly_file_version_normal(self):
        """Test getting monthly file version"""
        result = get_monthly_file_version("25M11W1")
        self.assertEqual(result, "25135")

    def test_get_monthly_file_version_standalone(self):
        """Test getting standalone monthly file version"""
        result = get_monthly_file_version("25M03W1", is_standalone=True)
        self.assertEqual(result, "251P0")

    def test_get_monthly_file_version_standalone_no_standalone_num(self):
        """Test getting standalone monthly file version when no standalone number exists"""
        result = get_monthly_file_version("25M04W1", is_standalone=True)
        self.assertEqual(result, "25105")

    def test_get_monthly_file_version_with_year_change(self):
        """Test getting monthly file version with year change"""
        result = get_monthly_file_version("25M01W1")
        self.assertEqual(result, "24144")

    def test_get_monthly_file_version_invalid(self):
        """Test getting monthly file version for invalid version"""
        result = get_monthly_file_version("25M13W1")
        self.assertEqual(result, "")


class TestIsMonth(unittest.TestCase):
    """Test is_month function"""

    def test_is_month_valid(self):
        """Test valid monthly version"""
        self.assertTrue(is_month("25M11W1"))
        self.assertTrue(is_month("25m11w1"))

    def test_is_month_all_valid_months(self):
        """Test all valid monthly versions"""
        for m in range(1, 13):
            month_str = str(m).zfill(2)
            self.assertTrue(is_month(f"25M{month_str}W1"))

    def test_is_month_invalid(self):
        """Test invalid monthly version"""
        self.assertFalse(is_month("invalid"))
        self.assertFalse(is_month("25M13W1"))
        self.assertFalse(is_month("25M00W1"))
        self.assertFalse(is_month("25Q1"))


class TestIsQuarter(unittest.TestCase):
    """Test is_quarter function"""

    def test_is_quarter_valid(self):
        """Test valid quarterly version"""
        self.assertTrue(is_quarter("17Q2"))
        self.assertTrue(is_quarter("17q2"))

    def test_is_quarter_all_valid_quarters(self):
        """Test all valid quarterly versions"""
        for q in range(1, 5):
            self.assertTrue(is_quarter(f"20Q{q}"))

    def test_is_quarter_invalid(self):
        """Test invalid quarterly version"""
        self.assertFalse(is_quarter("invalid"))
        self.assertFalse(is_quarter("17Q5"))
        self.assertFalse(is_quarter("17Q0"))
        self.assertFalse(is_quarter("25M11W1"))


class TestGetBaseQuarter(unittest.TestCase):
    """Test get_base_quarter function"""

    def test_get_base_quarter_valid(self):
        """Test getting base quarter"""
        result = get_base_quarter("25M11W1")
        self.assertEqual(result, "25Q4")

    def test_get_base_quarter_with_year_change(self):
        """Test getting base quarter with year change"""
        result = get_base_quarter("25M01W1")
        self.assertEqual(result, "24Q4")

    def test_get_base_quarter_all_months(self):
        """Test getting base quarter for all configured months"""
        for month_key in MONTHLY_VERSION_CONFIG.keys():
            result = get_base_quarter(f"25{month_key}")
            self.assertIsNotNone(result)
            self.assertIn("Q", result)

    def test_get_base_quarter_invalid(self):
        """Test getting base quarter for invalid version"""
        result = get_base_quarter("25M13W1")
        self.assertEqual(result, "")


class TestGetRdfQuarter(unittest.TestCase):
    """Test get_rdf_quarter function"""

    def test_get_rdf_quarter_valid(self):
        """Test getting RDF quarter"""
        result = get_rdf_quarter("25M03W1")
        self.assertEqual(result, "25Q2")

    def test_get_rdf_quarter_with_year_change(self):
        """Test getting RDF quarter with year change"""
        result = get_rdf_quarter("25M12W1")
        self.assertEqual(result, "26Q1")

    def test_get_rdf_quarter_no_rdf_quarter(self):
        """Test getting RDF quarter when not configured"""
        result = get_rdf_quarter("25M04W1")
        self.assertEqual(result, "")

    def test_get_rdf_quarter_invalid_version(self):
        """Test getting RDF quarter for invalid version"""
        result = get_rdf_quarter("25M13W1")
        self.assertEqual(result, "")

    def test_get_rdf_quarter_non_month(self):
        """Test getting RDF quarter for non-monthly version"""
        result = get_rdf_quarter("17Q2")
        self.assertEqual(result, "")


class TestGetJvQuarter(unittest.TestCase):
    """Test get_jv_quarter function"""

    def test_get_jv_quarter_valid(self):
        """Test getting JV quarter"""
        result = get_jv_quarter("25M11W1")
        self.assertEqual(result, "25Q3")

    def test_get_jv_quarter_with_year_change(self):
        """Test getting JV quarter with year change"""
        result = get_jv_quarter("25M01W1")
        self.assertEqual(result, "24Q4")

    def test_get_jv_quarter_all_configured_months(self):
        """Test getting JV quarter for all configured months"""
        for month_key in MONTHLY_VERSION_CONFIG.keys():
            result = get_jv_quarter(f"25{month_key}")
            self.assertIsNotNone(result)
            self.assertIn("Q", result)

    def test_get_jv_quarter_invalid_version(self):
        """Test getting JV quarter for invalid version"""
        result = get_jv_quarter("25M13W1")
        self.assertEqual(result, "")

    def test_get_jv_quarter_non_month(self):
        """Test getting JV quarter for non-monthly version"""
        result = get_jv_quarter("17Q2")
        self.assertEqual(result, "")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def test_year_boundary_q1_to_q4(self):
        """Test year boundary transition from Q1 to Q4"""
        year, quarter = get_last_quarter_split("20Q1")
        self.assertEqual(year, 19)
        self.assertEqual(quarter, 4)

    def test_month_boundary_january(self):
        """Test month boundary for January"""
        prev = get_previous_version("20M01W1")
        self.assertEqual(prev, "19M12W1")

    def test_all_quarter_chars_mapped(self):
        """Test all quarter characters are properly mapped"""
        for q_num, char in QUARTER_NUMBER_CHAR_DICT.items():
            self.assertIn(q_num, range(1, 5))
            self.assertIsInstance(char, str)

    def test_all_standalone_quarter_chars_mapped(self):
        """Test all standalone quarter characters are properly mapped"""
        for q_num, char in STANDALONE_QUARTER_NUMBER_CHAR_DICT.items():
            self.assertIn(q_num, range(1, 5))
            self.assertIsInstance(char, str)

    def test_monthly_config_completeness(self):
        """Test monthly configuration has all required fields"""
        required_fields = ["here_version_number", "base_quarter", "jv_base_quarter"]
        for month_key, config in MONTHLY_VERSION_CONFIG.items():
            for field in required_fields:
                self.assertIn(field, config)


if __name__ == '__main__':
    unittest.main()
