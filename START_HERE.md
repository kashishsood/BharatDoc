# 🚀 START HERE - Fix Your Dashboard

## 📋 Current Situation

✅ **Dashboard is running** on http://localhost:3001
❌ **Dashboard shows timeout error** - cannot load data

## 🎯 The Problem (Simple Version)

Your dashboard needs data from the Analytics API, but:
- Analytics API is not running (needs PostgreSQL)
- PostgreSQL is not running (needs Docker)
- **Docker Desktop is not started** ← This is the root cause!

## ✅ The Solution (3 Steps)

### Step 1: Start Docker Desktop ⏱️ 1 minute

1. Press **Windows Key**
2. Type **"Docker Desktop"**
3. Open it and **wait for it to fully start** (30-60 seconds)
4. Look for Docker icon in system tray - should be green/white

### Step 2: Run Setup Commands ⏱️ 2 minutes

Open PowerShell in the BharatDoc folder and run these commands:

```powershell
# Start PostgreSQL
docker run -d --name bharatdoc-postgres -p 5432:5432 -e POSTGRES_DB=bharatdoc -e POSTGRES_USER=bharatdoc -e POSTGRES_PASSWORD=bharatdoc postgres:15
```

**Wait 20 seconds**, then:

```powershell
# Load database schema
Get-Content analytics/schema.sql | docker exec -i bharatdoc-postgres psql -U bharatdoc -d bharatdoc
```

Then:

```powershell
# Seed database
cd analytics
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python seed_data.py
```

Then:

```powershell
# Start analytics service (KEEP THIS TERMINAL OPEN!)
python main.py
```

### Step 3: Refresh Dashboard ⏱️ 5 seconds

1. Go to browser: **http://localhost:3001**
2. Press **Ctrl + F5**
3. **Done!** Dashboard should now show data 🎉

## 🎯 Verification

Before refreshing, test analytics API in a new PowerShell window:

```powershell
curl http://localhost:8002/health
```

Should return:
```json
{"status":"healthy","database":"connected"}
```

If you see this, the dashboard will work!

## 📊 What You'll See

Once working:
- ✅ Total Extractions: 500
- ✅ Average F1 Score: 0.88
- ✅ Average Latency: 160ms
- ✅ Charts with real data
- ✅ Auto-refresh every 30 seconds

## 📚 More Information

- **Simple guide**: Read `FIX_DASHBOARD_NOW.md`
- **Detailed explanation**: Read `DASHBOARD_ISSUE_EXPLAINED.md`
- **Troubleshooting**: Read `DASHBOARD_NOT_LOADING_FIX.md`

## 🚨 Common Issues

### "Docker command not found"
Install Docker Desktop: https://www.docker.com/products/docker-desktop/

### "Container already exists"
```powershell
docker start bharatdoc-postgres
```
Then continue from "Load database schema"

### "Port already in use"
```powershell
docker stop bharatdoc-postgres
docker rm bharatdoc-postgres
```
Then retry

## ⏱️ Total Time

- Start Docker Desktop: 1 minute
- Run commands: 2 minutes
- Refresh dashboard: 5 seconds

**Total: ~3 minutes to fix!**

---

## 🎯 Quick Summary

1. **Start Docker Desktop** (wait for it to fully start)
2. **Run 4 commands** (PostgreSQL, schema, seed, analytics)
3. **Refresh browser** (Ctrl+F5)

That's it! Your dashboard will work.

---

**Ready?** Start with Step 1: Open Docker Desktop!
