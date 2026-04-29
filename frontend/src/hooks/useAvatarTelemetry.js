import { useEffect, useState } from 'react';
import {
  EMOTIONS,
  emotionForAction,
  emotionForSpeechStatus,
} from '../avatar/emotionSystem';

const EMPTY_ENERGY = {
  value: 0,
  energy: 0,
  lipSync: 0,
};

export function useAvatarTelemetry() {
  const [telemetry, setTelemetry] = useState({
    emotion: 'neutral',
    action: null,
    speechStatus: { state: 'idle', queueSize: 0 },
    energy: EMPTY_ENERGY,
    capabilities: window.__AIRI_AVATAR_CAPABILITIES || null,
    specialToken: null,
    updatedAt: 0,
  });

  useEffect(() => {
    let frame = 0;
    let latestEnergy = EMPTY_ENERGY;

    const flushEnergy = () => {
      frame = 0;
      setTelemetry((current) => ({
        ...current,
        energy: latestEnergy,
        updatedAt: Date.now(),
      }));
    };

    const handleAction = (event) => {
      const action = event.detail || {};
      setTelemetry((current) => ({
        ...current,
        emotion: emotionForAction(action),
        action,
        updatedAt: Date.now(),
      }));
    };

    const handleSpeechStatus = (event) => {
      const speechStatus = event.detail || { state: 'idle', queueSize: 0 };
      setTelemetry((current) => ({
        ...current,
        speechStatus,
        emotion: emotionForSpeechStatus(speechStatus, current.emotion),
        updatedAt: Date.now(),
      }));
    };

    const handleEnergy = (event) => {
      const detail = event.detail || {};
      latestEnergy = {
        value: Math.max(0, Math.min(1, Number(detail.value || 0))),
        energy: Math.max(0, Math.min(1, Number(detail.energy || 0))),
        lipSync: detail.lipSync == null ? null : Math.max(0, Math.min(1, Number(detail.lipSync || 0))),
      };
      if (!frame) frame = window.requestAnimationFrame(flushEnergy);
    };

    const handleCapabilities = (event) => {
      setTelemetry((current) => ({
        ...current,
        capabilities: event.detail || null,
        updatedAt: Date.now(),
      }));
    };

    const handleSpecialToken = (event) => {
      setTelemetry((current) => ({
        ...current,
        specialToken: event.detail || null,
        updatedAt: Date.now(),
      }));
    };

    window.addEventListener('avatar_action', handleAction);
    window.addEventListener('speech_status', handleSpeechStatus);
    window.addEventListener('avatar_speech_energy', handleEnergy);
    window.addEventListener('avatar_model_capabilities', handleCapabilities);
    window.addEventListener('avatar_special_token', handleSpecialToken);

    return () => {
      window.removeEventListener('avatar_action', handleAction);
      window.removeEventListener('speech_status', handleSpeechStatus);
      window.removeEventListener('avatar_speech_energy', handleEnergy);
      window.removeEventListener('avatar_model_capabilities', handleCapabilities);
      window.removeEventListener('avatar_special_token', handleSpecialToken);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  return {
    ...telemetry,
    emotionInfo: EMOTIONS[telemetry.emotion] || EMOTIONS.neutral,
  };
}
