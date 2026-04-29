import { createPlaybackManager } from '../airi/audio/playbackManager';
import { createSpeechPipeline } from '../airi/audio/speechPipeline';
import { createLive2DLipSync } from '../airi/lipsync/live2dLipSync';
import { ensureEyesOpen, resetMouthForm, setMouthForm } from '../avatar/avatarRuntime';
import { normalizeMouthProfile } from '../avatar/modelProfilePresets';
import { resolveExpression, resolveMotion } from '../avatar/motionMap';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const PLAYBACK_INTENTS = new Set(['queue', 'replace', 'interrupt']);

const MOUTH_SHAPES = {
  rest: { a: 0.06, i: 0.02, u: 0.02, e: 0.02, o: 0.03, up: 0, down: 0, angry: 0, form: 0, form2: 0 },
  open: { a: 1, i: 0.04, u: 0.02, e: 0.12, o: 0.16, up: 0.08, down: 0, angry: 0, form: 0.02, form2: 0.08 },
  wide: { a: 0.26, i: 1, u: 0.02, e: 0.52, o: 0.02, up: 0.3, down: 0, angry: 0, form: 0.64, form2: 0.52 },
  tightRound: { a: 0.22, i: 0.03, u: 1, e: 0.04, o: 0.64, up: 0, down: 0.12, angry: 0.1, form: -0.68, form2: -0.55 },
  spread: { a: 0.42, i: 0.3, u: 0.03, e: 1, o: 0.08, up: 0.2, down: 0, angry: 0, form: 0.5, form2: 0.38 },
  round: { a: 0.32, i: 0.03, u: 0.58, e: 0.05, o: 1, up: 0, down: 0.08, angry: 0.08, form: -0.5, form2: -0.38 },
  teeth: { a: 0.18, i: 0.78, u: 0.02, e: 0.66, o: 0.02, up: 0.28, down: 0, angry: 0, form: 0.58, form2: 0.44 },
  closed: { a: 0.04, i: 0.02, u: 0.02, e: 0.02, o: 0.03, up: 0, down: 0, angry: 0, form: 0, form2: 0 },
};

MOUTH_SHAPES.a = MOUTH_SHAPES.open;
MOUTH_SHAPES.i = MOUTH_SHAPES.wide;
MOUTH_SHAPES.u = MOUTH_SHAPES.tightRound;
MOUTH_SHAPES.e = MOUTH_SHAPES.spread;
MOUTH_SHAPES.o = MOUTH_SHAPES.round;
MOUTH_SHAPES.m = MOUTH_SHAPES.closed;

const VISEME_ALIASES = {
  a: 'open',
  i: 'wide',
  u: 'tightRound',
  e: 'spread',
  o: 'round',
  m: 'closed',
  silence: 'rest',
  pause: 'rest',
  bilabial: 'closed',
  labiodental: 'teeth',
};

const VISEME_BY_LATIN = [
  { name: 'open', pattern: /a/i },
  { name: 'wide', pattern: /[iy]/i },
  { name: 'tightRound', pattern: /[uv]/i },
  { name: 'spread', pattern: /e/i },
  { name: 'round', pattern: /o/i },
];

let sharedAudioContext = null;
let activeTurnId = null;
let pendingTtsCount = 0;
let currentModel = null;
let currentApp = null;
let activeAudio = null;
let activeAudioUrl = '';
let activeMouthSyncStop = null;
let speechPipeline = null;
const playbackRuntimes = new Map();

function emitSpeechStatus(detail) {
  window.dispatchEvent(new CustomEvent('speech_status', { detail }));
}

function currentTtsConfig() {
  return window.__AIRI_TTS_CONFIG || {};
}

function currentAvatarConfig() {
  return window.__AIRI_AVATAR_CONFIG || {};
}

function currentBehaviorProfile() {
  return currentAvatarConfig().modelProfile?.behavior || {};
}

function currentSpeechProfile() {
  return currentBehaviorProfile().speech || {};
}

