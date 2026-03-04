import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Switch,
  ScrollView,
  Alert,
  StatusBar,
  SafeAreaView,
} from 'react-native';
import Video, { OnLoadData, OnProgressData, OnErrorData } from 'react-native-video';

const DEFAULT_STREAM_URL = 'http://localhost:8080/live/stream1.m3u8';
const DEFAULT_AD_URL = 'http://localhost:3000/ads/vast';

interface AppConfig {
  streamUrl: string;
  adsEnabled: boolean;
  analyticsEnabled: boolean;
  offlineCaching: boolean;
}

export default function App(): React.JSX.Element {
  const [config] = useState<AppConfig>({
    streamUrl: DEFAULT_STREAM_URL,
    adsEnabled: true,
    analyticsEnabled: true,
    offlineCaching: false,
  });

  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [quality, setQuality] = useState('Auto');
  const videoRef = useRef<Video>(null);

  const handleLoad = (data: OnLoadData) => {
    setDuration(data.duration);
    setPlaying(true);
    if (config.analyticsEnabled) {
      console.log('[Analytics] Stream loaded', {
        duration: data.duration,
        naturalSize: data.naturalSize,
      });
    }
  };

  const handleProgress = (data: OnProgressData) => {
    setCurrentTime(data.currentTime);
  };

  const handleError = (error: OnErrorData) => {
    Alert.alert('Playback Error', error.error?.localizedDescription || 'Unknown error');
    setPlaying(false);
  };

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

      <View style={styles.header}>
        <Text style={styles.headerTitle}>Video Cloud Platform</Text>
      </View>

      {/* Video Player */}
      <View style={styles.playerContainer}>
        <Video
          ref={videoRef}
          source={{ uri: config.streamUrl }}
          style={styles.video}
          resizeMode="contain"
          paused={!playing}
          muted={muted}
          onLoad={handleLoad}
          onProgress={handleProgress}
          onError={handleError}
          controls={false}
          allowsExternalPlayback
          pictureInPicture
          preferredForwardBufferDuration={30}
        />

        {/* Custom Controls Overlay */}
        <View style={styles.controls}>
          <TouchableOpacity
            onPress={() => setPlaying(p => !p)}
            style={styles.playBtn}>
            <Text style={styles.playBtnText}>{playing ? '⏸' : '▶'}</Text>
          </TouchableOpacity>

          <Text style={styles.timeText}>
            {formatTime(currentTime)} / {formatTime(duration || 0)}
          </Text>

          <TouchableOpacity
            onPress={() => setMuted(m => !m)}
            style={styles.muteBtn}>
            <Text style={styles.muteText}>{muted ? '🔇' : '🔊'}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Stream Info */}
      <ScrollView style={styles.info}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Stream Info</Text>
          <Text style={styles.infoRow}>URL: {config.streamUrl}</Text>
          <Text style={styles.infoRow}>Quality: {quality}</Text>
          <Text style={styles.infoRow}>Position: {formatTime(currentTime)}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Settings</Text>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Ad Integration</Text>
            <Switch
              value={config.adsEnabled}
              trackColor={{ false: '#475569', true: '#2563eb' }}
              ios_backgroundColor="#475569"
            />
          </View>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Analytics</Text>
            <Switch
              value={config.analyticsEnabled}
              trackColor={{ false: '#475569', true: '#2563eb' }}
              ios_backgroundColor="#475569"
            />
          </View>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Offline Caching</Text>
            <Switch
              value={config.offlineCaching}
              trackColor={{ false: '#475569', true: '#2563eb' }}
              ios_backgroundColor="#475569"
            />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
  },
  headerTitle: {
    color: '#60a5fa',
    fontSize: 18,
    fontWeight: '700',
  },
  playerContainer: {
    backgroundColor: '#000',
    aspectRatio: 16 / 9,
    position: 'relative',
  },
  video: {
    ...StyleSheet.absoluteFillObject,
  },
  controls: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  playBtn: {
    padding: 4,
    marginRight: 10,
  },
  playBtnText: {
    color: '#fff',
    fontSize: 18,
  },
  timeText: {
    flex: 1,
    color: '#cbd5e1',
    fontSize: 12,
    fontFamily: 'monospace',
  },
  muteBtn: {
    padding: 4,
  },
  muteText: {
    fontSize: 16,
  },
  info: {
    flex: 1,
    padding: 12,
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 8,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardTitle: {
    color: '#94a3b8',
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  infoRow: {
    color: '#cbd5e1',
    fontSize: 12,
    fontFamily: 'monospace',
    marginBottom: 4,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  settingLabel: {
    color: '#e2e8f0',
    fontSize: 14,
  },
});
