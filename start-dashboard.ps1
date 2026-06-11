# BharatDoc Dashboard Startup Script
Write-Host "🚀 Starting BharatDoc Dashboard Services..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Docker is running
Write-Host "Step 1: Checking Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 2: Setup PostgreSQL
Write-Host "Step 2: Setting up PostgreSQL..." -ForegroundColor Yellow
$postgresExists = docker ps -a --filter "name=bharatdoc-postgres" --format "{{.Names}}"

if ($postgresExists -eq "bharatdoc-postgres") {
    $postgresRunning = docker ps --filter "name=bharatdoc-postgres" --format "{{.Names}}"
    
    if ($postgresRunning -eq "bharatdoc-postgres") {
        Write-Host "✅ PostgreSQL is already running" -ForegroundColor Green
    }
    else {
        Write-Host "Starting PostgreSQL container..." -ForegroundColor Cyan
        docker start bharatdoc-postgres
        Write-Host "✅ PostgreSQL started" -ForegroundColor Green
        Start-Sleep -Seconds 15
    }
}
else {
    Write-Host "Creating PostgreSQL container..." -ForegroundColor Cyan
    docker run -d --name bharatdoc-postgres -p 5432:5432 -e POSTGRES_DB=bharatdoc -e POSTGRES_USER=bharatdoc -e POSTGRES_PASSWORD=bharatdoc postgres:15
    Write-Host "✅ PostgreSQL container created" -ForegroundColor Green
    Write-Host "Waiting for initialization (20 seconds)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 20
}

Write-Host ""

# Step 3: Load schema
Write-Host "Step 3: Loading database schema..." -ForegroundColor Yellow
try {
    Get-Content analytics/schema.sql | docker exec -i bharatdoc-postgres psql -U bharatdoc -d bharatdoc 2>&1 | Out-Null
    Write-Host "✅ Database schema loaded" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Schema might already exist" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Seed database
Write-Host "Step 4: Seeding database..." -ForegroundColor Yellow
$env:DATABASE_URL = "postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
Push-Location analytics
python seed_data.py
Pop-Location
Write-Host "✅ Database seeded" -ForegroundColor Green

Write-Host ""

# Step 5: Check services
Write-Host "Step 5: Checking services..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 2 -ErrorAction Stop | Out-Null
    Write-Host "✅ Analytics service is running" -ForegroundColor Green
    $analyticsRunning = $true
}
catch {
    Write-Host "⚠️  Analytics service is not running" -ForegroundColor Yellow
    $analyticsRunning = $false
}

try {
    Invoke-WebRequest -Uri "http://localhost:3001" -TimeoutSec 2 -ErrorAction Stop | Out-Null
    Write-Host "✅ Dashboard is running" -ForegroundColor Green
    $dashboardRunning = $true
}
catch {
    Write-Host "⚠️  Dashboard is not running" -ForegroundColor Yellow
    $dashboardRunning = $false
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ SETUP COMPLETE!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Service Status:" -ForegroundColor Cyan
Write-Host "  ✅ PostgreSQL: Running on port 5432" -ForegroundColor Green

if ($analyticsRunning) {
    Write-Host "  ✅ Analytics API: Running on port 8002" -ForegroundColor Green
}
else {
    Write-Host "  ⚠️  Analytics API: Not running" -ForegroundColor Yellow
}

if ($dashboardRunning) {
    Write-Host "  ✅ Dashboard: Running on port 3001" -ForegroundColor Green
}
else {
    Write-Host "  ⚠️  Dashboard: Not running" -ForegroundColor Yellow
}

Write-Host ""

if (-not $analyticsRunning -or -not $dashboardRunning) {
    Write-Host "📝 Next Steps:" -ForegroundColor Cyan
    Write-Host ""
    
    if (-not $analyticsRunning) {
        Write-Host "1. Start Analytics Service:" -ForegroundColor Yellow
        Write-Host "   cd analytics" -ForegroundColor White
        Write-Host "   `$env:DATABASE_URL=`"postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc`"" -ForegroundColor White
        Write-Host "   python main.py" -ForegroundColor White
        Write-Host ""
    }
    
    if (-not $dashboardRunning) {
        Write-Host "2. Start Dashboard:" -ForegroundColor Yellow
        Write-Host "   cd apps/dashboard" -ForegroundColor White
        Write-Host "   npm run dev" -ForegroundColor White
        Write-Host ""
    }
    
    Write-Host "3. Open browser: http://localhost:3001" -ForegroundColor Yellow
}
else {
    Write-Host "🎉 All services are running!" -ForegroundColor Green
    Write-Host "🌐 Open Dashboard: http://localhost:3001" -ForegroundColor Cyan
    Write-Host "Press Ctrl+F5 to refresh" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
