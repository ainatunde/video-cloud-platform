/**
 * Ad Insertion Service — Express application entry point
 * =========================================================
 * Provides SSAI ad decision, VAST serving, and impression/click tracking.
 */

'use strict';

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { v4: uuidv4 } = require('uuid');

const logger = require('./logger');
const AdDecisionServer = require('./ad-decision-server');
const VastParser = require('./vast-parser');
const SSAIEngine = require('./ssai-engine');

const PORT = parseInt(process.env.PORT || '3000', 10);
const NODE_ENV = process.env.NODE_ENV || 'development';

const app = express();

// ── Middleware ────────────────────────────────────────────────────────────────

app.use(helmet());
app.use(cors());
app.use(compression()); // gzip response bodies
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

// Assign request IDs for tracing
app.use((req, _res, next) => {
  req.id = uuidv4();
  next();
});

// Request logging
app.use((req, _res, next) => {
  logger.info({ id: req.id, method: req.method, url: req.url });
  next();
});

// Global rate limiter
app.use(
  rateLimit({
    windowMs: 60_000,
    max: 500,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many requests' },
  })
);

// ── Singletons ────────────────────────────────────────────────────────────────

const adDecisionServer = new AdDecisionServer();
const vastParser = new VastParser();
const ssaiEngine = new SSAIEngine();

// ── Routes ───────────────────────────────────────────────────────────────────

/**
 * GET /health
 * Liveness probe — returns 200 with service status.
 */
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'ad-insertion',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

/**
 * POST /ads/decision
 * Make an ad decision based on SCTE-35 splice context and YOLO content analysis.
 *
 * Body: {
 *   splice_event_id: number,
 *   duration_seconds: number,
 *   pts_seconds: number,
 *   content_categories: string[],
 *   stream_id: string,
 * }
 */
app.post('/ads/decision', async (req, res) => {
  try {
    const context = req.body;
    const decision = await adDecisionServer.decideAd(context);
    res.json(decision);
  } catch (err) {
    logger.error({ id: req.id, err: err.message }, 'Ad decision failed');
    res.status(500).json({ error: 'Ad decision failed', detail: err.message });
  }
});

/**
 * GET /ads/vast/:ad_id
 * Serve a VAST XML document for the requested ad ID.
 */
app.get('/ads/vast/:ad_id', async (req, res) => {
  try {
    const { ad_id } = req.params;
    const vast = vastParser.buildVastResponse({ ad_id });
    res.set('Content-Type', 'application/xml; charset=utf-8');
    res.send(vast);
  } catch (err) {
    logger.error({ id: req.id, err: err.message }, 'VAST serving failed');
    res.status(500).send('<VAST version="3.0"/>');
  }
});

/**
 * POST /ads/impression/:ad_id
 * Record a view impression for an ad.
 */
app.post('/ads/impression/:ad_id', async (req, res) => {
  try {
    const { ad_id } = req.params;
    const { stream_id, position_ms, tracking_urls } = req.body || {};
    await ssaiEngine.trackImpressions(ad_id, Array.isArray(tracking_urls) ? tracking_urls : []);
    logger.info({ ad_id, stream_id, position_ms }, 'Impression recorded');
    res.status(204).send();
  } catch (err) {
    logger.error({ id: req.id, err: err.message }, 'Impression tracking failed');
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /ads/click/:ad_id
 * Record a click-through for an ad.
 */
app.post('/ads/click/:ad_id', async (req, res) => {
  try {
    const { ad_id } = req.params;
    const { stream_id } = req.body || {};
    logger.info({ ad_id, stream_id }, 'Click recorded');
    res.status(204).send();
  } catch (err) {
    logger.error({ id: req.id, err: err.message }, 'Click tracking failed');
    res.status(500).json({ error: err.message });
  }
});

// ── 404 handler ───────────────────────────────────────────────────────────────

app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// ── Error handler ─────────────────────────────────────────────────────────────

// eslint-disable-next-line no-unused-vars
app.use((err, req, res, _next) => {
  logger.error({ id: req.id, err: err.message, stack: err.stack }, 'Unhandled error');
  res.status(500).json({ error: 'Internal server error' });
});

// ── Start ─────────────────────────────────────────────────────────────────────

const server = app.listen(PORT, () => {
  logger.info(`Ad Insertion Service listening on port ${PORT} (${NODE_ENV})`);
});

// Graceful shutdown
const shutdown = (signal) => {
  logger.info(`Received ${signal}, shutting down…`);
  server.close(() => {
    logger.info('HTTP server closed');
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10_000);
};
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

module.exports = app; // exported for testing
