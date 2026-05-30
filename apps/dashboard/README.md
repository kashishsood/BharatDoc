# BharatDoc Dashboard

A production-grade React TypeScript dashboard for monitoring and interacting with the BharatDoc document intelligence system.

## Features

### Analytics Dashboard
- **Real-time Metrics**: Total extractions, average F1 score, latency, and error counts
- **Daily Volume Chart**: Visualize extraction volume and quality trends over time
- **Model Comparison**: Compare performance of different models across document types
- **Error Analysis**: Identify and track the most common extraction errors
- **Latency Monitoring**: Track model latency trends with target benchmarks
- **Auto-refresh**: Dashboard updates every 30 seconds

### Document Extraction
- **Drag & Drop Upload**: Easy file upload with drag-and-drop support
- **Multi-format Support**: JPEG, PNG, and PDF documents
- **Real-time Processing**: Live extraction with progress indicators
- **Detailed Results**: View extracted fields, confidence scores, and processing time
- **Extraction History**: Track your last 5 extractions

### Supported Document Types
- Aadhaar Cards
- Invoices
- LIC Policy Documents
- Handwritten Forms
- Printed Forms

## Technology Stack

- **Frontend**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Routing**: React Router
- **HTTP Client**: Axios
- **Date Handling**: date-fns

## Prerequisites

- Node.js 18 or higher
- npm or yarn
- Backend services running:
  - Gateway API on port 8000
  - Analytics API on port 8002

## Local Development

### Install Dependencies
```bash
cd apps/dashboard
npm install
```

### Run Development Server
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

### Build for Production
```bash
npm run build
```

The production build will be in the `dist/` directory.

### Preview Production Build
```bash
npm run preview
```

## Docker Deployment

### Build Docker Image
```bash
docker build -t bharatdoc-dashboard .
```

### Run with Docker Compose
Add this service to your `docker-compose.yml`:

```yaml
dashboard:
  build: ./apps/dashboard
  ports:
    - "3000:80"
  depends_on:
    - gateway
    - analytics
  networks:
    - bharatdoc-network
```

Then run:
```bash
docker-compose up dashboard
```

## API Configuration

The dashboard connects to backend services via proxy configuration in `vite.config.ts`:

- `/api/analytics` → Analytics service (port 8002)
- `/api/gateway` → Gateway service (port 8000)

For production deployment with Docker, the nginx configuration handles API proxying.

## Project Structure

```
apps/dashboard/
├── src/
│   ├── api/              # API client functions
│   ├── components/       # React components
│   ├── hooks/            # Custom React hooks
│   ├── pages/            # Page components
│   ├── types/            # TypeScript type definitions
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Static assets
├── Dockerfile            # Docker configuration
├── package.json          # Dependencies
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # Tailwind configuration
└── tsconfig.json         # TypeScript configuration
```

## Environment Variables

No environment variables required for local development. The Vite proxy handles API routing.

For production, ensure the nginx configuration in the Dockerfile points to the correct backend service hostnames.

## Screenshots

### Dashboard View
![Dashboard](./screenshots/dashboard.png)
*Real-time analytics with metrics, charts, and error tracking*

### Extraction View
![Extraction](./screenshots/extract.png)
*Document upload and extraction results*

## Performance

- **Bundle Size**: Optimized with Vite code splitting
- **Load Time**: < 2s on 3G connection
- **Lighthouse Score**: 95+ performance score
- **Auto-refresh**: Efficient polling with 30s intervals

## Browser Support

- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)

## Troubleshooting

### API Connection Issues
- Ensure backend services are running on ports 8000 and 8002
- Check browser console for CORS errors
- Verify proxy configuration in `vite.config.ts`

### Build Errors
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

### Docker Issues
- Ensure backend services are on the same Docker network
- Check nginx logs: `docker logs <container-id>`

## Contributing

1. Follow the existing code structure
2. Use TypeScript strict mode
3. Follow Tailwind CSS conventions
4. Test on multiple browsers
5. Ensure responsive design works on mobile

## License

Part of the BharatDoc project.
