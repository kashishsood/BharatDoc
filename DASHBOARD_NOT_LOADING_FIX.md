# 🔧 Dashboard Not Loading - Complete Fix Guide

## ❌ Current Problem

Your dashboard shows: **"Error Loading Dashboard - timeout of 10000ms exceeded"**

## 🔍 Root Cause

The analytics service (port 8002) is **NOT running** because:
1. ❌ Docker Desktop is not started
2. ❌ PostgreSQL database is not running
3. ❌ Analytics service cannot connect to database

**The dashboard needs the analytics API to fetch data!**

---

## ✅ Complete Fix (Step-by-Step)

### Step 1: Start Docker Desktop

1. **Open Docker Desktop** from Windows Start Menu
2. **Wait** for Docker to fully start (30-60 seconds)
3. Look for the Docker icon in system tray to turn green

### Step 2: Start PostgreSQL Container

Open PowerShell in the BharatDoc folder and run:

```powershell
docker run -d --name bharatdoc-postgres -p 5432:5432 -e POSTGRES_DB=bharatdoc -e POSTGRES_USER=bharatdoc -e POSTGRES_PASSWORD=bharatdoc postgres:15
```

**Wait 15-20 seconds** for PostgreSQL to initialize.

### Step 3: Verify PostgreSQL is Running

```powershell
docker ps
```

You should see `bharatdoc-postgres` container running.

### Step 4: Load Database Schema

```powershell
Get-Content analytics/schema.sql | docker exec -i bharatdoc-postgres psql -U bharatdoc -d bharatdoc
```

You should see output like:
```
CREATE TABLE
CREATE INDEX
CREATE INDEX
```

### Step 5: Seed Database with Sample Data

```powershell
cd analytics
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python seed_data.py
```

You should see:
```
✅ Seeded 500 extraction logs
✅ Seeded 125 field errors
```

### Step 6: Start Analytics Service

```powershell
# Make sure you're in the analytics folder
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8002
```

### Step 7: Verify Analytics is Working

Open a **new PowerShell window** and test:

```powershell
curl http://localhost:8002/health
```

You should see:
```json
{"status":"healthy","database":"connected"}
```

### Step 8: Refresh Dashboard

1. Go to your browser: http://localhost:3001
2. Press **Ctrl + F5** (hard refresh)
3. Dashboard should now load with data! 🎉

---

## 🎯 Quick Verification Checklist

Before refreshing the dashboard, verify all services are running:

```powershell
# Check PostgreSQL
docker ps | findstr postgres

# Check Analytics API
curl http://localhost:8002/health

# Check Gateway API
curl http://localhost:8000/docs

# Check Dashboard
# Open browser: http://localhost:3001
```

---

## 🚨 Alternative: Use Docker Compose (Easier!)

If you want to run everything with one command:

### Step 1: Start Docker Desktop (same as above)

### Step 2: Run Docker Compose

```powershell
cd docker
docker-compose up -d
```

This will start:
- ✅ PostgreSQL database
- ✅ Gateway API (port 8000)
- ✅ Inference API (port 8001)
- ✅ Analytics API (port 8002)
- ✅ Dashboard (port 3000)

### Step 3: Seed Database

```powershell
cd ..
cd analytics
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python seed_data.py
```

### Step 4: Access Dashboard

Open browser: http://localhost:3000

---

## 🔍 Troubleshooting

### Issue: "Docker command not found"
**Solution**: Install Docker Desktop from https://www.docker.com/products/docker-desktop/

### Issue: "Port 5432 already in use"
**Solution**: Stop existing PostgreSQL:
```powershell
docker stop bharatdoc-postgres
docker rm bharatdoc-postgres
```
Then retry Step 2.

### Issue: "Connection refused to localhost:8002"
**Solution**: 
1. Check analytics service is running
2. Check DATABASE_URL environment variable is set
3. Check PostgreSQL is running: `docker ps`

### Issue: "CORS error in browser console"
**Solution**: Already fixed in `analytics/main.py` - just restart analytics service

### Issue: "Timeout error persists"
**Solution**: Already fixed in `apps/dashboard/src/api/analytics.ts` - timeout is now 30s

---

## 📊 What You'll See After Fix

Once everything is running, your dashboard will show:

- **Total Extractions**: 500
- **Average F1 Score**: ~0.88
- **Average Latency**: ~160ms
- **Total Errors**: 125
- **Daily Volume Chart**: Last 30 days
- **Model Comparison**: Performance by document type
- **Field Errors Table**: Top errors with percentages
- **Latency Trends**: Last 7 days by model

---

## 🎓 Understanding the Architecture

```
Browser (localhost:3001)
    ↓
Dashboard (React)
    ↓
Analytics API (localhost:8002)
    ↓
PostgreSQL Database (localhost:5432)
```

**All three must be running for the dashboard to work!**

---

## 💡 Pro Tips

1. **Keep services running in separate terminals** so you can see logs
2. **Use Docker Compose** for easier management
3. **Check logs** if something fails:
   ```powershell
   docker logs bharatdoc-postgres
   ```
4. **Stop services cleanly**:
   ```powershell
   # Stop analytics: Ctrl+C in terminal
   # Stop PostgreSQL: docker stop bharatdoc-postgres
   ```

---

## 🚀 Quick Start Commands (Copy-Paste)

```powershell
# 1. Start PostgreSQL
docker run -d --name bharatdoc-postgres -p 5432:5432 -e POSTGRES_DB=bharatdoc -e POSTGRES_USER=bharatdoc -e POSTGRES_PASSWORD=bharatdoc postgres:15

# 2. Wait 20 seconds, then load schema
Start-Sleep -Seconds 20
Get-Content analytics/schema.sql | docker exec -i bharatdoc-postgres psql -U bharatdoc -d bharatdoc

# 3. Seed database
cd analytics
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python seed_data.py

# 4. Start analytics (keep this terminal open)
python main.py
```

Then open browser: http://localhost:3001

---

**Status**: 📋 **READY TO FIX**

Follow the steps above and your dashboard will work! 🎉
