import { AIRI_LOCAL_PRESENCE_DEFAULTS } from '../airi/live2d/airiLive2DConfig';

export const EMOTIONS = {
  neutral: {
    id: 'neutral',
    label: '平静',
    tone: '#d7e4ef',
    action: { expression: 'neutral', motion: 'idle', style: 'idle', reason: 'emotion_neutral' },
  },
  happy: {
    id: 'happy',
    label: '开心',
    tone: '#7cf3bd',
    action: { expression: 'happy', motion: 'encourage', style: 'interaction', reason: 'emotion_happy' },
  },
  sad: {
    id: 'sad',
    label: '抱歉',
    tone: '#8fb7ff',
    action: { expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'emotion_sad' },
  },
  angry: {
    id: 'angry',
    label: '严肃',
    tone: '#ff9b9b',
    action: { expression: 'serious', motion: 'emphasize', style: 'serious', reason: 'emotion_angry' },
  },
  think: {
    id: 'think',
    label: '思考',
    tone: '#ffd080',
    action: { expression: 'thinking', motion: 'magic', style: 'thinking', reason: 'emotion_think' },
  },
  surprised: {
    id: 'surprised',
    label: '惊讶',
    tone: '#b6a2ff',
    action: { expression: 'surprised', motion: 'magic', style: 'interaction', reason: 'emotion_surprised' },
  },
  awkward: {
    id: 'awkward',
    label: '迟疑',
    tone: '#ffb6d0',
    action: { expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'emotion_awkward' },
  },
  question: {
    id: 'question',
    label: '疑问',
    tone: '#9ee8ff',
    action: { expression: 'thinking', motion: 'nod', style: 'thinking', reason: 'emotion_question' },
  },
  curious: {
    id: 'curious',
    label: '好奇',
    tone: '#c8f27c',
    action: { expression: 'encouraging', motion: 'explain', style: 'normal', reason: 'emotion_curious' },
  },
};

export const EMOTION_VALUES = Object.values(EMOTIONS);

export const MOTION_PRESETS = [
  { id: 'idle', label: '待机' },
  { id: 'explain', label: '说明' },
  { id: 'nod', label: '点头' },
  { id: 'emphasize', label: '强调' },
  { id: 'magic', label: '思考' },
  { id: 'encourage', label: '鼓励' },
  { id: 'celebrate', label: '庆祝' },
];

export const BEAT_STYLES = [
  { id: 'punchy-v', label: '有力' },
  { id: 'balanced-v', label: '自然' },
  { id: 'swing-lr', label: '左右' },
  { id: 'sway-sine', label: '轻摆' },
];

const EXPRESSION_EMOTION = {
  neutral: 'neutral',
  warm: 'happy',
  blink: 'neutral',
  happy: 'happy',
  thinking: 'think',
  serious: 'angry',
  surprised: 'surprised',
  apologetic: 'sad',
  encouraging: 'curious',
};

const STATUS_EMOTION = {
  loading: 'think',
  queued: 'think',
  playing: 'happy',
  interaction: 'curious',
  idle_behavior: 'curious',
  ready: 'neutral',
  idle: 'neutral',
  error: 'awkward',
  unavailable: 'awkward',
};

export const DEFAULT_AVATAR_DEBUG_CONFIG = {
  ...AIRI_LOCAL_PRESENCE_DEFAULTS,
};

function clampNumber(value, min, max, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function normalizeBoolean(value, fallback) {
  if (typeof value === 'boolean') return value;
  if (value === 'true') return true;
  if (value === 'false') return false;
  return fallback;
}

export function normalizeEmotion(value, fallback = 'neutral') {
  const id = String(value || '').trim();
  return EMOTIONS[id] ? id : fallback;
}

export function emotionForAction(action = {}) {
  if (action.emotion) return normalizeEmotion(action.emotion);
  if (action.style === 'thinking') return 'think';
  if (action.style === 'serious') return 'angry';
  if (action.style === 'soft') return 'sad';
  if (action.reason?.includes?.('question')) return 'question';
  return normalizeEmotion(EXPRESSION_EMOTION[action.expression], 'neutral');
}

export function emotionForSpeechStatus(status = {}, fallback = 'neutral') {
  return normalizeEmotion(STATUS_EMOTION[status.state], fallback);
}

export function actionForEmotion(emotionId, patch = {}) {
  const emotion = EMOTIONS[normalizeEmotion(emotionId)] || EMOTIONS.neutral;
  return {
    ...emotion.action,
    ...patch,
    emotion: emotion.id,
    reason: patch.reason || emotion.action.reason,
  };
}

export function normalizeAvatarDebugConfig(value = {}) {
  return {
    focusGain: clampNumber(value.focusGain, 0, 1.8, DEFAULT_AVATAR_DEBUG_CONFIG.focusGain),
    speechMotionGain: clampNumber(value.speechMotionGain, 0, 1.8, DEFAULT_AVATAR_DEBUG_CONFIG.speechMotionGain),
    breathGain: clampNumber(value.breathGain, 0, 1.8, DEFAULT_AVATAR_DEBUG_CONFIG.breathGain),
    cheekGain: clampNumber(value.cheekGain, 0, 1.8, DEFAULT_AVATAR_DEBUG_CONFIG.cheekGain),
    beatStyle: BEAT_STYLES.some((item) => item.id === value.beatStyle)
      ? value.beatStyle
      : DEFAULT_AVATAR_DEBUG_CONFIG.beatStyle,
    autoBeatStyle: normalizeBoolean(value.autoBeatStyle, DEFAULT_AVATAR_DEBUG_CONFIG.autoBeatStyle),
    live2dIdleAnimationEnabled: normalizeBoolean(
      value.live2dIdleAnimationEnabled,
      DEFAULT_AVATAR_DEBUG_CONFIG.live2dIdleAnimationEnabled,
    ),
    live2dAutoBlinkEnabled: normalizeBoolean(
      value.live2dAutoBlinkEnabled,
      DEFAULT_AVATAR_DEBUG_CONFIG.live2dAutoBlinkEnabled,
    ),
    live2dForceAutoBlinkEnabled: normalizeBoolean(
      value.live2dForceAutoBlinkEnabled,
      DEFAULT_AVATAR_DEBUG_CONFIG.live2dForceAutoBlinkEnabled,
    ),
  };
}

export function readAvatarDebugConfig(storage = window.localStorage) {
  try {
    const stored = storage?.getItem?.('airi.avatar.debug');
    if (stored) return normalizeAvatarDebugConfig(JSON.parse(stored));
  } catch {
    // Ignore malformed debug settings.
  }
  return normalizeAvatarDebugConfig();
}

export function writeAvatarDebugConfig(config, storage = window.localStorage) {
  const next = normalizeAvatarDebugConfig(config);
  storage?.setItem?.('airi.avatar.debug', JSON.stringify(next));
  return next;
}
