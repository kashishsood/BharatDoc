# 🔧 Fix Dashboard - Simple Steps

## ❌ Current Problem

Your dashboard shows: **"Error Loading Dashboard - timeout exceeded"**

**Root Cause**: Docker Desktop is NOT running, so PostgreSQL can't start, so Analytics API can't run.

---

## ✅ Solution (3 Simple Steps)

### Step 1: Start Docker Desktop

1. Press **Windows Key**
2. Type **"Docker Desktop"**
3. Click to open it
4. **Wait 30-60 seconds** for Docker to fully start
5. Look for Docker icon in system tray (bottom-right) - it should turn green/white

---

### Step 2: Run These Commands

Open PowerShell in the BharatDoc folder and copy-paste these commands **one by one**:

```powershell
# Create and start PostgreSQL
docker run -d --name bharatdoc-postgres -p 5432:5432 -e POSTGRES_DB=bharatdoc -e POSTGRES_USER=bharatdoc -e POSTGRES_PASSWORD=bharatdoc postgres:15
```

Wait 20 seconds, then:

```powershell
# Load database schema
Get-Content analytics/schema.sql | docker exec -i bharatdoc-postgres psql -U bharatdoc -d bharatdoc
```

Then:

```powershell
# Seed database with sample data
cd analytics
$env:DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
python seed_data.py
```

You should see: ✅ Seeded 500 extraction logs

Then:

```powershell
# Start analytics service (keep this terminal open!)
python main.py
```

You should see: INFO: Uvicorn running on http://0.0.0.0:8002

---

### Step 3: Refresh Dashboard

1. Go to your browser: **http://localhost:3001**
2. Press **Ctrl + F5** (hard refresh)
3. Dashboard should now load with data! 🎉

---

## 🎯 Quick Verification

Before refreshing dashboard, open a **new PowerShell window** and test:

```powershell
# Test analytics API
curl http://localhost:8002/health
```

You should see:
```json
{"status":"healthy","database":"connected"}
```

If you see this, the dashboard will work!

---

## 📊 What You'll See

Once working, your dashboard will show:

- **Total Extractions**: 500
- **Average F1 Score**: ~0.88
- **Average Latency**: ~160ms
- **Total Errors**: 125
- **Charts**: Daily volume, model comparison, latency trends
- **Tables**: Field errors with percentages

---

## 🚨 Troubleshooting

### "Docker command not found"
- Install Docker Desktop: https://www.docker.com/products/docker-desktop/

### "Port 5432 already in use"
```powershell
docker stop bharatdoc-postgres
docker rm bharatdoc-postgres
```
Then retry Step 2.

### "Container already exists"
```powershell
docker start bharatdoc-postgres
```
Then continue from "Load database schema" in Step 2.

### Analytics won't start
- Make sure PostgreSQL is running: `docker ps`
- Make sure DATABASE_URL is set
- Check for errors in the terminal

---

## 💡 Keep Services Running

**Important**: Keep the analytics terminal open! If you close it, analytics stops.

To stop everything later:
1. Press **Ctrl+C** in analytics terminal
2. Run: `docker stop bharatdoc-postgres`

---

## 🎯 Summary

1. ✅ Start Docker Desktop (wait for it to fully start)
2. ✅ Run PostgreSQL container
3. ✅ Load schema and seed data
4. ✅ Start analytics service
5. ✅ Refresh dashboard (Ctrl+F5)

**That's it!** Your dashboard will work.

---

**Need help?** Check if Docker is running: `docker ps`
If you see containers listed, Docker is working!
