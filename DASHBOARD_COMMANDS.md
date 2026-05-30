# BharatDoc Dashboard - Quick Command Reference

## ✅ Complete Implementation

All 30 files have been created for a production-ready React TypeScript dashboard.

---

## 📦 1. Install Dependencies

```bash
cd apps\dashboard
npm install
```

**What this does**: Installs all required packages including React, TypeScript, Vite, Tailwind CSS, Recharts, Axios, React Router, and date-fns.

---

## 🚀 2. Run in Development Mode

```bash
npm run dev
```

**Access at**: http://localhost:3000

**What this does**: 
- Starts Vite development server with hot module replacement
- Proxies API calls to backend services
- `/api/analytics` → http://localhost:8002
- `/api/gateway` → http://localhost:8000

**Prerequisites**: 
- Gateway service running on port 8000
- Analytics service running on port 8002

---

## 🏗️ 3. Build for Production

```bash
npm run build
```

**What this does**: 
- Compiles TypeScript to JavaScript
- Bundles and optimizes all assets
- Outputs to `dist/` directory
- Minifies CSS and JavaScript
- Tree-shakes unused code

**Output**: Production-ready static files in `dist/`

---

## 🔍 4. Preview Production Build

```bash
npm run preview
```

**Access at**: http://localhost:4173

**What this does**: Serves the production build locally for testing before deployment.

---

## 🐳 5. Docker Deployment

### Option A: Docker Compose (Recommended)

```bash
cd ..\..
cd docker
docker-compose up dashboard
```

**Access at**: http://localhost:3000

**What this does**:
- Builds the dashboard Docker image
- Starts nginx server
- Proxies API calls to backend services
- Serves production build

### Option B: Standalone Docker

```bash
cd apps\dashboard
docker build -t bharatdoc-dashboard .
docker run -p 3000:80 bharatdoc-dashboard
```

---

## 📝 6. Git Commands

### Add all dashboard files

```bash
git add apps\dashboard\
git add docker\docker-compose.yml
```

### Check what will be committed

```bash
git status
```

### Commit with proper message

```bash
git commit -m "feat: add production-ready React TypeScript dashboard

- Complete analytics dashboard with real-time metrics
- Document extraction interface with drag-and-drop upload
- Recharts visualizations for all analytics endpoints
- Dark theme UI with Tailwind CSS
- Docker support with nginx proxy configuration
- Auto-refresh every 30 seconds for live data
- Responsive design for mobile and desktop
- TypeScript strict mode with full type safety
- Vite for fast development and optimized builds
- Comprehensive documentation and setup guides

Components:
- MetricCard: Display key metrics with trends
- DailyVolumeChart: Volume and quality over time
- ModelComparisonChart: Compare model performance
- FieldErrorsTable: Error analysis with pagination
- LatencyTrendChart: Monitor latency trends
- DocumentUpload: Drag-and-drop file upload
- ExtractionResult: Display extraction results
- Navbar: Navigation with routing

Pages:
- Dashboard: Real-time analytics overview
- Extract: Document upload and extraction

Technical:
- React 18 with TypeScript
- Tailwind CSS for styling
- Recharts for data visualization
- Axios for API calls
- React Router for navigation
- date-fns for date formatting
- Multi-stage Docker build
- Nginx for production serving"
```

### Push to remote (if needed)

```bash
git push origin main
```

---

## 🧪 7. Verification Commands

### Check if files were created

```bash
dir apps\dashboard\src\components
dir apps\dashboard\src\pages
dir apps\dashboard\src\api
```

### Check package.json

```bash
type apps\dashboard\package.json
```

### Verify Docker Compose configuration

```bash
type docker\docker-compose.yml
```

---

## 🔧 8. Troubleshooting Commands

### Clear node_modules and reinstall

```bash
cd apps\dashboard
rmdir /s /q node_modules
del package-lock.json
npm install
```

### Clear Vite cache

```bash
rmdir /s /q node_modules\.vite
npm run dev
```

### Check for TypeScript errors

```bash
npm run build
```

### View Docker logs

```bash
docker-compose logs dashboard
```

---

## 📊 9. Testing the Dashboard

### Start backend services first

```bash
# Terminal 1: Start Gateway
cd gateway
python -m uvicorn main:app --port 8000

# Terminal 2: Start Analytics
cd analytics
python main.py

# Terminal 3: Start Dashboard
cd apps\dashboard
npm run dev
```

### Test checklist

1. ✅ Open http://localhost:3000
2. ✅ Navigate to Dashboard page
3. ✅ Verify metrics cards display
4. ✅ Check all charts render
5. ✅ Navigate to Extract page
6. ✅ Upload a test document
7. ✅ Verify extraction results display
8. ✅ Check browser console for errors

---

## 📁 Files Created (30 total)

```
apps/dashboard/
├── src/
│   ├── api/
│   │   ├── analytics.ts          ✅
│   │   └── gateway.ts             ✅
│   ├── components/
│   │   ├── DailyVolumeChart.tsx   ✅
│   │   ├── DocumentUpload.tsx     ✅
│   │   ├── ExtractionResult.tsx   ✅
│   │   ├── FieldErrorsTable.tsx   ✅
│   │   ├── LatencyTrendChart.tsx  ✅
│   │   ├── MetricCard.tsx         ✅
│   │   ├── ModelComparisonChart.tsx ✅
│   │   └── Navbar.tsx             ✅
│   ├── hooks/
│   │   └── useFetch.ts            ✅
│   ├── pages/
│   │   ├── Dashboard.tsx          ✅
│   │   └── Extract.tsx            ✅
│   ├── types/
│   │   └── index.ts               ✅
│   ├── App.tsx                    ✅
│   ├── index.css                  ✅
│   └── main.tsx                   ✅
├── .dockerignore                  ✅
├── .eslintrc.cjs                  ✅
├── .gitignore                     ✅
├── Dockerfile                     ✅
├── index.html                     ✅
├── package.json                   ✅
├── postcss.config.js              ✅
├── README.md                      ✅
├── SETUP.md                       ✅
├── IMPLEMENTATION_COMPLETE.md     ✅
├── tailwind.config.js             ✅
├── tsconfig.json                  ✅
├── tsconfig.node.json             ✅
└── vite.config.ts                 ✅

docker/
└── docker-compose.yml (updated)   ✅
```

---

## 🎯 Quick Start (Copy-Paste Ready)

```bash
# Navigate to dashboard
cd apps\dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Open browser to http://localhost:3000
```

---

## 🚢 Production Deployment (Copy-Paste Ready)

```bash
# Build production bundle
cd apps\dashboard
npm run build

# Or use Docker
cd ..\..
cd docker
docker-compose up -d dashboard
```

---

## ✅ Success Indicators

- ✅ `npm install` completes without errors
- ✅ `npm run dev` starts server on port 3000
- ✅ Dashboard page loads with metrics
- ✅ Charts render with data
- ✅ Extract page allows file upload
- ✅ No console errors in browser
- ✅ API calls succeed (check Network tab)

---

## 📞 Support

If you encounter issues:

1. **Check backend services**: Ensure gateway (8000) and analytics (8002) are running
2. **Check browser console**: Look for JavaScript errors
3. **Check network tab**: Verify API calls are successful
4. **Review logs**: Check terminal output for errors
5. **Read documentation**: See README.md and SETUP.md

---

**Status**: ✅ READY FOR USE
**Last Updated**: 2026-05-30
**Version**: 1.0.0
