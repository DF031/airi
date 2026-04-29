import { behaviorProfileForModel } from './modelBehaviorProfiles';
import {
  MODEL_PROFILE_PRESETS,
  normalizeMotionStrategy,
  normalizeMouthProfile,
  normalizeStageProfile,
} from './modelProfilePresets';

export const DEFAULT_MODEL_URL = import.meta.env.VITE_LIVE2D_MODEL_URL || '/live2d/hiyori/Hiyori.model3.json';

export const DEFAULT_AVATAR_FIT = {
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  mouthGain: 1,
};

const BASE_KNOWN_MODEL_PROFILES = {
  '/Epsilon/runtime/Epsilon.model3.json': {
    id: 'epsilon',
    name: 'Epsilon',
    fit: { scale: 0.98, offsetX: 0, offsetY: 0, mouthGain: 1.12 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['Tap', 0], ['Flick', 0], ['FlickUp', 0]],
      nod: [['FlickDown', 0], ['Tap', 1]],
      emphasize: [['FlickUp', 1], ['Flick3', 0]],
      magic: [['Shake', 1], ['Flick3', 1]],
      encourage: [['Tap', 2], ['Flick', 1]],
      celebrate: [['Shake', 0], ['Tap', 3]],
    },
  },
  '/izumi/runtime/izumi_illust.model3.json': {
    id: 'izumi',
    name: 'Izumi',
    fit: { scale: 1.02, offsetX: 0, offsetY: -16, mouthGain: 1.1 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['Tap', 0], ['FlickRight', 0]],
      nod: [['FlickLeft', 0], ['Tap', 1]],
      emphasize: [['FlickRight', 1], ['Tap', 2]],
      magic: [['Shake', 0]],
      encourage: [['Tap', 1], ['Idle', 1]],
      celebrate: [['FlickRight', 1], ['Shake', 0]],
    },
  },
  '/live2d/hiyori/Hiyori.model3.json': {
    id: 'hiyori',
    name: 'Hiyori',
    fit: { scale: 0.94, offsetX: 0, offsetY: 34, mouthGain: 1.08 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['TapBody', 0], ['Idle', 1]],
      nod: [['TapBody', 0], ['Idle', 2]],
      emphasize: [['TapBody', 0], ['Idle', 3]],
      magic: [['TapBody', 0], ['Idle', 4]],
      encourage: [['TapBody', 0], ['Idle', 5]],
      celebrate: [['TapBody', 0], ['Idle', 6]],
    },
  },
  '/live2d/natori/Natori.model3.json': {
    id: 'natori',
    name: 'Natori',
    fit: { scale: 0.94, offsetX: 0, offsetY: 10, mouthGain: 1.1 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['TapBody', 0], ['TapBody', 1], ['Idle', 1]],
      nod: [['TapBody', 1], ['Idle', 0]],
      emphasize: [['TapBody', 2], ['TapBody', 3]],
      magic: [['TapBody', 4], ['Idle', 2]],
      encourage: [['TapBody', 3], ['Idle', 1]],
      celebrate: [['TapBody', 4], ['Idle', 2]],
    },
  },
  '/mao_pro_zh/runtime/mao_pro.model3.json': {
    id: 'mao-pro',
    name: 'Mao Pro',
    fit: { scale: 0.98, offsetX: 0, offsetY: 0, mouthGain: 1.24 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['', 0], ['', 1], ['Idle', 0]],
      nod: [['', 1], ['', 0]],
      emphasize: [['', 2], ['', 3]],
      magic: [['', 4], ['special', 0]],
      encourage: [['', 3], ['', 4]],
      celebrate: [['', 5], ['special', 1]],
    },
  },
  '/shizuku/runtime/shizuku.model3.json': {
    id: 'shizuku',
    name: 'Shizuku',
    fit: { scale: 1.02, offsetX: 0, offsetY: -4, mouthGain: 1.12 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['Tap', 0], ['FlickUp', 0]],
      nod: [['FlickUp', 0], ['Tap', 0]],
      emphasize: [['Flick3', 0], ['Tap', 0]],
      magic: [['Flick3', 0]],
      encourage: [['Tap', 0], ['Idle', 0]],
      celebrate: [['Flick3', 0]],
    },
  },
  '/tororo_hijiki/hijiki/runtime/hijiki.model3.json': {
    id: 'hijiki',
    name: 'Hijiki',
    fit: { scale: 1.12, offsetX: 0, offsetY: -8, mouthGain: 1.18 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['Tap', 0], ['FlickUp', 0]],
      nod: [['FlickDown', 0], ['Tap', 1]],
      emphasize: [['Tap', 2], ['Flick', 0]],
      magic: [['FlickUp', 0], ['Tap', 2]],
      encourage: [['Tap', 1], ['Idle', 1]],
      celebrate: [['Flick', 0], ['Idle', 2]],
    },
  },
  '/tororo_hijiki/tororo/runtime/tororo.model3.json': {
    id: 'tororo',
    name: 'Tororo',
    fit: { scale: 1.12, offsetX: 0, offsetY: -8, mouthGain: 1.18 },
    motionAliases: {
      idle: [['Idle', 0]],
      explain: [['Tap', 0], ['FlickUp', 0]],
      nod: [['FlickDown', 0], ['Tap', 1]],
      emphasize: [['Tap', 2], ['Flick', 0]],
      magic: [['FlickUp', 0], ['Tap', 2]],
      encourage: [['Tap', 1], ['Idle', 1]],
      celebrate: [['Flick', 0], ['Idle', 2]],
    },
  },
};

