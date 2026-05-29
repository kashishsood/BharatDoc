"""
BharatDoc-VLM: Schema Validation Tests
=========================================
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.models import AadhaarSchema, LICPolicySchema, InvoiceSchema, SchemaValidator


class TestAadhaarSchema:
    def test_valid_aadhaar(self):
        data = {
            "name": "Rajesh Kumar", "date_of_birth": "15/08/1990",
            "gender": "MALE", "aadhaar_number": "9234 5678 9012",
        }
        result = AadhaarSchema.model_validate(data)
        assert result.name == "Rajesh Kumar"
        assert result.aadhaar_number == "9234 5678 9012"

    def test_aadhaar_ocr_correction(self):
        """Test that O→0 and l→1 corrections work."""
        data = {
            "name": "Test User", "date_of_birth": "01/01/2000",
            "gender": "MALE", "aadhaar_number": "9234 5678 9O12",
        }
        result = AadhaarSchema.model_validate(data)
        assert result.aadhaar_number == "9234 5678 9012"

    def test_invalid_aadhaar_number(self):
        data = {
            "name": "Test", "date_of_birth": "01/01/2000",
            "gender": "MALE", "aadhaar_number": "123",
        }
        with pytest.raises(Exception):
            AadhaarSchema.model_validate(data)

    def test_invalid_date_format(self):
        data = {
            "name": "Test", "date_of_birth": "2000-01-01",
            "gender": "MALE", "aadhaar_number": "923456789012",
        }
        with pytest.raises(Exception):
            AadhaarSchema.model_validate(data)

    def test_hindi_gender(self):
        data = {
            "name": "Test", "date_of_birth": "01/01/2000",
            "gender": "पुरुष", "aadhaar_number": "923456789012",
        }
        result = AadhaarSchema.model_validate(data)
        assert result.gender.value == "पुरुष"


class TestLICSchema:
    def test_valid_policy(self):
        data = {
            "policy_number": "12345678", "holder_name": "Priya Nair",
            "plan_name": "Jeevan Anand", "sum_assured": 1000000.0,
            "premium_amount": 25000.0, "maturity_date": "01/04/2045",
        }
        result = LICPolicySchema.model_validate(data)
        assert result.sum_assured == 1000000.0

    def test_invalid_sum_assured(self):
        data = {
            "policy_number": "12345678", "holder_name": "Test",
            "plan_name": "Test Plan", "sum_assured": 100.0,
            "premium_amount": 25000.0, "maturity_date": "01/04/2045",
        }
        with pytest.raises(Exception):
            LICPolicySchema.model_validate(data)


class TestInvoiceSchema:
    def test_valid_invoice(self):
        data = {
            "invoice_number": "INV-001", "vendor_name": "TCS Ltd",
            "invoice_date": "15/01/2024", "total_amount": 100000.0,
            "line_items": [{"description": "Service", "quantity": 10,
                           "unit_price": 10000, "amount": 100000}],
        }
        result = InvoiceSchema.model_validate(data)
        assert result.total_amount == 100000.0

    def test_valid_gstin(self):
        data = {
            "invoice_number": "INV-001", "vendor_name": "TCS",
            "invoice_date": "15/01/2024", "total_amount": 50000.0,
            "vendor_gstin": "27AAACT2727Q1ZV",
        }
        result = InvoiceSchema.model_validate(data)
        assert result.vendor_gstin == "27AAACT2727Q1ZV"

    def test_invalid_gstin(self):
        data = {
            "invoice_number": "INV-001", "vendor_name": "TCS",
            "invoice_date": "15/01/2024", "total_amount": 50000.0,
            "vendor_gstin": "INVALID",
        }
        with pytest.raises(Exception):
            InvoiceSchema.model_validate(data)


class TestSchemaValidator:
    def test_validate_valid_aadhaar(self):
        validator = SchemaValidator()
        data = {
            "name": "Test User", "date_of_birth": "01/01/2000",
            "gender": "MALE", "aadhaar_number": "923456789012",
        }
        result = validator.validate("aadhaar", data)
        assert result["valid"] is True

    def test_validate_invalid_returns_errors(self):
        validator = SchemaValidator()
        result = validator.validate("aadhaar", {"name": "X"})
        assert result["valid"] is False
        assert result["errors"] is not None
        assert len(result["errors"]) > 0

    def test_unknown_doc_type(self):
        validator = SchemaValidator()
        result = validator.validate("unknown_type", {})
        assert result["valid"] is False
        assert "unknown_type" in result["errors"][0]["message"].lower() or "unknown" in result["errors"][0]["field"]

    def test_supported_types(self):
        validator = SchemaValidator()
        assert "aadhaar" in validator.supported_types
        assert "lic_policy" in validator.supported_types
        assert "invoice" in validator.supported_types
