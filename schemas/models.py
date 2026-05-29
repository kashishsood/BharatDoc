"""
BharatDoc-VLM: Pydantic v2 Models for Document Schemas
======================================================

Provides strongly-typed Pydantic models for every supported document type.
These models are the single source of truth for extraction output validation.

Design decisions:
- All models use Pydantic v2 (model_validate, model_json_schema)
- Optional fields use `None` default so partial extractions are valid
- Validators catch common OCR errors (e.g., 'O' vs '0' in Aadhaar numbers)
- SchemaValidator dispatches to the correct model based on doc_type
"""

from __future__ import annotations

import re
import logging
from typing import Optional, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# =============================================================
# Enums
# =============================================================

class Gender(str, Enum):
    """Gender values accepted on Aadhaar cards (English + Hindi)."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    TRANSGENDER = "TRANSGENDER"
    PURUSH = "पुरुष"
    MAHILA = "महिला"
    TRANSGENDER_HI = "ट्रांसजेंडर"


class PremiumFrequency(str, Enum):
    """LIC premium payment frequencies."""
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    HALF_YEARLY = "HALF_YEARLY"
    YEARLY = "YEARLY"
    SINGLE = "SINGLE"


class NomineeRelationship(str, Enum):
    """Standard nominee relationships for insurance."""
    SPOUSE = "SPOUSE"
    CHILD = "CHILD"
    PARENT = "PARENT"
    SIBLING = "SIBLING"
    OTHER = "OTHER"


# =============================================================
# Aadhaar Schema
# =============================================================

class AadhaarSchema(BaseModel):
    """
    Extraction schema for Aadhaar cards issued by UIDAI.
    
    Why this structure:
    - aadhaar_number allows spaces because OCR often preserves the 
      'XXXX XXXX XXXX' printed format. We normalize in the validator.
    - name_hindi is optional because older cards or poor scans may 
      not yield the Hindi text.
    - photo_present is a boolean detection signal, not the image itself.
    """
    name: str = Field(..., min_length=2, max_length=100, description="Full name as printed")
    name_hindi: Optional[str] = Field(None, description="Name in Devanagari if detected")
    date_of_birth: str = Field(..., description="DOB in DD/MM/YYYY format")
    gender: Gender = Field(..., description="Gender enum")
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number")
    address: Optional[str] = Field(None, max_length=500, description="Full address")
    pincode: Optional[str] = Field(None, description="6-digit PIN code")
    photo_present: bool = Field(True, description="Whether photo region detected")
    vid: Optional[str] = Field(None, description="16-digit Virtual ID if present")
    issue_date: Optional[str] = Field(None, description="Card issue date")

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, v: str) -> str:
        """
        Normalize and validate Aadhaar number.
        OCR commonly confuses 'O' with '0' and 'l' with '1'.
        We fix these before validation.
        """
        # Common OCR corrections
        cleaned = v.replace(" ", "").replace("O", "0").replace("o", "0").replace("l", "1")
        if not re.match(r"^\d{12}$", cleaned):
            raise ValueError(f"Aadhaar number must be 12 digits, got: {cleaned}")
        # Return in standard spaced format
        return f"{cleaned[:4]} {cleaned[4:8]} {cleaned[8:12]}"

    @field_validator("date_of_birth", "issue_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate DD/MM/YYYY date format."""
        if v is None:
            return v
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError(f"Date must be in DD/MM/YYYY format, got: {v}")
        return v

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: Optional[str]) -> Optional[str]:
        """Validate 6-digit Indian PIN code."""
        if v is None:
            return v
        cleaned = v.strip()
        if not re.match(r"^\d{6}$", cleaned):
            raise ValueError(f"PIN code must be 6 digits, got: {cleaned}")
        return cleaned


# =============================================================
# LIC Policy Schema
# =============================================================

class RiderBenefit(BaseModel):
    """Rider benefits attached to an LIC policy."""
    rider_name: str
    rider_sum_assured: float = Field(..., gt=0)


