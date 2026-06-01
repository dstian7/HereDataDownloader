import os
import sys
import unittest
from unittest.mock import Mock, MagicMock, patch, mock_open
import tempfile
import shutil
import pandas as pd
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, ".."))

# Import the functions to test
from ai_doc_summarizer import summarize_tnm, generate_glance_md_file


class TestAiDocSummarizer(unittest.TestCase):
    """Test cases for AI document summarizer functions."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.tnm_path = os.path.join(self.test_dir, "TNM-278")
        os.makedirs(self.tnm_path, exist_ok=True)

        # Create Glance subdirectory
        self.glance_path = os.path.join(self.tnm_path, "Glance")
        os.makedirs(self.glance_path, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Remove temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_generate_glance_md_file_success(self):
        """Test successful generation of glance markdown file."""
        # Create a sample Excel file
        df = pd.DataFrame({
            'TNM': [278, 278, 279],
            'Column1': ['A', 'B', 'C'],
            'Column2': [1, 2, 3]
        })
        excel_file = os.path.join(self.glance_path, "Test_Glance.xlsx")
        df.to_excel(excel_file, index=False)

        result = generate_glance_md_file(self.tnm_path)

        expected_md_file = os.path.join(self.glance_path, "Glance-278.md")
        self.assertEqual(result, expected_md_file)
        self.assertTrue(os.path.exists(expected_md_file))
        self.assertTrue(os.path.exists(os.path.join(self.glance_path, "Glance-278.xlsx")))

    def test_generate_glance_md_file_already_exists(self):
        """Test when glance markdown file already exists."""
        # Create existing markdown file
        expected_md_file = os.path.join(self.glance_path, "Glance-278.md")
        with open(expected_md_file, 'w') as f:
            f.write("Existing content")

        result = generate_glance_md_file(self.tnm_path)

        self.assertEqual(result, expected_md_file)
        # Verify content wasn't changed
        with open(expected_md_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Existing content")

    def test_generate_glance_md_file_no_glance_directory(self):
        """Test when Glance directory doesn't exist."""
        # Remove Glance directory
        shutil.rmtree(self.glance_path)

        result = generate_glance_md_file(self.tnm_path)

        self.assertIsNone(result)

    def test_generate_glance_md_file_no_excel_file(self):
        """Test when no Glance Excel file exists in directory."""
        result = generate_glance_md_file(self.tnm_path)

        self.assertIsNone(result)

    def test_generate_glance_md_file_filters_by_tnm_number(self):
        """Test that markdown file only contains rows matching TNM number."""
        # Create Excel with multiple TNM numbers
        df = pd.DataFrame({
            'TNM': [278, 278, 279, 280],
            'Data': ['A', 'B', 'C', 'D']
        })
        excel_file = os.path.join(self.glance_path, "Test_Glance.xlsx")
        df.to_excel(excel_file, index=False)

        result = generate_glance_md_file(self.tnm_path)

        # Read generated Excel to verify filtering
        filtered_excel = os.path.join(self.glance_path, "Glance-278.xlsx")
        df_filtered = pd.read_excel(filtered_excel)
        self.assertEqual(len(df_filtered), 2)
        self.assertTrue(all(df_filtered['TNM'] == 278))

    @patch('ai_doc_summarizer.client')
    def test_summarize_tnm_success(self, mock_client):
        """Test successful TNM summarization."""
        # Setup test files
        pdf_file = os.path.join(self.tnm_path, "TNM-278.pdf")
        with open(pdf_file, 'wb') as f:
            f.write(b"PDF content")

        # Create glance Excel file
        df = pd.DataFrame({'TNM': [278], 'Data': ['Test']})
        excel_file = os.path.join(self.glance_path, "Test_Glance.xlsx")
        df.to_excel(excel_file, index=False)

        # Create prompt file
        config_dir = os.path.join(os.path.dirname(__file__), "../config")
        os.makedirs(config_dir, exist_ok=True)
        prompt_file = os.path.join(config_dir, "tnm_prompt.md")
        with open(prompt_file, 'w') as f:
            f.write("Test prompt")

        # Mock OpenAI responses
        mock_file = Mock()
        mock_file.id = "file-123"
        mock_client.files.create.return_value = mock_file

        mock_response = Mock()
        mock_response.output_text = "This is a summary"
        mock_client.responses.create.return_value = mock_response

        result = summarize_tnm(self.tnm_path)

        expected_output = os.path.join(self.glance_path, "Summary-278.txt")
        self.assertEqual(result, expected_output)
        self.assertTrue(os.path.exists(expected_output))

        with open(expected_output, 'r') as f:
            content = f.read()
        self.assertEqual(content, "This is a summary")

        # Cleanup
        if os.path.exists(config_dir):
            shutil.rmtree(config_dir)

    def test_summarize_tnm_no_pdf_file(self):
        """Test when PDF file doesn't exist."""
        # Create glance Excel file
        df = pd.DataFrame({'TNM': [278], 'Data': ['Test']})
        excel_file = os.path.join(self.glance_path, "Test_Glance.xlsx")
        df.to_excel(excel_file, index=False)

        # Create prompt file
        config_dir = os.path.join(os.path.dirname(__file__), "../config")
        os.makedirs(config_dir, exist_ok=True)
        prompt_file = os.path.join(config_dir, "tnm_prompt.md")
        with open(prompt_file, 'w') as f:
            f.write("Test prompt")

        result = summarize_tnm(self.tnm_path)

        self.assertEqual(result, "Error: TNM PDF file does not exist.")

        # Cleanup
        if os.path.exists(config_dir):
            shutil.rmtree(config_dir)

    def test_summarize_tnm_glance_generation_failed(self):
        """Test when glance markdown generation fails."""
        # Don't create Glance directory
        shutil.rmtree(self.glance_path)

        result = summarize_tnm(self.tnm_path)

        self.assertEqual(result, "Error: Glance markdown file generation failed.")

    @patch('ai_doc_summarizer.client')
    def test_summarize_tnm_no_response(self, mock_client):
        """Test when OpenAI returns no response."""
        # Setup test files
        pdf_file = os.path.join(self.tnm_path, "TNM-278.pdf")
        with open(pdf_file, 'wb') as f:
            f.write(b"PDF content")

        # Create glance Excel file
        df = pd.DataFrame({'TNM': [278], 'Data': ['Test']})
        excel_file = os.path.join(self.glance_path, "Test_Glance.xlsx")
        df.to_excel(excel_file, index=False)

        # Create prompt file
        config_dir = os.path.join(os.path.dirname(__file__), "../config")
        os.makedirs(config_dir, exist_ok=True)
        prompt_file = os.path.join(config_dir, "tnm_prompt.md")
        with open(prompt_file, 'w') as f:
            f.write("Test prompt")

        # Mock OpenAI responses
        mock_file = Mock()
        mock_file.id = "file-123"
        mock_client.files.create.return_value = mock_file

        mock_response = Mock()
        mock_response.output_text = None
        mock_client.responses.create.return_value = mock_response

        result = summarize_tnm(self.tnm_path)

        self.assertEqual(result, "No reply found.")

        # Cleanup
        if os.path.exists(config_dir):
            shutil.rmtree(config_dir)

    def test_generate_glance_md_file_edge_case_tnm_number_extraction(self):
        """Test TNM number extraction from path with different formats."""
        # Test with TNM-001
        tnm_path_001 = os.path.join(self.test_dir, "TNM-001")
        os.makedirs(tnm_path_001, exist_ok=True)
        glance_path_001 = os.path.join(tnm_path_001, "Glance")
        os.makedirs(glance_path_001, exist_ok=True)

        df = pd.DataFrame({'TNM': [1, 1], 'Data': ['A', 'B']})
        excel_file = os.path.join(glance_path_001, "Test_Glance.xlsx")
        df.to_excel(excel_file, index=False)

        result = generate_glance_md_file(tnm_path_001)

        expected_md_file = os.path.join(glance_path_001, "Glance-1.md")
        self.assertEqual(result, expected_md_file)
        self.assertTrue(os.path.exists(expected_md_file))

    def test_generate_glance_md_file_empty_dataframe(self):
        """Test with Excel file that has no matching TNM numbers."""
        df = pd.DataFrame({
            'TNM': [100, 200, 300],
            'Data': ['A', 'B', 'C']
        })
        excel_file = os.path.join(self.glance_path, "Test_Glance.xlsx")
        df.to_excel(excel_file, index=False)

        result = generate_glance_md_file(self.tnm_path)

        # Should still create files, just with empty/filtered data
        expected_md_file = os.path.join(self.glance_path, "Glance-278.md")
        self.assertEqual(result, expected_md_file)
        self.assertTrue(os.path.exists(expected_md_file))


if __name__ == '__main__':
    unittest.main()