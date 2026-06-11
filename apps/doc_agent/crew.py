"""
CrewAI-based document processing crew for Indian documents.

This module implements a multi-agent system for classifying, extracting,
and validating Indian document types using CrewAI framework.
"""

from typing import Dict, Any
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool


@tool("classify_document_tool")
def classify_document_tool(image_path: str) -> str:
    """
    Classify the type of Indian document from an image.
    
    Args:
        image_path: Path to the document image file
        
    Returns:
        Document type classification (e.g., 'aadhaar', 'invoice', 'lic_policy')
    """
    # Mock implementation - in production, this would call a CLIP/LayoutLM classifier
    document_types = ['aadhaar', 'invoice', 'lic_policy', 'handwritten', 'pan_card', 'passport']
    
    # Simple heuristic based on filename for demo
    image_lower = image_path.lower()
    if 'aadhaar' in image_lower:
        return 'aadhaar'
    elif 'invoice' in image_lower or 'gst' in image_lower:
        return 'invoice'
    elif 'lic' in image_lower or 'policy' in image_lower:
        return 'lic_policy'
    elif 'pan' in image_lower:
        return 'pan_card'
    elif 'passport' in image_lower:
        return 'passport'
    else:
        return 'handwritten'


@tool("extract_fields_tool")
def extract_fields_tool(image_path: str, document_type: str) -> Dict[str, Any]:
    """
    Extract structured fields from a document based on its type.
    
    Args:
        image_path: Path to the document image file
        document_type: Type of document (from classification)
        
    Returns:
        Dictionary of extracted fields specific to document type
    """
    # Mock implementation - in production, this would call Donut/LayoutLMv3/TrOCR
    mock_extractions = {
        'aadhaar': {
            'aadhaar_number': '1234 5678 9012',
            'name': 'Rajesh Kumar',
            'dob': '15/08/1990',
            'gender': 'Male',
            'address': '123 MG Road, Bangalore, Karnataka - 560001'
        },
        'invoice': {
            'invoice_number': 'INV-2024-001',
            'gstin': '29ABCDE1234F1Z5',
            'date': '15/01/2024',
            'total_amount': '₹15,750.00',
            'vendor_name': 'ABC Trading Pvt Ltd',
            'items': [
                {'description': 'Product A', 'quantity': 2, 'rate': 5000, 'amount': 10000},
                {'description': 'Product B', 'quantity': 1, 'rate': 5750, 'amount': 5750}
            ]
        },
        'lic_policy': {
            'policy_number': 'LIC-789456123',
            'policy_holder_name': 'Priya Sharma',
            'sum_assured': '₹10,00,000',
            'premium_amount': '₹15,000',
            'policy_start_date': '01/04/2023',
            'maturity_date': '01/04/2043',
            'nominee': 'Amit Sharma'
        },
        'pan_card': {
            'pan_number': 'ABCDE1234F',
            'name': 'Vikram Singh',
            'father_name': 'Rajendra Singh',
            'dob': '20/05/1985'
        },
        'passport': {
            'passport_number': 'M1234567',
            'name': 'Anjali Gupta',
            'dob': '10/03/1992',
            'place_of_birth': 'Mumbai',
            'date_of_issue': '15/06/2020',
            'date_of_expiry': '14/06/2030'
        },
        'handwritten': {
            'text_content': 'Extracted handwritten text content',
            'confidence': 0.85
        }
    }
    
    return mock_extractions.get(document_type, {'error': 'Unknown document type'})


@tool("validate_schema_tool")
def validate_schema_tool(fields: Dict[str, Any], document_type: str) -> Dict[str, Any]:
    """
    Validate extracted fields against official Indian document schemas.
    
    Args:
        fields: Dictionary of extracted fields
        document_type: Type of document being validated
        
    Returns:
        Validation result with status and any errors
    """
    # Mock implementation - in production, this would use regex patterns and business rules
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }
    
    if document_type == 'aadhaar':
        # Aadhaar: 12-digit number
        aadhaar = fields.get('aadhaar_number', '').replace(' ', '')
        if not aadhaar.isdigit() or len(aadhaar) != 12:
            validation_result['is_valid'] = False
            validation_result['errors'].append('Aadhaar number must be exactly 12 digits')
    
    elif document_type == 'invoice':
        # GSTIN: 15 characters (2-state code + 10-PAN + 1-entity + 1-Z + 1-checksum)
        gstin = fields.get('gstin', '')
        if len(gstin) != 15:
            validation_result['is_valid'] = False
            validation_result['errors'].append('GSTIN must be exactly 15 characters')
        
        # Invoice number should exist
        if not fields.get('invoice_number'):
            validation_result['is_valid'] = False
            validation_result['errors'].append('Invoice number is required')
    
    elif document_type == 'lic_policy':
        # LIC policy number format validation
        policy_num = fields.get('policy_number', '')
        if not policy_num or len(policy_num) < 9:
            validation_result['is_valid'] = False
            validation_result['errors'].append('Invalid LIC policy number format')
    
    elif document_type == 'pan_card':
        # PAN: 10 characters (5-letters + 4-digits + 1-letter)
        pan = fields.get('pan_number', '')
        if len(pan) != 10:
            validation_result['is_valid'] = False
            validation_result['errors'].append('PAN must be exactly 10 characters')
        elif not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
            validation_result['is_valid'] = False
            validation_result['errors'].append('PAN format: 5 letters + 4 digits + 1 letter')
    
    elif document_type == 'passport':
        # Passport number: 1 letter + 7 digits
        passport = fields.get('passport_number', '')
        if len(passport) != 8:
            validation_result['warnings'].append('Passport number should be 8 characters')
    
    # Add field completeness check
    if not fields:
        validation_result['is_valid'] = False
        validation_result['errors'].append('No fields were extracted')
    
    return validation_result