class LICPolicySchema(BaseModel):
    """
    Extraction schema for LIC (Life Insurance Corporation) policy documents.
    
    Why this structure:
    - sum_assured and premium_amount have wide ranges because LIC covers
      micro-insurance (₹10K) to high-value plans (₹10Cr).
    - Separate policy_term vs premium_paying_term because limited premium
      payment plans are common in India.
    - rider_benefits is a list because policies often bundle accident/CI riders.
    """
    policy_number: str = Field(..., description="8-10 digit policy number")
    holder_name: str = Field(..., min_length=2, max_length=100)
    plan_name: str = Field(..., min_length=3, description="LIC plan name")
    plan_number: Optional[str] = Field(None, description="3-4 digit plan number")
    sum_assured: float = Field(..., ge=10000, le=100000000, description="Sum assured in INR")
    premium_amount: float = Field(..., ge=100, le=10000000, description="Premium in INR")
    premium_frequency: Optional[PremiumFrequency] = None
    policy_term_years: Optional[int] = Field(None, ge=5, le=75)
    premium_paying_term_years: Optional[int] = Field(None, ge=1, le=75)
    commencement_date: Optional[str] = Field(None, description="DD/MM/YYYY")
    maturity_date: str = Field(..., description="DD/MM/YYYY")
    nominee_name: Optional[str] = None
    nominee_relationship: Optional[NomineeRelationship] = None
    branch_code: Optional[str] = None
    rider_benefits: Optional[List[RiderBenefit]] = None

    @field_validator("policy_number")
    @classmethod
    def validate_policy_number(cls, v: str) -> str:
        """LIC policy numbers are typically 8-10 digits."""
        cleaned = v.strip().replace(" ", "")
        if not re.match(r"^\d{8,10}$", cleaned):
            raise ValueError(f"Policy number must be 8-10 digits, got: {cleaned}")
        return cleaned

    @field_validator("maturity_date", "commencement_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError(f"Date must be in DD/MM/YYYY format, got: {v}")
        return v


# =============================================================
# Invoice Schema
# =============================================================

class InvoiceLineItem(BaseModel):
    """Single line item on an invoice."""
    description: str
    hsn_code: Optional[str] = Field(None, description="HSN/SAC code for GST")
    quantity: float = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)
    amount: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_amount_consistency(self) -> "InvoiceLineItem":
        """
        Check that amount ≈ quantity × unit_price.
        We use a 1% tolerance because rounding differences are common
        in Indian invoices (amounts often rounded to nearest rupee).
        """
        expected = self.quantity * self.unit_price
        if expected > 0 and abs(self.amount - expected) / expected > 0.01:
            logger.warning(
                f"Line item amount {self.amount} differs from "
                f"qty({self.quantity}) × price({self.unit_price}) = {expected}"
            )
        return self


