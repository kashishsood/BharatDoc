# Contributing to BharatDoc

Thank you for your interest in contributing to BharatDoc!

## Development Setup

### Prerequisites
- Python 3.10+
- Docker and Docker Compose
- Node.js 18+ (for dashboard)
- PostgreSQL 15+ (for analytics)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/kashishsood/BharatDoc.git
cd BharatDoc
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run with Docker Compose**
```bash
cd docker
docker-compose up -d
```

Services will be available at:
- Gateway: http://localhost:8000
- Inference: http://localhost:8001
- Analytics: http://localhost:8002
- Dashboard: http://localhost:3000

## Project Structure

```
BharatDoc/
├── gateway/          # API gateway with routing
├── router/           # CLIP-based document classifier
├── schemas/          # Pydantic validation schemas
├── inference/        # FastAPI inference server
├── analytics/        # Analytics API with PostgreSQL
├── apps/
│   ├── dashboard/    # React TypeScript dashboard
│   ├── doc_agent/    # CrewAI multi-agent system
│   └── ...           # Other demo apps
├── docker/           # Docker configurations
└── monitoring/       # Prometheus metrics
```

## Running Individual Services

### Gateway (Port 8000)
```bash
python -m gateway.gateway --mock
```

### Inference Server (Port 8001)
```bash
cd inference
python main.py --mock
```

### Analytics API (Port 8002)
```bash
cd analytics
export DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python main.py
```

### Dashboard (Port 3001)
```bash
cd apps/dashboard
npm install
npm run dev
```

### CrewAI Agent (Port 8003)
```bash
cd apps/doc_agent
pip install -r requirements.txt
python main.py
```

## Testing

### Run tests
```bash
pytest tests/
```

### Test specific service
```bash
# Test gateway
curl -X POST http://localhost:8000/process -F "file=@test.jpg"

# Test CrewAI agent
curl -X POST http://localhost:8003/process -F "file=@aadhaar.jpg"

# Test analytics health
curl http://localhost:8002/health
```

## Code Style

- Python: Follow PEP 8, use type hints
- TypeScript: Follow Airbnb style guide
- Use meaningful variable names
- Add docstrings to all functions and classes
- Keep functions focused and single-purpose

## Commit Messages

Follow conventional commits format:
```
feat: add new feature
fix: bug fix
docs: documentation changes
refactor: code refactoring
test: adding tests
chore: maintenance tasks
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit with descriptive messages
7. Push to your fork
8. Open a Pull Request

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Questions?

Open an issue or reach out to the maintainers.
