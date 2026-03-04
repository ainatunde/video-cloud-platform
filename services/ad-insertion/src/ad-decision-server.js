/**
 * Ad Decision Server
 * ==================
 * Selects the best ad for a SCTE-35 splice opportunity using context from
 * the YOLO content analyzer and third-party VAST ad servers.
 */

'use strict';

const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const logger = require('./logger');
const ThirdPartyIntegration = require('./third-party-integration');
const adServersConfig = require('../config/ad-servers.json');

class AdDecisionServer {
  constructor() {
    this._integration = new ThirdPartyIntegration();
  }

  /**
   * Decide which ad to serve for the given splice context.
   *
   * @param {Object} context
   * @param {number} context.splice_event_id
   * @param {number} context.duration_seconds
   * @param {number} context.pts_seconds
   * @param {string[]} [context.content_categories]
   * @param {string} [context.stream_id]
   * @returns {Promise<Object>} Ad decision including VAST URL and metadata.
   */
  async decideAd(context) {
    const {
      splice_event_id,
      duration_seconds = adServersConfig.default_ad_duration,
      pts_seconds,
      content_categories = [],
      stream_id = 'unknown',
    } = context;

    logger.info(
      { splice_event_id, duration_seconds, stream_id, content_categories },
      'Making ad decision'
    );

    // Gather candidates from enabled ad servers
    const candidates = await this._fetchCandidates({
      duration_seconds,
      content_categories,
      stream_id,
    });

    const best = this.selectBestAd(candidates, context);

    return {
      decision_id: uuidv4(),
      splice_event_id,
      ad_id: best?.ad_id || null,
      vast_url: best?.vast_url || null,
      duration_seconds: best?.duration || duration_seconds,
      pts_seconds,
      selected: best !== null,
    };
  }

  /**
   * Fetch ad candidates from all enabled ad server integrations.
   *
   * @private
   */
  async _fetchCandidates({ duration_seconds, content_categories, stream_id }) {
    const servers = adServersConfig.ad_servers.filter((s) => s.enabled);
    const results = await Promise.allSettled(
      servers.map((server) =>
        this._queryVASTServer(server, { duration_seconds, content_categories, stream_id })
      )
    );

    const candidates = [];
    for (const r of results) {
      if (r.status === 'fulfilled' && r.value) {
        candidates.push(...(Array.isArray(r.value) ? r.value : [r.value]));
      }
    }
    return candidates;
  }

  /**
   * Query a single VAST ad server for candidates.
   *
   * @param {Object} server  Ad server config entry.
   * @param {Object} params  Request parameters.
   * @returns {Promise<Object[]>}
   */
  async queryVASTServer(server, params) {
    return this._queryVASTServer(server, params);
  }

  async _queryVASTServer(server, { duration_seconds, content_categories, stream_id }) {
    if (server.type === 'local') {
      // Return a synthetic local ad for fill
      return [
        {
          ad_id: uuidv4(),
          vast_url: `/ads/vast/local-${uuidv4()}`,
          duration: duration_seconds,
          source: 'local',
          iab_categories: content_categories,
        },
      ];
    }

    if (!server.url) {
      logger.warn({ server: server.name }, 'Ad server URL not configured; skipping');
      return [];
    }

    try {
      const client = this._integration.getClient(server.name);
      if (client) {
        return await client.requestAd({ duration_seconds, content_categories, stream_id });
      }

      // Generic VAST URL query
      const url = new URL(server.url);
      url.searchParams.set('dur', duration_seconds);
      url.searchParams.set('cat', content_categories.join(','));
      url.searchParams.set('sid', stream_id);

      const resp = await axios.get(url.toString(), {
        timeout: server.timeout_ms || 2000,
        headers: { Accept: 'application/xml' },
      });

      return [
        {
          ad_id: uuidv4(),
          vast_url: url.toString(),
          vast_xml: resp.data,
          duration: duration_seconds,
          source: server.name,
        },
      ];
    } catch (err) {
      logger.warn({ server: server.name, err: err.message }, 'Ad server query failed');
      return [];
    }
  }

  /**
   * Select the best ad from a list of candidates using context-aware scoring.
   *
   * Scoring criteria:
   * - IAB category match (+10 per overlap)
   * - Local fill preference when fill_rate = 1.0
   *
   * @param {Object[]} candidates
   * @param {Object}   context
   * @returns {Object|null}
   */
  selectBestAd(candidates, context) {
    if (!candidates.length) return null;

    const targetCategories = new Set(context.content_categories || []);

    const scored = candidates.map((c) => {
      let score = 0;
      // IAB category overlap bonus
      const candCats = c.iab_categories || [];
      for (const cat of candCats) {
        if (targetCategories.has(cat)) score += 10;
      }
      // Prefer ads matching the requested duration
      const durDiff = Math.abs((c.duration || 30) - (context.duration_seconds || 30));
      score -= durDiff;
      return { ...c, _score: score };
    });

    scored.sort((a, b) => b._score - a._score);
    return scored[0];
  }
}

module.exports = AdDecisionServer;
