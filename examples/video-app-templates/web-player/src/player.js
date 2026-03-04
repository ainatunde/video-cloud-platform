// Video.js + HLS.js player initialization
// Reads HLS_URL from URL params or config panel

(function () {
  'use strict';

  var player = null;
  var hls = null;

  // Read HLS URL from query string if provided
  var params = new URLSearchParams(window.location.search);
  var initialUrl = params.get('url');
  if (initialUrl) {
    document.getElementById('stream-url').value = initialUrl;
  }

  function initPlayer(streamUrl) {
    // Destroy existing player instance if any
    if (player) {
      player.dispose();
      player = null;
    }
    if (hls) {
      hls.destroy();
      hls = null;
    }

    // Initialize Video.js
    player = videojs('video-player', {
      fluid: true,
      aspectRatio: '16:9',
      autoplay: false,
      muted: false,
      controls: true,
      preload: 'auto',
      html5: {
        vhs: {
          overrideNative: !videojs.browser.IS_SAFARI,
          enableLowInitialPlaylist: true,
        },
      },
    });

    // Use native HLS on Safari; use hls.js on other browsers
    if (Hls.isSupported()) {
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 90,
        maxBufferLength: 30,
        maxMaxBufferLength: 600,
      });

      hls.loadSource(streamUrl);
      hls.attachMedia(player.tech().el());

      hls.on(Hls.Events.MANIFEST_PARSED, function () {
        player.play().catch(function () {
          console.log('Autoplay blocked by browser policy');
        });
      });

      hls.on(Hls.Events.ERROR, function (event, data) {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.error('Fatal network error — attempting recovery');
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.error('Fatal media error — attempting recovery');
              hls.recoverMediaError();
              break;
            default:
              console.error('Fatal HLS error — cannot recover', data);
              hls.destroy();
              break;
          }
        }
      });
    } else if (player.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      player.src({ type: 'application/vnd.apple.mpegurl', src: streamUrl });
      player.play().catch(function () {});
    } else {
      alert('HLS is not supported in this browser.');
    }

    // Stats update loop
    startStatsLoop();
  }

  function startStatsLoop() {
    var statsInterval = setInterval(function () {
      if (!player || !hls) {
        clearInterval(statsInterval);
        return;
      }
      updateStats();
    }, 1000);
  }

  function updateStats() {
    if (!hls) return;

    var level = hls.levels[hls.currentLevel];
    if (level) {
      var width = level.width || '—';
      var height = level.height || '—';
      var bitrate = level.bitrate ? Math.round(level.bitrate / 1000) + ' kbps' : '—';
      document.getElementById('stat-resolution').textContent = width + 'x' + height;
      document.getElementById('stat-bitrate').textContent = bitrate;
    }

    if (player) {
      var buffered = player.buffered();
      var currentTime = player.currentTime();
      if (buffered.length > 0) {
        var bufferEnd = buffered.end(buffered.length - 1);
        var bufferAhead = (bufferEnd - currentTime).toFixed(1);
        document.getElementById('stat-buffer').textContent = bufferAhead + 's';
      }
    }
  }

  // Global functions for HTML buttons
  window.loadStream = function () {
    var url = document.getElementById('stream-url').value.trim();
    if (!url) {
      alert('Please enter a stream URL');
      return;
    }

    var adsEnabled = document.getElementById('ads-enabled').checked;
    var adUrl = document.getElementById('ad-url').value.trim();

    if (adsEnabled && adUrl && window.initAds) {
      window.initAds(url, adUrl, initPlayer);
    } else {
      initPlayer(url);
    }
  };

  window.toggleStats = function () {
    document.getElementById('show-stats').checked =
      !document.getElementById('show-stats').checked;
    var overlay = document.getElementById('stats-overlay');
    overlay.classList.toggle('visible', document.getElementById('show-stats').checked);
  };

  // Auto-load on page start if URL param provided
  if (initialUrl) {
    window.loadStream();
  }
})();
