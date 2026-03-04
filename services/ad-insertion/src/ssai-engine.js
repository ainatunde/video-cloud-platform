/**
 * SSAI Engine
 * ===========
 * Server-Side Ad Insertion: stitches ad segments into live HLS manifests at
 * SCTE-35 splice points and fires impression tracking beacons.
 */

'use strict';

const axios = require('axios');
const logger = require('./logger');

class SSAIEngine {
  /**
   * Stitch an ad into a stream at the given splice point.
   *
   * In a production implementation this would:
   * 1. Fetch and transcode ad to match the ABR ladder
   * 2. Replace HLS segments in the splice window
   * 3. Update the manifest
   *
   * @param {string} streamUrl    HLS manifest URL of the main content.
   * @param {string} adUrl        HLS manifest URL of the ad.
   * @param {number} splicePoint  PTS in seconds where the splice occurs.
   * @returns {Promise<Object>}   Stitched manifest information.
   */
  async stitchAd(streamUrl, adUrl, splicePoint) {
    logger.info({ streamUrl, adUrl, splicePoint }, 'Stitching ad into stream');
    // Placeholder: in production, fetch both manifests, compute segment overlap,
    // and build a combined manifest.
    return {
      stitched: true,
      stream_url: streamUrl,
      ad_url: adUrl,
      splice_point: splicePoint,
      stitched_manifest: `${streamUrl}?ad=${encodeURIComponent(adUrl)}&t=${splicePoint}`,
    };
  }

  /**
   * Replace HLS segments in the manifest between spliceInPts and spliceOutPts
   * with the provided ad segments list.
   *
   * @param {string}   hlsManifest    Content of the HLS variant playlist.
   * @param {string[]} adSegments     Array of ad segment URLs.
   * @param {number}   spliceInPts    Cue-out PTS in seconds.
   * @param {number}   spliceOutPts   Cue-in PTS in seconds.
   * @returns {string} Modified HLS manifest content.
   */
  replaceSegments(hlsManifest, adSegments, spliceInPts, spliceOutPts) {
    if (!hlsManifest || !adSegments.length) return hlsManifest;

    const lines = hlsManifest.split('\n');
    const result = [];
    let inSplice = false;
    let currentPts = 0;

    for (const line of lines) {
      // Track running PTS from EXTINF duration values
      if (line.startsWith('#EXTINF:')) {
        const dur = parseFloat(line.slice(8));
        if (!isNaN(dur)) {
          if (currentPts >= spliceInPts && currentPts < spliceOutPts) {
            // We're inside the splice window — skip content segments
            inSplice = true;
          } else {
            inSplice = false;
          }
          currentPts += dur;
        }
      }

      if (inSplice) {
        // Skip content segment lines inside the splice window
        if (!line.startsWith('#')) continue;
      }

      result.push(line);
    }

    // Insert ad segments at the splice-in position
    const insertIdx = result.findIndex(
      (l) => l.startsWith('#EXT-X-DATERANGE') && l.includes('SCTE35-OUT')
    );
    if (insertIdx >= 0) {
      const adLines = adSegments.flatMap((segUrl) => [
        '#EXTINF:6.000,',
        segUrl,
      ]);
      result.splice(insertIdx + 1, 0, ...adLines);
    }

    return result.join('\n');
  }

  /**
   * Fire impression tracking beacons for an ad.
   *
   * @param {string}   adId          Ad identifier.
   * @param {string[]} trackingUrls  List of tracking beacon URLs to ping.
   * @returns {Promise<void>}
   */
  async trackImpressions(adId, trackingUrls) {
    if (!trackingUrls || !trackingUrls.length) {
      logger.debug({ adId }, 'No tracking URLs to ping');
      return;
    }

    const results = await Promise.allSettled(
      trackingUrls.map((url) =>
        axios.get(url, { timeout: 3000, headers: { 'User-Agent': 'VideoPlatform-SSAI/1.0' } })
      )
    );

    let fired = 0;
    for (const r of results) {
      if (r.status === 'fulfilled') {
        fired++;
      } else {
        logger.warn({ adId, err: r.reason?.message }, 'Tracking beacon failed');
      }
    }

    logger.info({ adId, fired, total: trackingUrls.length }, 'Impression beacons fired');
  }
}

module.exports = SSAIEngine;
