# BharatDoc Dashboard - Setup Guide

## Quick Start Commands

### 1. Install Dependencies
```bash
cd apps/dashboard
npm install
```

### 2. Run in Development Mode
```bash
npm run dev
```
Dashboard will be available at: http://localhost:3000

### 3. Build for Production
```bash
npm run build
```

### 4. Preview Production Build
```bash
npm run preview
```

## Docker Deployment

### Build and Run with Docker Compose
```bash
cd docker
docker-compose up dashboard
```

Dashboard will be available at: http://localhost:3000

### Build Docker Image Standalone
```bash
cd apps/dashboard
docker build -t bharatdoc-dashboard .
docker run -p 3000:80 bharatdoc-dashboard
```

## Git Commands

### Add all dashboard files to git
```bash
git add apps/dashboard/
git add docker/docker-compose.yml
```

### Commit with proper message
```bash
git commit -m "feat: add production-ready React TypeScript dashboard

- Complete analytics dashboard with real-time metrics
- Document extraction interface with drag-and-drop
- Recharts visualizations for all analytics endpoints
- Dark theme UI with Tailwind CSS
- Docker support with nginx proxy
- Auto-refresh every 30 seconds
- Responsive design for mobile and desktop"
```

## Verification Checklist

- [ ] Backend services running (gateway:8000, analytics:8002)
- [ ] Node.js 18+ installed
- [ ] npm install completed without errors
- [ ] Dev server starts successfully
- [ ] Dashboard loads at localhost:3000
- [ ] Can navigate between Dashboard and Extract pages
- [ ] Analytics charts display data
- [ ] Document upload works
- [ ] No console errors

## Troubleshooting

### Port Already in Use
```bash
# Change port in vite.config.ts
server: {
  port: 3001,  // Change to different port
  ...
}
```

### API Connection Failed
- Ensure gateway is running on port 8000
- Ensure analytics is running on port 8002
- Check browser console for CORS errors

### Build Errors
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

1. Start backend services (gateway and analytics)
2. Install dashboard dependencies
3. Run development server
4. Open http://localhost:3000
5. Test document extraction
6. View analytics dashboard
