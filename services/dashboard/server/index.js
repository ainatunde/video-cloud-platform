'use strict';

const express = require('express');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Health check
app.get('/health', (req, res) => res.json({ status: 'ok', timestamp: new Date().toISOString() }));

// API proxy to backend services
app.use(
  '/api/streams',
  createProxyMiddleware({
    target: process.env.SRS_API_URL || 'http://srs:1985',
    changeOrigin: true,
    pathRewrite: { '^/api/streams': '/api/v1/streams' },
  }),
);

app.use(
  '/api/transcode',
  createProxyMiddleware({
    target: process.env.TRANSCODER_URL || 'http://ffmpeg-transcoder:8002',
    changeOrigin: true,
  }),
);

app.use(
  '/api/ads',
  createProxyMiddleware({
    target: process.env.AD_SERVER_URL || 'http://ad-server:3000',
    changeOrigin: true,
  }),
);

app.use(
  '/api/scte35',
  createProxyMiddleware({
    target: process.env.SCTE35_URL || 'http://scte35-processor:8001',
    changeOrigin: true,
  }),
);

app.use(
  '/api/analytics',
  createProxyMiddleware({
    target: process.env.ANALYTICS_URL || 'http://timescaledb:5432',
    changeOrigin: true,
  }),
);

// Serve React app
app.use(express.static(path.join(__dirname, '../dist')));

// SPA fallback
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../dist/index.html'));
});

app.listen(PORT, () => {
  console.log(`Dashboard server running on port ${PORT}`);
});
