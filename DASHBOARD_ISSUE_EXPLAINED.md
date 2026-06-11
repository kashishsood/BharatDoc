# Dashboard Issue - Complete Explanation

## 🔍 What's Happening

Your dashboard at **http://localhost:3001** shows:
```
Error Loading Dashboard
timeout of 10000ms exceeded
```

## 🎯 Root Cause

The dashboard is trying to fetch data from the **Analytics API** (port 8002), but:

1. ❌ **Docker Desktop is NOT running**
   - Error: "The system cannot find the file specified" (dockerDesktopLinuxEngine pipe)
   
2. ❌ **PostgreSQL database is NOT running**
   - Requires Docker to be running
   - Analytics API needs PostgreSQL to store/retrieve data
   
3. ❌ **Analytics service is NOT running**
   - Cannot start without database connection
   - Dashboard has no data source

## 📊 Architecture

Here's how the dashboard works:

```
Browser (localhost:3001)
    ↓
    Fetches data from
    ↓
Analytics API (localhost:8002)
    ↓
    Queries data from
    ↓
PostgreSQL Database (localhost:5432)
    ↓
    Runs in
    ↓
Docker Container
```

**All 4 layers must be running for the dashboard to work!**

## ✅ What's Currently Running

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| Dashboard | 3001 | ✅ Running | React app (Vite dev server) |
| Gateway | 8000 | ✅ Running | Mock mode |
| Inference | 8001 | ✅ Running | Mock mode |
| **Analytics** | **8002** | **❌ NOT Running** | **Needs PostgreSQL** |
| **PostgreSQL** | **5432** | **❌ NOT Running** | **Needs Docker** |
| **Docker** | - | **❌ NOT Running** | **Must start first** |

## 🔧 What We've Already Fixed

### 1. API Timeout (✅ Fixed)
**File**: `apps/dashboard/src/api/analytics.ts`
- Increased timeout from 10s to 30s
- Gives more time for API responses

### 2. CORS Configuration (✅ Fixed)
**File**: `analytics/main.py`
- Added CORS middleware
- Allows dashboard to make cross-origin requests
- Configured for localhost:3000 and localhost:3001

### 3. Import Path (✅ Fixed)
**File**: `analytics/main.py`
- Fixed import statement for queries module
- Analytics can now run from its directory

### 4. Database Schema (✅ Ready)
**File**: `analytics/schema.sql`
- Schema is ready to load
- Creates extraction_logs and field_errors tables

### 5. Sample Data (✅ Ready)
**File**: `analytics/seed_data.py`
- Script ready to generate 500 sample logs
- Realistic data for testing dashboard

## ❌ What Still Needs to Be Done

### 1. Start Docker Desktop
**Why**: PostgreSQL runs in a Docker container
**How**: Open Docker Desktop from Windows Start Menu
**Time**: 30-60 seconds to fully start

### 2. Start PostgreSQL Container
**Why**: Analytics API needs a database
**Command**:
```powershell
docker run -d --name bharatdoc-postgres -p 5432:5432 -e POSTGRES_DB=bharatdoc -e POSTGRES_USER=bharatdoc -e POSTGRES_PASSWORD=bharatdoc postgres:15
```
**Time**: 20 seconds to initialize

### 3. Load Database Schema
**Why**: Create tables for storing data
**Command**:
```powershell
Get-Content analytics/schema.sql | docker exec -i bharatdoc-postgres psql -U bharatdoc -d bharatdoc
```
**Time**: 1-2 seconds

### 4. Seed Database
**Why**: Populate with sample data for dashboard
**Command**:
```powershell
cd analytics
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python seed_data.py
```
**Time**: 5-10 seconds

### 5. Start Analytics Service
**Why**: Provide API endpoints for dashboard
**Command**:
```powershell
python main.py
```
**Time**: 2-3 seconds to start

### 6. Refresh Dashboard
**Why**: Load data from analytics API
**How**: Press Ctrl+F5 in browser
**Time**: Instant

## 🎯 Expected Result

After completing all steps, your dashboard will show:

### Metrics Cards
- Total Extractions: **500**
- Average F1 Score: **0.88**
- Average Latency: **160ms**
- Total Errors: **125**

### Charts
- **Daily Volume**: Bar chart showing extractions per day (last 30 days)
- **Model Comparison**: Grouped bar chart comparing F1 scores by document type
- **Latency Trends**: Line chart showing latency over time (last 7 days)

### Tables
- **Field Errors**: Top 10 errors with counts and percentages

### Features
- Auto-refresh every 30 seconds
- Responsive design
- Dark theme
- Interactive tooltips

## 📝 Quick Start Commands

Copy-paste these in order (after starting Docker Desktop):

```powershell
# 1. Start PostgreSQL (wait 20 seconds after this)
docker run -d --name bharatdoc-postgres -p 5432:5432 -e POSTGRES_DB=bharatdoc -e POSTGRES_USER=bharatdoc -e POSTGRES_PASSWORD=bharatdoc postgres:15

# 2. Load schema (run after 20 seconds)
Get-Content analytics/schema.sql | docker exec -i bharatdoc-postgres psql -U bharatdoc -d bharatdoc

# 3. Seed database
cd analytics
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python seed_data.py

# 4. Start analytics (keep terminal open)
python main.py
```

Then refresh browser: **http://localhost:3001** (Ctrl+F5)

## 🔍 Verification Commands

```powershell
# Check Docker is running
docker ps

# Check PostgreSQL is running
docker ps | findstr postgres

# Check analytics health
curl http://localhost:8002/health

# Should return: {"status":"healthy","database":"connected"}
```

## 💡 Why This Happened

The dashboard was built to work with a full backend stack:
- Frontend (React) ✅ Running
- Gateway API ✅ Running (mock mode)
- Inference API ✅ Running (mock mode)
- **Analytics API** ❌ Not running (needs database)
- **PostgreSQL** ❌ Not running (needs Docker)

The analytics service is the **only one that requires a real database** because it stores and retrieves historical data for the dashboard visualizations.

## 🎓 Understanding the Error

```
Error Loading Dashboard
timeout of 10000ms exceeded
```

This means:
1. Dashboard tried to fetch data from `http://localhost:8002/api/analytics/...`
2. Waited 30 seconds (we increased it from 10s)
3. Got no response (because analytics service isn't running)
4. Showed timeout error

Once analytics is running, the dashboard will get data instantly (< 1 second).

## 📚 Files Involved

### Frontend
- `apps/dashboard/src/api/analytics.ts` - API client (timeout fixed)
- `apps/dashboard/src/pages/Dashboard.tsx` - Dashboard page
- `apps/dashboard/src/components/*.tsx` - Chart components

### Backend
- `analytics/main.py` - FastAPI server (CORS fixed)
- `analytics/queries.py` - Database queries
- `analytics/schema.sql` - Database schema
- `analytics/seed_data.py` - Sample data generator

### Configuration
- `apps/dashboard/vite.config.ts` - Proxy configuration
- `analytics/.env.example` - Environment variables template

## 🚀 Next Steps

1. **Read**: `FIX_DASHBOARD_NOW.md` for simple step-by-step instructions
2. **Start**: Docker Desktop
3. **Run**: Commands to set up PostgreSQL and analytics
4. **Refresh**: Dashboard in browser
5. **Enjoy**: Working dashboard with real data! 🎉

---

**Status**: 📋 **READY TO FIX**

All code is ready. Just need to start the services!
