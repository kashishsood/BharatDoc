# CI/CD Pipeline Setup for BharatDoc

This document explains the GitHub Actions CI/CD pipeline for BharatDoc-VLM.

## Pipeline Overview

### 1. Main CI/CD Pipeline (`.github/workflows/ci.yml`)

Triggers on:
- Push to `main` branch
- Pull requests to `main` branch

**Jobs:**

#### Job 1: `lint-and-type-check`
- Runs `ruff` for code linting
- Runs `mypy` for type checking
- Fails if either check fails

#### Job 2: `test`
- Runs full test suite with pytest
- Generates coverage report
- Uploads coverage as artifact
- Requires `lint-and-type-check` to pass first

#### Job 3: `build-docker`
- Builds Docker images using docker-compose
- **Only runs on push to main** (not on PRs)
- Requires `test` to pass first

#### Job 4: `security-scan`
- Runs `bandit` security scanner
- Scans for medium and high severity issues
- Continues on error (doesn't fail pipeline)
- Uploads security report as artifact

### 2. PR Checks Pipeline (`.github/workflows/pr-checks.yml`)

Triggers on:
- Pull requests to `main` branch only

**Features:**
- Fast validation (no coverage, shorter timeout)
- Runs `ruff check` and `pytest`
- **Automatically comments on PR** with pass/fail status
- Uses built-in `GITHUB_TOKEN` (no setup needed)

## Local Development

### Run checks locally before pushing:

```bash
# Install dev dependencies
pip install ruff mypy pytest pytest-cov pytest-timeout bandit

# Run linting
ruff check gateway/ inference/ schemas/ router/ core/

# Auto-fix linting issues
ruff check --fix gateway/ inference/ schemas/ router/ core/

# Run type checking
mypy gateway/ inference/ schemas/ --ignore-missing-imports

# Run tests
pytest tests/ -v --tb=short --cov=. --cov-report=term

# Run security scan
bandit -r gateway/ inference/ schemas/ router/ core/ -ll
```

### Run with Make:

```bash
make lint      # Run ruff
make test      # Run pytest
```

## Configuration Files

- **`pyproject.toml`**: Ruff, mypy, bandit, and pytest configuration
- **`pytest.ini`**: Pytest-specific settings (timeout, markers)
- **`.gitignore`**: Excludes build artifacts, caches, model downloads

## Artifacts

The pipeline generates these artifacts:

1. **Coverage Report** (`coverage.xml`)
   - Available for 30 days
   - Download from Actions tab → Workflow run → Artifacts

2. **Security Report** (`bandit-report.json`)
   - Available for 30 days
   - JSON format with all security findings

## Troubleshooting

### Tests timing out
- Default timeout is 30 seconds per test
- Adjust in `pytest.ini` or `pyproject.toml`
- Mark slow tests with `@pytest.mark.slow`

### Linting failures
- Run `ruff check --fix` locally to auto-fix
- Some issues require manual fixes

### Type checking failures
- Add `# type: ignore` for unavoidable issues
- Improve type hints in code

### Docker build failures
- Test locally: `docker-compose -f docker/docker-compose.yml build`
- Check Dockerfile syntax
- Ensure all dependencies are in requirements.txt

## GitHub Secrets (if needed in future)

Currently, the pipeline uses only built-in secrets:
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

To add custom secrets:
1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add secret name and value
4. Reference in workflow: `${{ secrets.SECRET_NAME }}`

## Badge for README

Add this to your README.md to show CI status:

```markdown
![CI/CD Pipeline](https://github.com/kashishsood/BharatDoc/actions/workflows/ci.yml/badge.svg)
```

## Next Steps

1. **Code Coverage Badge**: Integrate with Codecov or Coveralls
2. **Deployment**: Add deployment job for staging/production
3. **Release Automation**: Auto-create releases on version tags
4. **Dependency Updates**: Add Dependabot configuration
