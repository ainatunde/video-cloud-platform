import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import Video, { OnLoadData, OnProgressData, OnBufferData } from 'react-native-video';

interface VideoPlayerProps {
  streamUrl: string;
  onQualityChange?: (quality: string) => void;
}

export default function VideoPlayer({ streamUrl, onQualityChange }: VideoPlayerProps): React.JSX.Element {
  const [paused, setPaused] = useState(false);
  const [muted, setMuted] = useState(false);
  const [buffering, setBuffering] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showControls, setShowControls] = useState(true);
  const videoRef = useRef<Video>(null);

  const handleLoad = (data: OnLoadData) => {
    setDuration(data.duration);
    setBuffering(false);
  };

  const handleProgress = (data: OnProgressData) => {
    setCurrentTime(data.currentTime);
  };

  const handleBuffer = (data: OnBufferData) => {
    setBuffering(data.isBuffering);
  };

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  const formatTime = (s: number): string => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const seek = (fraction: number) => {
    videoRef.current?.seek(fraction * duration);
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity
        activeOpacity={1}
        onPress={() => setShowControls(v => !v)}
        style={styles.videoWrapper}>

        <Video
          ref={videoRef}
          source={{ uri: streamUrl }}
          style={styles.video}
          resizeMode="contain"
          paused={paused}
          muted={muted}
          onLoad={handleLoad}
          onProgress={handleProgress}
          onBuffer={handleBuffer}
          controls={false}
          allowsExternalPlayback
          pictureInPicture
        />

        {/* Buffering indicator */}
        {buffering && (
          <View style={styles.bufferingOverlay}>
            <ActivityIndicator size="large" color="#60a5fa" />
            <Text style={styles.bufferingText}>Buffering…</Text>
          </View>
        )}

        {/* Controls overlay */}
        {showControls && (
          <View style={styles.controlsOverlay}>
            {/* Top bar */}
            <View style={styles.topBar}>
              <Text style={styles.topBarText} numberOfLines={1}>
                {streamUrl.split('/').pop()}
              </Text>
            </View>

            {/* Center controls */}
            <View style={styles.centerControls}>
              <TouchableOpacity
                onPress={() => videoRef.current?.seek(currentTime - 10)}
                style={styles.seekBtn}>
                <Text style={styles.seekText}>-10s</Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={() => setPaused(p => !p)}
                style={styles.playPauseBtn}>
                <Text style={styles.playPauseText}>{paused ? '▶' : '⏸'}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={() => videoRef.current?.seek(currentTime + 10)}
                style={styles.seekBtn}>
                <Text style={styles.seekText}>+10s</Text>
              </TouchableOpacity>
            </View>

            {/* Bottom bar */}
            <View style={styles.bottomBar}>
              {/* Progress bar */}
              <TouchableOpacity
                style={styles.progressContainer}
                onPress={e => {
                  const x = e.nativeEvent.locationX;
                  seek(x / e.nativeEvent.target);
                }}>
                <View style={styles.progressTrack}>
                  <View style={[styles.progressFill, { width: `${progressPercent}%` as `${number}%` }]} />
                </View>
              </TouchableOpacity>

              <View style={styles.bottomControls}>
                <Text style={styles.timeText}>
                  {formatTime(currentTime)} / {formatTime(duration)}
                </Text>

                <View style={styles.rightControls}>
                  <TouchableOpacity onPress={() => setMuted(m => !m)} style={styles.iconBtn}>
                    <Text style={styles.iconText}>{muted ? '🔇' : '🔊'}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={() => onQualityChange?.('720p')}
                    style={styles.qualityBtn}>
                    <Text style={styles.qualityText}>HD</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          </View>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#000',
    width: '100%',
    aspectRatio: 16 / 9,
  },
  videoWrapper: {
    flex: 1,
    position: 'relative',
  },
  video: {
    ...StyleSheet.absoluteFillObject,
  },
  bufferingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  bufferingText: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 8,
  },
  controlsOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
    backgroundColor: 'rgba(0,0,0,0.35)',
  },
  topBar: {
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  topBarText: {
    color: '#e2e8f0',
    fontSize: 13,
  },
  centerControls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 24,
  },
  seekBtn: { padding: 8 },
  seekText: { color: '#e2e8f0', fontSize: 14 },
  playPauseBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playPauseText: { color: '#fff', fontSize: 22 },
  bottomBar: {
    paddingHorizontal: 12,
    paddingBottom: 10,
  },
  progressContainer: {
    paddingVertical: 6,
  },
  progressTrack: {
    height: 3,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 2,
  },
  progressFill: {
    height: 3,
    backgroundColor: '#60a5fa',
    borderRadius: 2,
  },
  bottomControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  timeText: {
    color: '#cbd5e1',
    fontSize: 11,
    fontFamily: 'monospace',
  },
  rightControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconBtn: { padding: 4 },
  iconText: { fontSize: 16 },
  qualityBtn: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 4,
  },
  qualityText: {
    color: '#e2e8f0',
    fontSize: 11,
    fontWeight: '600',
  },
});