class DocumentProcessingCrew:
    """
    Multi-agent crew for processing Indian documents.
    
    This crew consists of three specialized agents working in sequence:
    1. DocumentClassifier: Identifies document type
    2. FieldExtractor: Extracts structured fields
    3. SchemaValidator: Validates against official schemas
    """
    
    def __init__(self):
        """Initialize the document processing crew with three specialized agents."""
        self.classifier_agent = self._create_classifier_agent()
        self.extractor_agent = self._create_extractor_agent()
        self.validator_agent = self._create_validator_agent()
        
    def _create_classifier_agent(self) -> Agent:
        """
        Create the document classification agent.
        
        Returns:
            Agent configured for document type classification
        """
        return Agent(
            role="Indian Document Classifier",
            goal="Classify the type of Indian document from an image with high accuracy",
            backstory=(
                "You are an expert in identifying Indian government and official documents. "
                "With years of experience in document analysis, you can distinguish between "
                "Aadhaar cards, GST invoices, LIC policies, PAN cards, passports, and "
                "handwritten forms. You understand the visual characteristics, layouts, "
                "and typical content patterns of each document type."
            ),
            tools=[classify_document_tool],
            verbose=True,
            allow_delegation=False
        )
    
    def _create_extractor_agent(self) -> Agent:
        """
        Create the field extraction agent.
        
        Returns:
            Agent configured for structured field extraction
        """
        return Agent(
            role="Document Field Extractor",
            goal="Extract all structured fields from the document with maximum accuracy",
            backstory=(
                "You are a specialist in optical character recognition and structured data "
                "extraction from documents. You have deep knowledge of multimodal models "
                "like Donut, LayoutLMv3, and TrOCR. You understand the specific fields "
                "required for each Indian document type and can accurately extract names, "
                "numbers, dates, addresses, and other structured information while "
                "maintaining data integrity and format."
            ),
            tools=[extract_fields_tool],
            verbose=True,
            allow_delegation=False
        )
    
    def _create_validator_agent(self) -> Agent:
        """
        Create the schema validation agent.
        
        Returns:
            Agent configured for document schema validation
        """
        return Agent(
            role="Indian Document Schema Validator",
            goal="Validate extracted fields against official Indian document schemas and formats",
            backstory=(
                "You are an expert in Indian government document standards and validation rules. "
                "You know that Aadhaar numbers must be exactly 12 digits, GSTIN must be 15 "
                "characters with specific format rules, PAN cards follow a 10-character pattern "
                "(5 letters + 4 digits + 1 letter), and LIC policy numbers have specific formats. "
                "You meticulously verify each field against official standards to ensure data "
                "quality and compliance with Indian regulations."
            ),
            tools=[validate_schema_tool],
            verbose=True,
            allow_delegation=False
        )
    
    def create_tasks(self, image_path: str) -> tuple[Task, Task, Task]:
        """
        Create the three sequential tasks for document processing.
        
        Args:
            image_path: Path to the document image to process
            
        Returns:
            Tuple of three tasks: (classify_task, extract_task, validate_task)
        """
        classify_task = Task(
            description=(
                f"Classify the Indian document type from the image at: {image_path}. "
                "Determine if it is an Aadhaar card, GST invoice, LIC policy, PAN card, "
                "passport, handwritten form, or other document type. Provide the document "
                "type classification as output."
            ),
            expected_output="A string indicating the document type (e.g., 'aadhaar', 'invoice', 'lic_policy')",
            agent=self.classifier_agent
        )
        
        extract_task = Task(
            description=(
                f"Extract all structured fields from the document at: {image_path}. "
                "Use the document type from the classification task to determine which "
                "fields to extract. For Aadhaar: extract number, name, DOB, gender, address. "
                "For invoices: extract invoice number, GSTIN, date, amounts, vendor details. "
                "For LIC policies: extract policy number, holder name, sum assured, premium, dates. "
                "Return all extracted fields as a structured dictionary."
            ),
            expected_output="A dictionary containing all extracted fields specific to the document type",
            agent=self.extractor_agent,
            context=[classify_task]
        )
        
        validate_task = Task(
            description=(
                "Validate the extracted fields against official Indian document schemas. "
                "Check Aadhaar numbers are 12 digits, GSTIN is 15 characters, PAN follows "
                "the correct format, LIC policy numbers are valid, and all required fields "
                "are present. Report any validation errors or warnings. Return a validation "
                "result with is_valid flag, list of errors, and list of warnings."
            ),
            expected_output="A validation result dictionary with is_valid, errors, and warnings",
            agent=self.validator_agent,
            context=[classify_task, extract_task]
        )
        
        return classify_task, extract_task, validate_task
    
    def process_document(self, image_path: str) -> Dict[str, Any]:
        """
        Process a document through the complete crew workflow.
        
        Args:
            image_path: Path to the document image to process
            
        Returns:
            Dictionary containing classification, extraction, and validation results
        """
        # Create tasks for this document
        classify_task, extract_task, validate_task = self.create_tasks(image_path)
        
        # Assemble the crew
        crew = Crew(
            agents=[self.classifier_agent, self.extractor_agent, self.validator_agent],
            tasks=[classify_task, extract_task, validate_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Execute the crew
        result = crew.kickoff()
        
        # Structure the output
        return {
            'image_path': image_path,
            'status': 'success',
            'result': str(result)
        }


def create_document_crew() -> DocumentProcessingCrew:
    """
    Factory function to create a document processing crew.
    
    Returns:
        Configured DocumentProcessingCrew instance
    """
    return DocumentProcessingCrew()