function mergeProfilePreset(base = {}, preset = {}) {
  return {
    ...base,
    ...preset,
    fit: { ...(base.fit || {}), ...(preset.fit || {}) },
    stage: { ...(base.stage || {}), ...(preset.stage || {}) },
    mouth: { ...(base.mouth || {}), ...(preset.mouth || {}) },
    motionStrategy: { ...(base.motionStrategy || {}), ...(preset.motionStrategy || {}) },
    expressionAliases: { ...(base.expressionAliases || {}), ...(preset.expressionAliases || {}) },
    motionAliases: { ...(base.motionAliases || {}), ...(preset.motionAliases || {}) },
    behavior: { ...(base.behavior || {}), ...(preset.behavior || {}) },
  };
}

export const KNOWN_MODEL_PROFILES = Object.fromEntries(
  Array.from(new Set([
    ...Object.keys(BASE_KNOWN_MODEL_PROFILES),
    ...Object.keys(MODEL_PROFILE_PRESETS),
  ])).map((url) => [
    url,
    mergeProfilePreset(BASE_KNOWN_MODEL_PROFILES[url], MODEL_PROFILE_PRESETS[url]),
  ]),
);

export const FALLBACK_MODELS = [
  {
    id: 'hiyori',
    name: 'Hiyori',
    url: DEFAULT_MODEL_URL,
    lip_sync_params: ['ParamMouthOpenY', 'ParamMouthForm'],
    motion_groups: { Idle: 9, TapBody: 1 },
  },
];

export function fitStorageKey(modelUrl) {
  return `airi.avatar.fit.${modelUrl || DEFAULT_MODEL_URL}`;
}

export function clampNumber(value, min, max, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

export function normalizeAvatarFit(value = {}) {
  return {
    scale: clampNumber(value.scale, 0.65, 1.55, DEFAULT_AVATAR_FIT.scale),
    offsetX: clampNumber(value.offsetX, -260, 260, DEFAULT_AVATAR_FIT.offsetX),
    offsetY: clampNumber(value.offsetY, -260, 260, DEFAULT_AVATAR_FIT.offsetY),
    mouthGain: clampNumber(value.mouthGain, 0.55, 1.8, DEFAULT_AVATAR_FIT.mouthGain),
  };
}

export function defaultFitForModel(modelUrl) {
  const known = KNOWN_MODEL_PROFILES[modelUrl] || {};
  return normalizeAvatarFit({
    ...DEFAULT_AVATAR_FIT,
    mouthGain: known.mouth?.gain ?? DEFAULT_AVATAR_FIT.mouthGain,
    ...(known.fit || {}),
  });
}

function uniqueIds(...groups) {
  return Array.from(new Set(groups.flat().filter(Boolean).map(String)));
}

function lipSyncParamsFromMouth(mouth = {}) {
  const params = mouth.params || {};
  const vowels = params.vowels || {};
  const extras = params.extras || {};
  return uniqueIds(
    params.open || [],
    params.form || [],
    params.form2 || [],
    vowels.a || [],
    vowels.i || [],
    vowels.u || [],
    vowels.e || [],
    vowels.o || [],
    extras.up || [],
    extras.down || [],
    extras.angry || [],
  );
}

export function readAvatarFit(modelUrl) {
  try {
    const stored = window.localStorage.getItem(fitStorageKey(modelUrl));
    if (stored) {
      return normalizeAvatarFit({ ...defaultFitForModel(modelUrl), ...JSON.parse(stored) });
    }
  } catch {
    // Ignore malformed local calibration data.
  }
  return defaultFitForModel(modelUrl);
}

export function profileForModel(model = {}) {
  const known = KNOWN_MODEL_PROFILES[model.url] || {};
  const mergedModel = { ...model, ...known, behavior: { ...(known.behavior || {}), ...(model.behavior || {}) } };
  const lipSyncParams = model.lip_sync_params || known.lip_sync_params || lipSyncParamsFromMouth(known.mouth);
  return {
    ...model,
    ...known,
    id: model.id || known.id || model.url || DEFAULT_MODEL_URL,
    name: known.name || model.name || 'Live2D',
    url: model.url || DEFAULT_MODEL_URL,
    fit: normalizeAvatarFit({
      ...DEFAULT_AVATAR_FIT,
      mouthGain: known.mouth?.gain ?? DEFAULT_AVATAR_FIT.mouthGain,
      ...(known.fit || {}),
      ...(model.fit || {}),
    }),
    stage: normalizeStageProfile(known.stage, model.stage),
    mouth: normalizeMouthProfile(
      known.mouth,
      !known.mouth && lipSyncParams.length ? { params: { open: lipSyncParams } } : null,
      model.mouth,
    ),
    motionStrategy: normalizeMotionStrategy(known.motionStrategy, model.motionStrategy),
    expressionAliases: { ...(known.expressionAliases || {}), ...(model.expressionAliases || {}) },
    motionAliases: { ...(known.motionAliases || {}), ...(model.motionAliases || {}) },
    motion_groups: model.motion_groups || known.motion_groups || {},
    expressions: model.expressions || known.expressions || [],
    lip_sync_params: lipSyncParams,
    behavior: behaviorProfileForModel(mergedModel),
  };
}

export function mergeAvatarModels(models = []) {
  const merged = new Map();

  for (const item of FALLBACK_MODELS) {
    const profile = profileForModel(item);
    merged.set(profile.url, profile);
  }

  for (const item of models) {
    const profile = profileForModel(item);
    merged.set(profile.url, profile);
  }

  for (const [url, item] of Object.entries(KNOWN_MODEL_PROFILES)) {
    if (!merged.has(url)) {
      merged.set(url, profileForModel({ ...item, url }));
    }
  }

  return Array.from(merged.values());
}
