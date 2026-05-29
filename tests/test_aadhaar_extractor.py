"""
BharatDoc-VLM: Aadhaar Extractor Tests
=========================================

Tests for the rule-based Aadhaar field extraction pipeline.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_pipeline.aadhaar_extractor import extract_aadhaar_fields, AadhaarExtraction


class TestAadhaarNumberExtraction:
    def test_standard_format(self):
        text = "Aadhaar: 9234 5678 9012"
        result = extract_aadhaar_fields(text)
        assert result.aadhaar_number == "9234 5678 9012"
        assert result.aadhaar_confidence >= 0.85

    def test_no_spaces(self):
        text = "ID: 923456789012"
        result = extract_aadhaar_fields(text)
        assert result.aadhaar_number == "9234 5678 9012"
        # Lower confidence because it was a continuous digit sequence
        assert result.aadhaar_confidence >= 0.65

    def test_ocr_substitution(self):
        """O→0, l→1 correction."""
        text = "Aadhaar: 923O 5678 9O12"
        result = extract_aadhaar_fields(text)
        assert result.aadhaar_number == "9230 5678 9012"

    def test_missing_aadhaar(self):
        text = "Government of India\nName: Test User"
        result = extract_aadhaar_fields(text)
        assert result.aadhaar_number is None
        assert any("not found" in w.lower() for w in result.warnings)


class TestDateExtraction:
    def test_standard_dob(self):
        text = "DOB: 15/08/1990"
        result = extract_aadhaar_fields(text)
        assert result.date_of_birth == "15/08/1990"
        assert result.dob_confidence >= 0.80

    def test_dash_separator(self):
        text = "Date of Birth: 01-12-2000"
        result = extract_aadhaar_fields(text)
        assert result.date_of_birth == "01/12/2000"

    def test_invalid_date_skipped(self):
        text = "Code: 99/99/9999"
        result = extract_aadhaar_fields(text)
        assert result.date_of_birth is None

    def test_missing_dob(self):
        text = "Name: Rajesh Kumar"
        result = extract_aadhaar_fields(text)
        assert result.date_of_birth is None
        assert any("date" in w.lower() for w in result.warnings)


class TestGenderExtraction:
    def test_male_english(self):
        text = "Gender: MALE"
        result = extract_aadhaar_fields(text)
        assert result.gender == "MALE"

    def test_female_english(self):
        text = "Gender: Female"
        result = extract_aadhaar_fields(text)
        assert result.gender == "FEMALE"

    def test_male_hindi(self):
        text = "लिंग: पुरुष"
        result = extract_aadhaar_fields(text)
        assert result.gender == "MALE"

    def test_female_hindi(self):
        text = "लिंग: महिला"
        result = extract_aadhaar_fields(text)
        assert result.gender == "FEMALE"

    def test_missing_gender(self):
        text = "Name: Rajesh"
        result = extract_aadhaar_fields(text)
        assert result.gender is None


class TestNameExtraction:
    def test_name_from_labeled_line(self):
        text = "Government of India\nRajesh Kumar Sharma\nDOB: 15/08/1990"
        result = extract_aadhaar_fields(text)
        assert result.name is not None
        assert "Rajesh" in result.name

    def test_skips_header(self):
        text = "Government of India\nUnique Identification Authority\nAnanya Reddy"
        result = extract_aadhaar_fields(text)
        assert result.name is not None
        assert "Government" not in result.name
        assert "Ananya" in result.name

    def test_skips_date_line(self):
        text = "DOB: 15/08/1990\nSuresh Nair"
        result = extract_aadhaar_fields(text)
        assert result.name is not None
        assert "Suresh" in result.name


class TestFullExtraction:
    def test_complete_aadhaar(self):
        text = """Government of India
Unique Identification Authority
Rajesh Kumar Sharma
DOB: 15/08/1990
Male
9234 5678 9012
Address: H.No 45, Sector 12, Dwarka
New Delhi - 110075"""
        result = extract_aadhaar_fields(text)
        assert result.aadhaar_number == "9234 5678 9012"
        assert result.date_of_birth == "15/08/1990"
        assert result.gender == "MALE"
        assert result.name is not None
        assert "Rajesh" in result.name
        assert result.overall_confidence > 0.7

    def test_partial_extraction_with_warnings(self):
        text = "Some garbled OCR text without clear fields"
        result = extract_aadhaar_fields(text)
        assert len(result.warnings) > 0
        assert result.overall_confidence == 0.0

    def test_to_dict_format(self):
        text = "Name: Test\nDOB: 01/01/2000\n9999 8888 7777\nMale"
        result = extract_aadhaar_fields(text)
        d = result.to_dict()
        assert d["doc_type"] == "aadhaar"
        assert "fields" in d
        assert "overall_confidence" in d
        assert "warnings" in d
        assert "extraction_completeness" in d
        # Each field should have value + confidence
        for fname, fdata in d["fields"].items():
            assert "value" in fdata
            assert "confidence" in fdata


class TestAddressExtraction:
    def test_address_after_label(self):
        text = """Name: Test User
Address: H.No 45, Sector 12
Dwarka, New Delhi"""
        result = extract_aadhaar_fields(text)
        assert result.address is not None
        assert "Sector 12" in result.address
