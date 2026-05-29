@echo off
REM Local CI checks script for Windows - run before pushing to GitHub

echo ==========================================
echo Running BharatDoc CI Checks Locally
echo ==========================================

REM Check if in project root
if not exist "requirements.txt" (
    echo Error: Must run from project root
    exit /b 1
)

REM Install dependencies if needed
echo.
echo 1. Checking dependencies...
pip install -q ruff mypy pytest pytest-cov pytest-timeout bandit 2>nul

REM Run ruff
echo.
echo 2. Running ruff linting...
ruff check gateway/ inference/ schemas/ router/ core/ data_pipeline/ evaluation/ feedback_loop/ training/ apps/
if errorlevel 1 (
    echo [FAIL] Ruff failed
    echo Run 'ruff check --fix' to auto-fix issues
    exit /b 1
)
echo [PASS] Ruff passed

REM Run mypy
echo.
echo 3. Running mypy type checking...
mypy gateway/ inference/ schemas/ --ignore-missing-imports --no-strict-optional
if errorlevel 1 (
    echo [FAIL] Mypy failed
    exit /b 1
)
echo [PASS] Mypy passed

REM Run pytest
echo.
echo 4. Running pytest...
pytest tests/ -v --tb=short --timeout=30
if errorlevel 1 (
    echo [FAIL] Tests failed
    exit /b 1
)
echo [PASS] Tests passed

REM Run bandit
echo.
echo 5. Running security scan...
bandit -r gateway/ inference/ schemas/ router/ core/ -ll
if errorlevel 1 (
    echo [WARN] Security issues found (non-blocking)
) else (
    echo [PASS] Security scan passed
)

echo.
echo ==========================================
echo All CI checks passed!
echo ==========================================
echo.
echo Ready to push to GitHub!
