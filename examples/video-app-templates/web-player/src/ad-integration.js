// Google IMA SDK integration
// Sets up pre-roll and mid-roll ad breaks
// Handles ad errors gracefully (falls through to content)

(function () {
  'use strict';

  var adsManager = null;
  var adsLoader = null;
  var adDisplayContainer = null;
  var contentPauseRequested = false;

  function createAdsLoader(adContainer) {
    adDisplayContainer = new google.ima.AdDisplayContainer(adContainer);

    adsLoader = new google.ima.AdsLoader(adDisplayContainer);

    adsLoader.addEventListener(
      google.ima.AdsManagerLoadedEvent.Type.ADS_MANAGER_LOADED,
      onAdsManagerLoaded,
      false
    );

    adsLoader.addEventListener(
      google.ima.AdErrorEvent.Type.AD_ERROR,
      onAdError,
      false
    );
  }

  function requestAds(vastUrl, videoElement) {
    adDisplayContainer.initialize();

    var adsRequest = new google.ima.AdsRequest();
    adsRequest.adTagUrl = vastUrl;

    // Match ad display container size to video
    adsRequest.linearAdSlotWidth = videoElement.clientWidth || 640;
    adsRequest.linearAdSlotHeight = videoElement.clientHeight || 360;
    adsRequest.nonLinearAdSlotWidth = videoElement.clientWidth || 640;
    adsRequest.nonLinearAdSlotHeight = Math.floor((videoElement.clientHeight || 360) / 3);

    adsLoader.requestAds(adsRequest);
  }

  function onAdsManagerLoaded(adsManagerLoadedEvent) {
    var adsRenderingSettings = new google.ima.AdsRenderingSettings();
    adsRenderingSettings.restoreCustomPlaybackStateOnAdBreakComplete = true;

    adsManager = adsManagerLoadedEvent.getAdsManager(
      document.getElementById('video-player'),
      adsRenderingSettings
    );

    adsManager.addEventListener(google.ima.AdErrorEvent.Type.AD_ERROR, onAdError);
    adsManager.addEventListener(google.ima.AdEvent.Type.CONTENT_PAUSE_REQUESTED, onContentPauseRequested);
    adsManager.addEventListener(google.ima.AdEvent.Type.CONTENT_RESUME_REQUESTED, onContentResumeRequested);
    adsManager.addEventListener(google.ima.AdEvent.Type.ALL_ADS_COMPLETED, onAllAdsCompleted);
    adsManager.addEventListener(google.ima.AdEvent.Type.STARTED, onAdStarted);
    adsManager.addEventListener(google.ima.AdEvent.Type.COMPLETE, onAdComplete);

    try {
      var videoEl = document.querySelector('#video-player video') ||
                    document.getElementById('video-player');
      adsManager.init(
        videoEl.clientWidth || 640,
        videoEl.clientHeight || 360,
        google.ima.ViewMode.NORMAL
      );
      adsManager.start();
    } catch (adError) {
      console.warn('IMA ads manager init failed, falling through to content:', adError);
      onAdError({ getError: function () { return adError; } });
    }
  }

  function onAdError(adErrorEvent) {
    console.warn('Ad error:', adErrorEvent.getError ? adErrorEvent.getError() : adErrorEvent);
    if (adsManager) {
      adsManager.destroy();
    }
    // Fall through to content — this is the key resilience feature
    if (window._adFallbackCallback) {
      window._adFallbackCallback();
    }
  }

  function onContentPauseRequested() {
    contentPauseRequested = true;
    var videoEl = document.querySelector('#video-player video');
    if (videoEl) videoEl.pause();
  }

  function onContentResumeRequested() {
    contentPauseRequested = false;
    var videoEl = document.querySelector('#video-player video');
    if (videoEl) videoEl.play().catch(function () {});
  }

  function onAllAdsCompleted() {
    if (adsManager) {
      adsManager.destroy();
    }
  }

  function onAdStarted() {
    console.log('Ad started');
  }

  function onAdComplete() {
    console.log('Ad completed');
  }

  // Public initialization function called from player.js
  window.initAds = function (streamUrl, vastUrl, contentLoadCallback) {
    // Check if IMA SDK loaded
    if (typeof google === 'undefined' || !google.ima) {
      console.warn('Google IMA SDK not loaded, skipping ads');
      contentLoadCallback(streamUrl);
      return;
    }

    var playerWrapper = document.querySelector('.player-wrapper');
    if (!playerWrapper) {
      contentLoadCallback(streamUrl);
      return;
    }

    // Create ad container div overlaid on player
    var adContainer = document.getElementById('ad-container');
    if (!adContainer) {
      adContainer = document.createElement('div');
      adContainer.id = 'ad-container';
      adContainer.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;z-index:10;';
      playerWrapper.appendChild(adContainer);
    }

    // Set fallback: load content if ads fail
    window._adFallbackCallback = function () {
      contentLoadCallback(streamUrl);
    };

    createAdsLoader(adContainer);

    // Load content first (IMA will pause it for pre-roll)
    contentLoadCallback(streamUrl);

    // Request ads after content is initialized
    setTimeout(function () {
      var videoEl = document.querySelector('#video-player video');
      if (videoEl) {
        requestAds(vastUrl, videoEl);
      }
    }, 500);
  };
})();
