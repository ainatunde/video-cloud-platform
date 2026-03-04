/**
 * VAST Parser
 * ===========
 * Parses VAST 3/4 XML, extracts media files and tracking events, and
 * generates VAST XML responses for the ad server.
 */

'use strict';

const xml2js = require('xml2js');
const { v4: uuidv4 } = require('uuid');
const logger = require('./logger');

const VAST_VERSION = '3.0';

class VastParser {
  constructor() {
    this._parser = new xml2js.Parser({
      explicitArray: false,
      ignoreAttrs: false,
      mergeAttrs: true,
    });
    this._builder = new xml2js.Builder({ xmldec: { version: '1.0', encoding: 'UTF-8' } });
  }

  /**
   * Parse a VAST XML string into a JavaScript object.
   *
   * @param {string} xml  Raw VAST XML.
   * @returns {Promise<Object>} Parsed VAST object.
   */
  async parse(xml) {
    try {
      return await this._parser.parseStringPromise(xml);
    } catch (err) {
      logger.error({ err: err.message }, 'VAST parse error');
      throw new Error(`Failed to parse VAST: ${err.message}`);
    }
  }

  /**
   * Extract all MediaFile entries from a parsed VAST object.
   *
   * @param {Object} vast  Parsed VAST object from parse().
   * @returns {Object[]} Array of MediaFile descriptors.
   */
  extractMediaFiles(vast) {
    try {
      const ads = vast?.VAST?.Ad;
      const adArr = Array.isArray(ads) ? ads : [ads].filter(Boolean);
      const files = [];

      for (const ad of adArr) {
        const linear = ad?.InLine?.Creatives?.Creative?.Linear;
        if (!linear) continue;

        const mf = linear?.MediaFiles?.MediaFile;
        const mediaFiles = Array.isArray(mf) ? mf : [mf].filter(Boolean);

        for (const m of mediaFiles) {
          files.push({
            url: typeof m === 'string' ? m : (m?._ || m?.['#text'] || ''),
            type: m?.type || 'video/mp4',
            bitrate: parseInt(m?.bitrate || '0', 10),
            width: parseInt(m?.width || '0', 10),
            height: parseInt(m?.height || '0', 10),
            delivery: m?.delivery || 'progressive',
          });
        }
      }

      return files;
    } catch (err) {
      logger.warn({ err: err.message }, 'extractMediaFiles failed');
      return [];
    }
  }

  /**
   * Extract all TrackingEvent entries from a parsed VAST object.
   *
   * @param {Object} vast  Parsed VAST object.
   * @returns {Object[]} Array of { event, url } descriptors.
   */
  extractTrackingEvents(vast) {
    try {
      const ads = vast?.VAST?.Ad;
      const adArr = Array.isArray(ads) ? ads : [ads].filter(Boolean);
      const events = [];

      for (const ad of adArr) {
        const tracking = ad?.InLine?.Creatives?.Creative?.Linear?.TrackingEvents?.Tracking;
        const trackArr = Array.isArray(tracking) ? tracking : [tracking].filter(Boolean);

        for (const t of trackArr) {
          events.push({
            event: t?.event || t?.$?.event || 'unknown',
            url: typeof t === 'string' ? t : (t?._ || t?.['#text'] || ''),
          });
        }
      }

      return events;
    } catch (err) {
      logger.warn({ err: err.message }, 'extractTrackingEvents failed');
      return [];
    }
  }

  /**
   * Build a minimal VAST 3.0 XML response for a given ad.
   *
   * @param {Object} ad
   * @param {string} ad.ad_id        Unique ad ID.
   * @param {string} [ad.media_url]  Direct video URL.
   * @param {number} [ad.duration]   Duration in seconds.
   * @param {string} [ad.title]      Ad title.
   * @param {string} [ad.click_url]  Click-through URL.
   * @returns {string} VAST XML string.
   */
  buildVastResponse(ad) {
    const {
      ad_id = uuidv4(),
      media_url = '',
      duration = 30,
      title = 'Ad',
      click_url = '',
    } = ad;

    const vastObj = {
      VAST: {
        $: { version: VAST_VERSION },
        Ad: {
          $: { id: ad_id },
          InLine: {
            AdSystem: 'VideoPlatform',
            AdTitle: title,
            Impression: { $: { id: `imp-${ad_id}` }, _: `/ads/impression/${ad_id}` },
            Creatives: {
              Creative: {
                $: { id: `cr-${ad_id}` },
                Linear: {
                  Duration: _secondsToVastDuration(duration),
                  TrackingEvents: {
                    Tracking: [
                      { $: { event: 'start' }, _: `/ads/tracking/${ad_id}/start` },
                      { $: { event: 'firstQuartile' }, _: `/ads/tracking/${ad_id}/q1` },
                      { $: { event: 'midpoint' }, _: `/ads/tracking/${ad_id}/midpoint` },
                      { $: { event: 'thirdQuartile' }, _: `/ads/tracking/${ad_id}/q3` },
                      { $: { event: 'complete' }, _: `/ads/tracking/${ad_id}/complete` },
                    ],
                  },
                  VideoClicks: {
                    ClickThrough: { $: { id: `ct-${ad_id}` }, _: click_url || `#` },
                    ClickTracking: { $: { id: `ctr-${ad_id}` }, _: `/ads/click/${ad_id}` },
                  },
                  MediaFiles: {
                    MediaFile: {
                      $: {
                        delivery: 'progressive',
                        type: 'video/mp4',
                        bitrate: '1500',
                        width: '1280',
                        height: '720',
                      },
                      _: media_url || '',
                    },
                  },
                },
              },
            },
          },
        },
      },
    };

    return this._builder.buildObject(vastObj);
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _secondsToVastDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return [
    String(h).padStart(2, '0'),
    String(m).padStart(2, '0'),
    String(s).padStart(2, '0'),
  ].join(':');
}

module.exports = VastParser;
