/**
 * Third-Party Ad Server Integrations
 * ====================================
 * Provides typed clients for Google Ad Manager, SpotX, and a generic VAST
 * fallback.  Each client exposes requestAd() and reportImpression().
 */

'use strict';

const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const logger = require('./logger');

// ── Google Ad Manager ─────────────────────────────────────────────────────────

class GoogleAdManagerClient {
  /**
   * @param {string} vastTagUrl  GAM VAST tag URL (from ad-servers.json or env).
   * @param {number} timeoutMs   Request timeout in milliseconds.
   */
  constructor(vastTagUrl, timeoutMs = 2000) {
    this._vastTagUrl = vastTagUrl;
    this._timeout = timeoutMs;
  }

  /**
   * Request an ad from Google Ad Manager.
   *
   * @param {Object} params
   * @param {number} params.duration_seconds
   * @param {string[]} params.content_categories
   * @param {string} params.stream_id
   * @returns {Promise<Object[]>} Array of ad candidates.
   */
  async requestAd({ duration_seconds, content_categories, stream_id }) {
    if (!this._vastTagUrl) {
      logger.warn('GoogleAdManagerClient: no VAST tag URL configured');
      return [];
    }

    try {
      const url = new URL(this._vastTagUrl);
      url.searchParams.set('sz', '1280x720');
      url.searchParams.set('dur', duration_seconds);
      url.searchParams.set('cust_params', `cat=${content_categories.join(',')}&sid=${stream_id}`);
      url.searchParams.set('correlator', Date.now());

      const resp = await axios.get(url.toString(), {
        timeout: this._timeout,
        headers: { Accept: 'application/xml' },
      });

      return [
        {
          ad_id: uuidv4(),
          vast_url: url.toString(),
          vast_xml: resp.data,
          duration: duration_seconds,
          source: 'google_ad_manager',
        },
      ];
    } catch (err) {
      logger.warn({ err: err.message }, 'GoogleAdManagerClient.requestAd failed');
      return [];
    }
  }

  /**
   * Report an impression to Google Ad Manager.
   *
   * @param {string} adId
   * @param {string} impressionUrl
   * @returns {Promise<void>}
   */
  async reportImpression(adId, impressionUrl) {
    if (!impressionUrl) return;
    try {
      await axios.get(impressionUrl, { timeout: 3000 });
      logger.debug({ adId }, 'GAM impression reported');
    } catch (err) {
      logger.warn({ adId, err: err.message }, 'GAM impression report failed');
    }
  }
}

// ── SpotX ─────────────────────────────────────────────────────────────────────

class SpotXClient {
  /**
   * @param {string} vastTagUrl  SpotX VAST tag URL.
   * @param {number} timeoutMs   Request timeout in milliseconds.
   */
  constructor(vastTagUrl, timeoutMs = 2000) {
    this._vastTagUrl = vastTagUrl;
    this._timeout = timeoutMs;
  }

  /**
   * Request an ad from SpotX.
   *
   * @param {Object} params
   * @param {number} params.duration_seconds
   * @param {string[]} params.content_categories
   * @param {string} params.stream_id
   * @returns {Promise<Object[]>}
   */
  async requestAd({ duration_seconds, content_categories, stream_id }) {
    if (!this._vastTagUrl) {
      logger.warn('SpotXClient: no VAST tag URL configured');
      return [];
    }

    try {
      const url = new URL(this._vastTagUrl);
      url.searchParams.set('VPI', 'MP4');
      url.searchParams.set('ad_mute', '0');
      url.searchParams.set('dur', duration_seconds);
      url.searchParams.set('iab_cat', content_categories.join(','));
      url.searchParams.set('cb', Date.now());

      const resp = await axios.get(url.toString(), {
        timeout: this._timeout,
        headers: { Accept: 'application/xml' },
      });

      return [
        {
          ad_id: uuidv4(),
          vast_url: url.toString(),
          vast_xml: resp.data,
          duration: duration_seconds,
          source: 'spotx',
        },
      ];
    } catch (err) {
      logger.warn({ err: err.message }, 'SpotXClient.requestAd failed');
      return [];
    }
  }

  /**
   * Report an impression to SpotX.
   *
   * @param {string} adId
   * @param {string} impressionUrl
   * @returns {Promise<void>}
   */
  async reportImpression(adId, impressionUrl) {
    if (!impressionUrl) return;
    try {
      await axios.get(impressionUrl, { timeout: 3000 });
      logger.debug({ adId }, 'SpotX impression reported');
    } catch (err) {
      logger.warn({ adId, err: err.message }, 'SpotX impression report failed');
    }
  }
}

// ── Generic VAST Client ───────────────────────────────────────────────────────

class GenericVASTClient {
  constructor(vastTagUrl, name = 'generic', timeoutMs = 2000) {
    this._vastTagUrl = vastTagUrl;
    this._name = name;
    this._timeout = timeoutMs;
  }

  async requestAd({ duration_seconds, content_categories, stream_id }) {
    if (!this._vastTagUrl) return [];
    try {
      const url = new URL(this._vastTagUrl);
      url.searchParams.set('dur', duration_seconds);
      url.searchParams.set('cat', content_categories.join(','));

      const resp = await axios.get(url.toString(), {
        timeout: this._timeout,
        headers: { Accept: 'application/xml' },
      });

      return [
        {
          ad_id: uuidv4(),
          vast_url: url.toString(),
          vast_xml: resp.data,
          duration: duration_seconds,
          source: this._name,
        },
      ];
    } catch (err) {
      logger.warn({ err: err.message, name: this._name }, 'GenericVASTClient.requestAd failed');
      return [];
    }
  }

  async reportImpression(_adId, _impressionUrl) {}
}

// ── Factory / registry ────────────────────────────────────────────────────────

class ThirdPartyIntegration {
  constructor() {
    const adServersConfig = require('../config/ad-servers.json');
    this._clients = {};

    for (const server of adServersConfig.ad_servers) {
      if (!server.enabled) continue;

      switch (server.name) {
        case 'google_ad_manager':
          this._clients[server.name] = new GoogleAdManagerClient(server.url, server.timeout_ms);
          break;
        case 'spotx':
          this._clients[server.name] = new SpotXClient(server.url, server.timeout_ms);
          break;
        default:
          if (server.url) {
            this._clients[server.name] = new GenericVASTClient(server.url, server.name, server.timeout_ms);
          }
      }
    }
  }

  getClient(name) {
    return this._clients[name] || null;
  }
}

module.exports = ThirdPartyIntegration;
module.exports.GoogleAdManagerClient = GoogleAdManagerClient;
module.exports.SpotXClient = SpotXClient;
module.exports.GenericVASTClient = GenericVASTClient;
