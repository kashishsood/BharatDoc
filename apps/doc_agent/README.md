# BharatDoc CrewAI Document Agent

Multi-agent document processing system using CrewAI framework.

## Overview

This service implements a **3-agent CrewAI crew** for intelligent Indian document processing:

1. **DocumentClassifier** - Identifies document type (Aadhaar, Invoice, LIC, PAN, etc.)
2. **FieldExtractor** - Extracts structured fields using multimodal models
3. **SchemaValidator** - Validates against official Indian document schemas

## Architecture

```
Client Upload
    ↓
DocumentClassifier Agent
    ↓ (context passing)
FieldExtractor Agent
    ↓ (context passing)
SchemaValidator Agent
    ↓
Structured Result
```

## Agents

### Agent 1: Indian Document Classifier
- **Role**: Classify Indian document types from images
- **Goal**: Identify Aadhaar, GST invoices, LIC policies, PAN cards, passports
- **Tool**: `classify_document_tool` - Returns document type
- **Expertise**: Visual characteristics and layouts of Indian documents

### Agent 2: Document Field Extractor
- **Role**: Extract all structured fields from documents
- **Goal**: Pull names, numbers, dates, addresses with high accuracy
- **Tool**: `extract_fields_tool` - Returns field dictionary
- **Expertise**: Multimodal models (Donut, LayoutLMv3, TrOCR)

### Agent 3: Indian Document Schema Validator
- **Role**: Validate extracted fields against official schemas
- **Goal**: Ensure compliance with Indian government standards
- **Tool**: `validate_schema_tool` - Returns validation result
- **Expertise**: Format validation (12-digit Aadhaar, 15-char GSTIN, PAN pattern)

## Installation

```bash
cd apps/doc_agent
pip install -r requirements.txt
```

## Usage

### Start the service

```bash
python main.py
```

Service starts on `http://localhost:8003`

### Process a document

```bash
curl -X POST http://localhost:8003/process \
  -F "file=@aadhaar_sample.jpg"
```

### Check health

```bash
curl http://localhost:8003/health
```

## API Endpoints

### POST /process
Process a document through the multi-agent crew.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: `file` (image file)

**Response:**
```json
{
  "image_path": "/path/to/image.jpg",
  "status": "success",
  "result": "Classification: aadhaar\nExtraction: {...}\nValidation: {...}"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

### GET /
Root endpoint with API information.

**Response:**
```json
{
  "name": "BharatDoc CrewAI Agent",
  "version": "1.0.0",
  "description": "Multi-agent document processing system",
  "endpoints": {...}
}
```

## Supported Document Types

- ✅ **Aadhaar Card** - 12-digit validation
- ✅ **GST Invoice** - GSTIN 15-character validation
- ✅ **LIC Policy** - Policy number format validation
- ✅ **PAN Card** - 10-character pattern (5 letters + 4 digits + 1 letter)
- ✅ **Passport** - 8-character format (1 letter + 7 digits)
- ✅ **Handwritten Forms** - Text extraction with confidence

## Validation Rules

### Aadhaar
- Must be exactly 12 digits
- Example: `1234 5678 9012`

### GSTIN
- Must be exactly 15 characters
- Format: 2-digit state + 10-char PAN + 1-entity + 1-Z + 1-checksum
- Example: `29ABCDE1234F1Z5`

### PAN Card
- Must be exactly 10 characters
- Format: 5 letters + 4 digits + 1 letter
- Example: `ABCDE1234F`

### LIC Policy
- Minimum 9 characters
- Example: `LIC-789456123`

### Passport
- 8 characters (1 letter + 7 digits)
- Example: `M1234567`

## Mock Data

The agents currently use mock tools that return realistic data for testing. In production, these would be replaced with:

- **CLIP classifier** for document type identification
- **Donut/LayoutLMv3/TrOCR** for field extraction
- **Regex validators** for schema compliance

## Code Structure

```
apps/doc_agent/
├── __init__.py           # Package initialization
├── crew.py               # Agent definitions, tools, crew assembly
├── main.py               # FastAPI application
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## Dependencies

- `crewai==0.28.8` - Multi-agent framework
- `fastapi==0.109.0` - Web framework
- `uvicorn==0.27.0` - ASGI server
- `python-multipart==0.0.6` - File upload support
- `pydantic==2.5.3` - Data validation

## Development

### Run in development mode

```bash
python main.py
```

### Run with custom port

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
```

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
```

### Using Uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 8003 --workers 4
```

## Example Output

### Classification Result
```
Document Type: aadhaar
Confidence: 1.0
```

### Extraction Result
```python
{
    'aadhaar_number': '1234 5678 9012',
    'name': 'Rajesh Kumar',
    'dob': '15/08/1990',
    'gender': 'Male',
    'address': '123 MG Road, Bangalore, Karnataka - 560001'
}
```

### Validation Result
```python
{
    'is_valid': True,
    'errors': [],
    'warnings': []
}
```

## Error Handling

The service returns structured error responses:

```json
{
  "detail": "Invalid file type. Allowed types: .jpg, .jpeg, .png, .pdf"
}
```

## Logs

The crew runs in verbose mode, showing agent reasoning:

```
[Agent: Indian Document Classifier]
Analyzing document characteristics...
Classification: aadhaar (confidence: 0.95)

[Agent: Document Field Extractor]
Extracting fields for document type: aadhaar
Fields extracted: aadhaar_number, name, dob, gender, address

[Agent: Indian Document Schema Validator]
Validating Aadhaar number format: 12 digits ✓
All validations passed
```

## Testing

### Manual Testing

```bash
# Create a test image
echo "test" > test.jpg

# Upload it
curl -X POST http://localhost:8003/process \
  -F "file=@test.jpg"
```

### Integration with BharatDoc

This service can be integrated into the BharatDoc pipeline:

```python
import httpx

async def process_with_crew(image_path: str):
    async with httpx.AsyncClient() as client:
        with open(image_path, 'rb') as f:
            response = await client.post(
                'http://localhost:8003/process',
                files={'file': f}
            )
        return response.json()
```

## Contributing

This is a demonstration implementation. For production use:

1. Replace mock tools with real model endpoints
2. Add authentication and rate limiting
3. Implement proper error recovery
4. Add metrics and monitoring
5. Scale with multiple crew instances

## License

Part of the BharatDoc project.

## Author

Created for BharatDoc document intelligence system.
