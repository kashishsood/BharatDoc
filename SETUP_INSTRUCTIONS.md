# GitHub Actions CI/CD Setup Instructions

## Files Created

The following files have been created for your CI/CD pipeline:

### GitHub Actions Workflows
1. **`.github/workflows/ci.yml`** - Main CI/CD pipeline
2. **`.github/workflows/pr-checks.yml`** - Fast PR validation with auto-comments

### Configuration Files
3. **`pyproject.toml`** - Ruff, mypy, bandit, and pytest configuration
4. **`pytest.ini`** - Pytest-specific settings
5. **`.gitignore`** - Git ignore patterns

### Documentation
6. **`.github/CICD_SETUP.md`** - Complete CI/CD documentation

### Scripts
7. **`scripts/run_ci_checks.sh`** - Local CI checks (Linux/Mac)
8. **`scripts/run_ci_checks.bat`** - Local CI checks (Windows)

### Updated Files
9. **`requirements.txt`** - Added `pytest-timeout>=2.2.0`
10. **`Makefile`** - Added CI check commands

---

## Step-by-Step Setup

### 1. Add Files to Git

```bash
# Add all new files
git add .github/
git add pyproject.toml pytest.ini .gitignore
git add scripts/
git add .github/CICD_SETUP.md SETUP_INSTRUCTIONS.md
git add requirements.txt Makefile

# Check what will be committed
git status
```

### 2. Commit Changes

```bash
git commit -m "Add GitHub Actions CI/CD pipeline

- Main CI/CD workflow with lint, test, docker build, security scan
- PR checks workflow with auto-commenting
- Ruff, mypy, pytest, bandit configuration
- Local CI check scripts for Windows and Linux
- Updated Makefile with CI commands
- Added pytest-timeout to requirements.txt"
```

### 3. Push to GitHub

```bash
git push origin main
```

### 4. Verify Pipeline

1. Go to your GitHub repository: https://github.com/kashishsood/BharatDoc
2. Click on the **"Actions"** tab
3. You should see the CI/CD pipeline running
4. Wait for all jobs to complete

---

## Testing the Pipeline

### Test on a Pull Request

1. Create a new branch:
   ```bash
   git checkout -b test-ci-pipeline
   ```

2. Make a small change (e.g., add a comment to README.md)

3. Commit and push:
   ```bash
   git add README.md
   git commit -m "Test CI pipeline"
   git push origin test-ci-pipeline
   ```

4. Create a Pull Request on GitHub

5. Watch the PR checks run and auto-comment on your PR!

---

## Running Checks Locally

### Option 1: Use Make (Recommended)

```bash
# Run all CI checks
make ci-checks

# Or run individually
make lint          # Linting only
make lint-fix      # Auto-fix linting issues
make typecheck     # Type checking only
make test          # Tests only
make security      # Security scan only
```

### Option 2: Use Scripts

**Linux/Mac:**
```bash
chmod +x scripts/run_ci_checks.sh
./scripts/run_ci_checks.sh
```

**Windows:**
```cmd
scripts\run_ci_checks.bat
```

### Option 3: Manual Commands

```bash
# Install dev dependencies
pip install ruff mypy pytest pytest-cov pytest-timeout bandit

# Run checks
ruff check gateway/ inference/ schemas/ router/ core/
mypy gateway/ inference/ schemas/ --ignore-missing-imports
pytest tests/ -v --tb=short --timeout=30
bandit -r gateway/ inference/ schemas/ router/ core/ -ll
```

---

## Pipeline Features

### ✅ What the Pipeline Does

1. **Linting** - Ensures code style consistency with ruff
2. **Type Checking** - Catches type errors with mypy
3. **Testing** - Runs full test suite with coverage
4. **Docker Build** - Validates Docker images (main branch only)
5. **Security Scan** - Detects security vulnerabilities with bandit
6. **PR Comments** - Auto-comments on PRs with pass/fail status

### 🚀 Automatic Triggers

- **Push to main**: Runs full pipeline including Docker build
- **Pull Request**: Runs lint, test, security (no Docker build)
- **PR Checks**: Fast validation + auto-comment on PR

### 📊 Artifacts

- Coverage reports (30 days retention)
- Security scan reports (30 days retention)

---

## Troubleshooting

### Pipeline Fails on First Run

**Common issues:**

1. **Missing dependencies in requirements.txt**
   - Solution: Ensure all imports are in requirements.txt

2. **Linting failures**
   - Solution: Run `ruff check --fix` locally and commit fixes

3. **Test failures**
   - Solution: Run `pytest tests/ -v` locally to debug

4. **Type checking failures**
   - Solution: Add type hints or use `# type: ignore` comments

### Tests Timeout

- Default timeout is 30 seconds per test
- Adjust in `pytest.ini` if needed
- Mark slow tests with `@pytest.mark.slow`

### Docker Build Fails

- Test locally: `docker-compose -f docker/docker-compose.yml build`
- Check Dockerfile syntax
- Ensure base images are accessible

---

## Next Steps

### 1. Add CI Badge to README

Add this to the top of your `README.md`:

```markdown
# BharatDoc-VLM 🇮🇳

![CI/CD Pipeline](https://github.com/kashishsood/BharatDoc/actions/workflows/ci.yml/badge.svg)
![PR Checks](https://github.com/kashishsood/BharatDoc/actions/workflows/pr-checks.yml/badge.svg)

**Production-grade multimodal document intelligence for Indian documents.**
```

### 2. Configure Branch Protection

1. Go to Settings → Branches
2. Add rule for `main` branch
3. Enable:
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - Select: `lint-and-type-check`, `test`, `pr-validation`

### 3. Optional Enhancements

- **Code Coverage Badge**: Integrate with Codecov
- **Deployment**: Add deployment jobs for staging/production
- **Release Automation**: Auto-create releases on version tags
- **Dependabot**: Auto-update dependencies

---

## Support

For issues or questions:
1. Check `.github/CICD_SETUP.md` for detailed documentation
2. Review GitHub Actions logs in the Actions tab
3. Run checks locally to debug before pushing

---

**Ready to push? Run this:**

```bash
git add .
git commit -m "Add CI/CD pipeline"
git push origin main
```

Then watch your pipeline run at: https://github.com/kashishsood/BharatDoc/actions