function currentMouthProfile() {
  return normalizeMouthProfile(currentAvatarConfig().modelProfile?.mouth);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function normalizeTurnId(turnId) {
  return String(turnId ?? 'default');
}

function createId(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function queueSize() {
  const size = playbackManager.size();
  const pipelineSize = speechPipeline?.size?.() || {};
  return size.waiting
    + pendingTtsCount
    + (size.active ? 1 : 0)
    + (pipelineSize.pendingIntents || 0);
}

function speechSegmentOptions() {
  const segment = currentSpeechProfile().segment || {};
  return {
    boost: Number(segment.boost ?? 2),
    minimumWords: Number(segment.minimumWords ?? 4),
    maximumWords: Number(segment.maximumWords ?? 18),
    maximumChars: Number(segment.maximumChars ?? 220),
    singleChunkChars: Number(segment.singleChunkChars ?? 120),
    singleChunkWords: Number(segment.singleChunkWords ?? 28),
  };
}

function speechPlaybackAction(action = {}) {
  const speechAction = currentSpeechProfile().action || {};
  return {
    ...speechAction,
    ...action,
    style: action.style || speechAction.style || 'speaking',
    reason: action.reason || speechAction.reason || 'speech_playing',
  };
}

function normalizeViseme(viseme) {
  const raw = String(viseme || '').trim();
  if (!raw) return '';
  return VISEME_ALIASES[raw] || (MOUTH_SHAPES[raw] ? raw : '');
}

function visemeForText(text) {
  const value = String(text || '').trim();
  if (!value) return 'rest';
  if (/^[\s,.!?;:，。！？；：、]+$/.test(value)) return 'rest';
  for (const rule of VISEME_BY_LATIN) {
    if (rule.pattern.test(value)) return rule.name;
  }
  return 'open';
}

function mouthShapeForSegment(segment) {
  const viseme = normalizeViseme(visemeForText(segment)) || 'open';
  const opennessByViseme = {
    rest: 0.1,
    closed: 0.12,
    teeth: 0.38,
    wide: 0.58,
    tightRound: 0.58,
    spread: 0.7,
    round: 0.72,
    open: 0.9,
  };
  return {
    viseme,
    shape: MOUTH_SHAPES[viseme] || MOUTH_SHAPES.open,
    pause: viseme === 'rest',
    openness: opennessByViseme[viseme] ?? 0.7,
  };
}

function mouthShapeForCue(cue, time) {
  const cueDuration = Math.max(0.035, Number(cue?.end || 0) - Number(cue?.start || 0));
  const progress = cue ? clamp((time - cue.start) / cueDuration, 0, 1) : 1;
  const consonant = normalizeViseme(cue?.consonant);
  if (consonant && progress < Math.min(0.28, 0.055 / cueDuration)) {
    return {
      viseme: consonant,
      shape: MOUTH_SHAPES[consonant] || MOUTH_SHAPES.closed,
      pause: false,
      openness: consonant === 'closed' ? 0.1 : 0.32,
      consonant: true,
    };
  }

  const viseme = normalizeViseme(cue?.viseme);
  if (!viseme) return mouthShapeForSegment(cue?.text || '');
  const fallback = mouthShapeForSegment('');
  const opennessByViseme = {
    rest: 0.1,
    closed: 0.12,
    teeth: 0.38,
    wide: 0.58,
    tightRound: 0.58,
    spread: 0.7,
    round: 0.72,
    open: 0.9,
  };
  return {
    viseme,
    shape: MOUTH_SHAPES[viseme] || MOUTH_SHAPES.open,
    pause: viseme === 'rest',
    openness: opennessByViseme[viseme] ?? fallback.openness,
  };
}

function blendMouthShapes(baseShape, overlayShape, amount) {
  const blended = {};
  for (const key of Object.keys(MOUTH_SHAPES.rest)) {
    const baseValue = baseShape?.[key] ?? 0;
    const overlayValue = overlayShape?.[key] ?? 0;
    blended[key] = baseValue + (overlayValue - baseValue) * amount;
  }
  return blended;
}

function mouthShapeFromLipSyncWeights(weights, mouthProfile = currentMouthProfile()) {
  if (!weights) return null;
  const vowelShapes = [
    ['A', MOUTH_SHAPES.open],
    ['E', MOUTH_SHAPES.spread],
    ['I', MOUTH_SHAPES.wide],
    ['O', MOUTH_SHAPES.round],
    ['U', MOUTH_SHAPES.tightRound],
  ];
  const maxWeight = Math.max(0, ...vowelShapes.map(([key]) => weights[key] || 0));
  const totalWeight = vowelShapes.reduce((sum, [key]) => sum + (weights[key] || 0), 0);
  if (maxWeight < 0.025 || totalWeight <= 0) return null;

  const shape = {};
  for (const key of Object.keys(MOUTH_SHAPES.rest)) {
    shape[key] = vowelShapes.reduce((sum, [vowel, vowelShape]) => (
      sum + (vowelShape[key] || 0) * ((weights[vowel] || 0) / totalWeight)
    ), 0);
  }

  return {
    shape,
    openness: clamp(maxWeight, 0, mouthProfile.lipSync.shapeOpenCap),
  };
}

function mouthShapeForText(text, audio) {
  const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : 1;
  const progress = clamp(audio.currentTime / duration, 0, 1);
  const index = Math.floor(progress * Math.max(1, text.length - 1));
  return mouthShapeForSegment(text.slice(Math.max(0, index - 1), index + 2));
}

function findActiveCue(cues, time) {
  if (!cues?.length) return null;
  return cues.find((cue) => time >= cue.start && time < cue.end) || null;
}

function cueArticulation(cue, time) {
  if (!cue) return 1;
  const progress = clamp((time - cue.start) / (cue.end - cue.start), 0, 1);
  const attack = clamp(progress / 0.28, 0, 1);
  const release = clamp((1 - progress) / 0.22, 0, 1);
  return Math.sin(progress * Math.PI) * Math.max(0.2, Math.min(attack, release));
}

function getAudioContext() {
  const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextCtor) return null;
  if (!sharedAudioContext) {
    sharedAudioContext = new AudioContextCtor();
  }
  return sharedAudioContext;
}

async function setupAnalyser(audio, mouthProfile = currentMouthProfile()) {
  try {
    const context = getAudioContext();
    if (!context) return null;
    if (context.state === 'suspended') await context.resume();

    const analyser = context.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.48;

    const source = context.createMediaElementSource(audio);
    let lipSync = null;
    try {
      lipSync = await createLive2DLipSync(context, {
        cap: mouthProfile.lipSync.cap,
        volumeScale: mouthProfile.lipSync.volumeScale,
        volumeExponent: mouthProfile.lipSync.volumeExponent,
        mouthUpdateIntervalMs: mouthProfile.lipSync.mouthUpdateIntervalMs,
        mouthLerpWindowMs: mouthProfile.lipSync.mouthLerpWindowMs,
      });
      lipSync.connectSource(source);
    } catch (error) {
      console.warn('[audio] wLipSync unavailable, using energy mouth sync:', error);
    }

    source.connect(analyser);
    analyser.connect(context.destination);
    return {
      analyser,
      data: new Uint8Array(analyser.fftSize),
      lipSync,
    };
  } catch (error) {
    console.warn('[audio] analyser unavailable, falling back to timed mouth sync:', error);
    return null;
  }
}

function audioEnergy(analyserState) {
  if (!analyserState) return null;
  const { analyser, data } = analyserState;
  analyser.getByteTimeDomainData(data);
  let sum = 0;
  for (const value of data) {
    const centered = (value - 128) / 128;
    sum += centered * centered;
  }
  return Math.sqrt(sum / data.length);
}

function startMouthSync(model, audio, text, mouthCues = [], app) {
  const mouthProfile = currentMouthProfile();
  let stopped = false;
  let animationId = 0;
  let mouthValue = 0;
  let targetMouthValue = 0;
  let lastTargetUpdateMs = 0;
  let lastMouthSmoothMs = 0;
  let lastPresenceEmitMs = 0;
  let currentShape = { ...MOUTH_SHAPES.rest };
  let analyserState = null;

  void setupAnalyser(audio, mouthProfile).then((state) => {
    analyserState = state;
  });

  const applyFrame = () => {
    if (stopped) return;
    const timestamp = performance.now();
    const energy = audioEnergy(analyserState);
    const lipSyncWeights = analyserState?.lipSync?.getVowelWeights?.();
    const lipSyncMouth = analyserState?.lipSync?.getMouthOpen?.();
    const lipSyncShape = mouthShapeFromLipSyncWeights(lipSyncWeights, mouthProfile);
    const cueTime = audio.currentTime + mouthProfile.leadSeconds;
    const activeCue = findActiveCue(mouthCues, cueTime);
    const cueShape = activeCue ? mouthShapeForCue(activeCue, cueTime) : mouthShapeForText(text, audio);
    const shape = lipSyncShape ? blendMouthShapes(cueShape.shape, lipSyncShape.shape, mouthProfile.lipSyncBlend) : cueShape.shape;
    const articulation = cueArticulation(activeCue, cueTime);
    const timedPulse = 0.34 + Math.sin(performance.now() / 58) * 0.18;
    const energyTarget = energy === null
      ? timedPulse
      : clamp((energy - mouthProfile.energyNoiseFloor) * mouthProfile.energyScale, 0, 1);

    if (lastTargetUpdateMs === 0 || timestamp - lastTargetUpdateMs >= mouthProfile.smoothing.targetIntervalMs) {
      const speechFloor = activeCue && !cueShape.pause && !cueShape.consonant ? mouthProfile.speechFloor : 0;
      const audioDrivenTarget = Number.isFinite(lipSyncMouth)
        ? Math.max(lipSyncMouth, energyTarget * mouthProfile.energyToLipSync)
        : energyTarget;
      const cueTarget = activeCue
        ? Math.max(audioDrivenTarget * mouthProfile.cueAudioBlend, articulation * cueShape.openness, speechFloor)
        : audioDrivenTarget;
      const consonantTarget = cueShape.consonant
        ? Math.max(energyTarget * mouthProfile.consonantEnergyBlend, cueShape.openness)
        : cueTarget;
      targetMouthValue = clamp(
        cueShape.pause ? Math.max(audioDrivenTarget * mouthProfile.pauseAudioBlend, 0.02) : consonantTarget,
        mouthProfile.openMin,
        mouthProfile.openMax,
      );
      lastTargetUpdateMs = timestamp;
    }

    if (lastMouthSmoothMs === 0) lastMouthSmoothMs = timestamp;
    const smoothing = clamp((timestamp - lastMouthSmoothMs) / mouthProfile.smoothing.lerpWindowMs, 0.08, mouthProfile.smoothing.open);
    mouthValue += (targetMouthValue - mouthValue) * smoothing;
    lastMouthSmoothMs = timestamp;

    const avatarConfig = currentAvatarConfig();
    const mouthGain = clamp(Number(avatarConfig.mouthGain ?? 1), 0.55, 1.8);
    const shapeSmoothing = cueShape.pause ? mouthProfile.smoothing.pauseShape : mouthProfile.smoothing.activeShape;
    for (const key of Object.keys(MOUTH_SHAPES.rest)) {
      currentShape[key] += ((shape[key] ?? 0) - currentShape[key]) * shapeSmoothing;
    }

    const finalMouthValue = clamp(mouthValue * mouthGain, mouthProfile.openMin, mouthProfile.openMax);
    setMouthForm(model, finalMouthValue, currentShape, mouthProfile);
    window.dispatchEvent(new CustomEvent('avatar_mouth_sync', {
      detail: {
        value: finalMouthValue,
        shape: { ...currentShape },
      },
    }));
    if (timestamp - lastPresenceEmitMs >= 40) {
      window.dispatchEvent(new CustomEvent('avatar_speech_energy', {
        detail: {
          value: finalMouthValue,
          energy: energyTarget,
          lipSync: Number.isFinite(lipSyncMouth) ? lipSyncMouth : null,
        },
      }));
      lastPresenceEmitMs = timestamp;
    }
  };

  const ticker = app?.ticker;
  const updateFromTicker = () => applyFrame();
  const updateFromAnimationFrame = () => {
    applyFrame();
    animationId = window.requestAnimationFrame(updateFromAnimationFrame);
  };

  if (ticker?.add && ticker?.remove) {
    const priority = window.PIXI?.UPDATE_PRIORITY?.LOW ?? -25;
    ticker.add(updateFromTicker, null, priority);
  } else {
    updateFromAnimationFrame();
  }

  return () => {
    stopped = true;
    if (ticker?.remove) ticker.remove(updateFromTicker);
    else window.cancelAnimationFrame(animationId);
    resetMouthForm(model);
    window.dispatchEvent(new CustomEvent('avatar_mouth_sync', {
      detail: { value: 0, shape: MOUTH_SHAPES.rest },
    }));
    window.dispatchEvent(new CustomEvent('avatar_speech_energy', { detail: { value: 0, energy: 0, lipSync: 0 } }));
  };
}

function decodeMouthCueHeader(response) {
  const encoded = response.headers.get('x-airi-mouth-cues');
  if (!encoded) return null;

  try {
    const binary = window.atob(encoded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const payload = JSON.parse(new TextDecoder('utf-8').decode(bytes));
    return {
      engine: payload.engine || response.headers.get('x-airi-tts-engine') || '',
      cues: Array.isArray(payload.cues)
        ? payload.cues
            .map((cue) => ({
              start: Number(cue.s),
              end: Number(cue.e),
              text: String(cue.t || ''),
              viseme: normalizeViseme(cue.v),
              consonant: normalizeViseme(cue.c),
            }))
            .filter((cue) => Number.isFinite(cue.start) && Number.isFinite(cue.end) && cue.end > cue.start)
        : [],
    };
  } catch (error) {
    console.warn('[audio] mouth cue header parse failed:', error);
    return null;
  }
}

function createAudioElement(audioUrl) {
  const audio = new Audio(audioUrl);
  audio.preload = 'auto';
  audio.load();
  return audio;
}

function cleanupAudioItem(item) {
  if (!item) return;
  try {
    item.audio?.pause();
    if (item.audio) {
      item.audio.onplay = null;
      item.audio.onended = null;
      item.audio.onerror = null;
      item.audio.removeAttribute('src');
      item.audio.load();
    }
  } catch {
    // Best-effort cleanup; browsers may reject cleanup after an abort.
  }
  if (item.audioUrl) URL.revokeObjectURL(item.audioUrl);
}

async function fetchTtsSegment(segment, signal) {
  const ttsConfig = currentTtsConfig();
  const response = await fetch(`${API_BASE_URL}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({ text: segment.text, voice: ttsConfig.voice, rate: ttsConfig.rate }),
  });

  if (!response.ok) throw new Error(`TTS request failed: HTTP ${response.status}`);
  const mouth = decodeMouthCueHeader(response);
  const blob = await response.blob();
  const audioUrl = URL.createObjectURL(blob);
  return {
    audio: createAudioElement(audioUrl),
    audioUrl,
    mouthCues: mouth?.cues || [],
    ttsEngine: mouth?.engine || '',
  };
}

async function synthesizeTtsRequest(request, signal) {
  pendingTtsCount += 1;
  emitSpeechStatus({
    state: 'loading',
    text: request.text,
    queueSize: queueSize(),
    message: '语音生成中',
  });

  try {
    return await fetchTtsSegment({ text: request.text }, signal);
  } catch (error) {
    if (!signal.aborted) {
      console.error('[audio] TTS generation failed:', error);
      emitSpeechStatus({ state: 'error', message: '语音生成失败' });
    }
    throw error;
  } finally {
    pendingTtsCount = Math.max(0, pendingTtsCount - 1);
  }
}

function cleanupRuntimeIfDone(intentId) {
  const runtime = playbackRuntimes.get(intentId);
  if (!runtime) return;
  if (runtime.closed && runtime.playbackCount <= 0) {
    playbackRuntimes.delete(intentId);
  }
}

async function playAudioItem(item, signal) {
  const runtime = playbackRuntimes.get(item.intentId) || {};
  const model = item.model || runtime.model || currentModel;
  const app = item.app || runtime.app || currentApp;
  const action = item.action || runtime.action || {};
  const { audio, audioUrl } = item.audio;
  currentModel = model;
  currentApp = app;
  activeAudio = audio;
  activeAudioUrl = audioUrl;

  return new Promise((resolve, reject) => {
    let settled = false;
    const settle = (handler, value) => {
      if (settled) return;
      settled = true;
      activeMouthSyncStop?.();
      activeMouthSyncStop = null;
      resetMouthForm(model);
      cleanupAudioItem(item.audio);
      if (activeAudio === audio) {
        activeAudio = null;
        activeAudioUrl = '';
      }
      handler(value);
    };

    const abort = () => {
      settle(reject, new Error(signal.reason || 'playback-aborted'));
    };

    signal.addEventListener('abort', abort, { once: true });

    audio.onplay = () => {
      const segmentSuffix = item.segmentCount > 1 ? ` ${item.segmentIndex + 1}/${item.segmentCount}` : '';
      emitSpeechStatus({
        state: 'playing',
        queueSize: queueSize(),
        message: `语音播放中${segmentSuffix}`,
      });
      applyAvatarAction(model, speechPlaybackAction(action), {
        skipMotion: currentSpeechProfile().keepMotionSilent !== false,
      });
      activeMouthSyncStop = startMouthSync(model, audio, item.text, item.audio.mouthCues, app);
    };

    audio.onended = () => {
      signal.removeEventListener('abort', abort);
      settle(resolve);
    };

    audio.onerror = () => {
      signal.removeEventListener('abort', abort);
      settle(reject, new Error('audio-playback-error'));
    };

    audio.play().catch((error) => {
      signal.removeEventListener('abort', abort);
      settle(reject, error);
    });
  });
}

const playbackManager = createPlaybackManager({
  maxVoices: 1,
  overflowPolicy: 'queue',
  ownerOverflowPolicy: 'steal-oldest',
  play: playAudioItem,
});

speechPipeline = createSpeechPipeline({
  tts: synthesizeTtsRequest,
  playback: playbackManager,
  logger: console,
});

speechPipeline.on('onTtsResult', (result) => {
  const runtime = playbackRuntimes.get(result.intentId);
  if (runtime) {
    runtime.playbackCount = (runtime.playbackCount || 0) + 1;
  }
  emitSpeechStatus({ state: 'queued', queueSize: queueSize() });
});

speechPipeline.on('onIntentEnd', (intentId) => {
  const runtime = playbackRuntimes.get(intentId);
  if (runtime) {
    runtime.closed = true;
  }
  cleanupRuntimeIfDone(intentId);
  if (queueSize() === 0) {
    emitSpeechStatus({ state: 'idle', queueSize: 0 });
  }
});

speechPipeline.on('onIntentCancel', ({ intentId }) => {
  const runtime = playbackRuntimes.get(intentId);
  if (runtime) {
    runtime.closed = true;
  }
  cleanupRuntimeIfDone(intentId);
  if (queueSize() === 0) {
    emitSpeechStatus({ state: 'idle', queueSize: 0 });
  }
});

playbackManager.onEnd((event) => {
  const runtime = playbackRuntimes.get(event.item?.intentId);
  if (runtime) {
    runtime.playbackCount = Math.max(0, (runtime.playbackCount || 0) - 1);
    cleanupRuntimeIfDone(event.item.intentId);
  }
  if (queueSize() === 0) {
    emitSpeechStatus({ state: 'idle', queueSize: 0 });
  }
});

playbackManager.onInterrupt((event) => {
  const runtime = playbackRuntimes.get(event.item?.intentId);
  if (runtime) {
    runtime.playbackCount = Math.max(0, (runtime.playbackCount || 0) - 1);
    cleanupRuntimeIfDone(event.item.intentId);
  }
  if (queueSize() === 0) {
    emitSpeechStatus({ state: 'idle', queueSize: 0 });
  }
});

playbackManager.onReject((event) => {
  const runtime = playbackRuntimes.get(event.item?.intentId);
  if (runtime) {
    runtime.playbackCount = Math.max(0, (runtime.playbackCount || 0) - 1);
    cleanupRuntimeIfDone(event.item.intentId);
  }
  console.warn('[audio] playback rejected:', event.reason);
});

export function applyAvatarAction(model, action = {}, options = {}) {
  if (!model) return;

  const expressionNames = resolveExpression(action.expression);
  const motionSpecs = resolveMotion(action.motion);

  for (const expressionName of expressionNames) {
    try {
      if (typeof model.expression !== 'function') break;
      model.expression(expressionName);
      if (action.expression === 'neutral' || action.expression === 'warm' || action.style === 'idle') {
        window.setTimeout(() => ensureEyesOpen(model), 80);
      }
      break;
    } catch (error) {
      console.warn('[avatar] expression failed:', expressionName, error);
    }
  }

  if (options.skipMotion) return;

  for (const motionSpec of motionSpecs) {
    try {
      if (typeof model.motion !== 'function' || !motionSpec) break;
      const forcePriority = window.__AIRI_MOTION_PRIORITY_FORCE;
      if (forcePriority !== undefined) model.motion(motionSpec[0], motionSpec[1], forcePriority);
      else model.motion(motionSpec[0], motionSpec[1]);
      break;
    } catch (error) {
      console.warn('[avatar] motion failed:', motionSpec, error);
    }
  }
}

export function playTextToSpeech(payload, model, app) {
  const text = typeof payload === 'string' ? payload : payload?.text;
  const action = typeof payload === 'string' ? {} : payload?.action;
  const intent = typeof payload === 'string'
    ? 'queue'
    : PLAYBACK_INTENTS.has(payload?.intent)
      ? payload.intent
      : 'queue';
  const turnId = normalizeTurnId(typeof payload === 'string' ? 'default' : payload?.turnId);
  const ownerId = turnId;

  currentModel = model || currentModel;
  currentApp = app || currentApp;

  if (intent === 'interrupt') {
    stopTextToSpeech(model, payload?.message || '语音已中断');
    return;
  }

  const behavior = intent === 'replace' || (activeTurnId !== null && activeTurnId !== turnId)
    ? 'replace'
    : intent;

  activeTurnId = turnId;

  if (!model) {
    emitSpeechStatus({ state: 'unavailable', message: '数字人模型尚未加载，暂不播放语音' });
    return;
  }

  const intentId = createId(`intent-${turnId}`);
  const streamId = createId(`stream-${turnId}`);
  playbackRuntimes.set(intentId, {
    model,
    app,
    action,
    turnId,
    closed: false,
    playbackCount: 0,
  });

  emitSpeechStatus({
    state: 'queued',
    queueSize: queueSize() + 1,
    message: '语音已进入队列',
  });

  const handle = speechPipeline.openIntent({
    intentId,
    streamId,
    ownerId,
    behavior,
    priority: behavior === 'replace' ? 'high' : 'normal',
    segmentOptions: speechSegmentOptions(),
  });
  handle.writeLiteral(text);
  handle.end();
}

export function stopTextToSpeech(model = currentModel, message = '语音已重置') {
  pendingTtsCount = 0;
  speechPipeline?.stopAll(message);
  playbackRuntimes.clear();
  activeMouthSyncStop?.();
  activeMouthSyncStop = null;

  if (activeAudio) {
    try {
      activeAudio.pause();
      activeAudio.removeAttribute('src');
      activeAudio.load();
    } catch {
      // Best-effort cleanup.
    }
  }
  if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);

  activeAudio = null;
  activeAudioUrl = '';
  activeTurnId = null;
  resetMouthForm(model);
  emitSpeechStatus({ state: 'idle', queueSize: 0, message });
}