class InvoiceSchema(BaseModel):
    """
    Extraction schema for Indian invoices and bills.
    
    Why this structure:
    - Separate CGST/SGST/IGST because Indian GST has a dual structure:
      intra-state = CGST+SGST, inter-state = IGST. Models must capture this.
    - vendor_gstin/buyer_gstin use the official 15-char GSTIN regex.
    - amount_in_words is kept because it's a cross-validation signal —
      if the numeric total and text total disagree, flag for review.
    """
    invoice_number: str = Field(..., min_length=1, max_length=50)
    vendor_name: str = Field(..., min_length=2, max_length=200)
    vendor_gstin: Optional[str] = Field(None, description="15-char GSTIN")
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    invoice_date: str = Field(..., description="DD/MM/YYYY")
    due_date: Optional[str] = None
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    subtotal: Optional[float] = Field(None, ge=0)
    cgst_amount: Optional[float] = Field(None, ge=0)
    sgst_amount: Optional[float] = Field(None, ge=0)
    igst_amount: Optional[float] = Field(None, ge=0)
    total_tax: Optional[float] = Field(None, ge=0)
    total_amount: float = Field(..., ge=0, le=1_000_000_000)
    amount_in_words: Optional[str] = None
    place_of_supply: Optional[str] = None
    payment_terms: Optional[str] = None

    @field_validator("vendor_gstin", "buyer_gstin")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate GSTIN format: 2-digit state code + 10-char PAN + 1 entity + 1Z + 1 check.
        Example: 27AAPFU0939F1ZV
        """
        if v is None:
            return v
        pattern = r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$"
        if not re.match(pattern, v.upper()):
            raise ValueError(f"Invalid GSTIN format: {v}")
        return v.upper()

    @field_validator("invoice_date", "due_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError(f"Date must be in DD/MM/YYYY format, got: {v}")
        return v

    @model_validator(mode="after")
    def validate_total_consistency(self) -> "InvoiceSchema":
        """
        Cross-validate: subtotal + total_tax should ≈ total_amount.
        This catches extraction errors where the model grabs the wrong number.
        """
        if self.subtotal is not None and self.total_tax is not None:
            expected = self.subtotal + self.total_tax
            if expected > 0 and abs(self.total_amount - expected) / expected > 0.02:
                logger.warning(
                    f"Total amount {self.total_amount} differs from "
                    f"subtotal({self.subtotal}) + tax({self.total_tax}) = {expected}"
                )
        return self


# =============================================================
# Schema Validator — dispatch by doc_type
# =============================================================

# Maps doc_type string → Pydantic model class
SCHEMA_REGISTRY = {
    "aadhaar": AadhaarSchema,
    "lic_policy": LICPolicySchema,
    "invoice": InvoiceSchema,
}


class SchemaValidator:
    """
    Validates extraction outputs against the correct schema based on doc_type.
    
    Why a separate class instead of just calling Model.model_validate():
    - Centralises schema lookup logic
    - Returns structured validation errors (which fields failed) instead of 500s
    - Supports adding new doc types by registering in SCHEMA_REGISTRY
    
    Usage:
        validator = SchemaValidator()
        result = validator.validate("aadhaar", extracted_data)
        if result["valid"]:
            validated_output = result["data"]
        else:
            field_errors = result["errors"]
    """

    def __init__(self):
        self.registry = SCHEMA_REGISTRY.copy()

    def register(self, doc_type: str, schema_class: type[BaseModel]) -> None:
        """Register a new document type schema."""
        self.registry[doc_type] = schema_class
        logger.info(f"Registered schema for doc_type: {doc_type}")

    def validate(self, doc_type: str, data: dict) -> dict:
        """
        Validate extracted data against the schema for the given doc_type.
        
        Returns:
            {
                "valid": bool,
                "doc_type": str,
                "data": dict | None,      # validated data if valid
                "errors": list | None      # structured field errors if invalid
            }
        """
        if doc_type not in self.registry:
            return {
                "valid": False,
                "doc_type": doc_type,
                "data": None,
                "errors": [{"field": "_doc_type", "message": f"Unknown doc_type: {doc_type}"}],
            }

        schema_class = self.registry[doc_type]
        try:
            validated = schema_class.model_validate(data)
            return {
                "valid": True,
                "doc_type": doc_type,
                "data": validated.model_dump(),
                "errors": None,
            }
        except Exception as e:
            # Parse Pydantic validation errors into structured field-level errors
            errors = []
            if hasattr(e, "errors"):
                for err in e.errors():
                    field_path = " → ".join(str(loc) for loc in err.get("loc", []))
                    errors.append({
                        "field": field_path,
                        "message": err.get("msg", str(err)),
                        "type": err.get("type", "unknown"),
                        "input": err.get("input", None),
                    })
            else:
                errors.append({"field": "_unknown", "message": str(e)})

            logger.warning(f"Schema validation failed for {doc_type}: {len(errors)} errors")
            return {
                "valid": False,
                "doc_type": doc_type,
                "data": None,
                "errors": errors,
            }

    def get_schema_json(self, doc_type: str) -> dict:
        """Return the JSON Schema for a given doc_type (useful for API docs)."""
        if doc_type not in self.registry:
            raise ValueError(f"Unknown doc_type: {doc_type}")
        return self.registry[doc_type].model_json_schema()

    @property
    def supported_types(self) -> list[str]:
        """List all supported document types."""
        return list(self.registry.keys())
