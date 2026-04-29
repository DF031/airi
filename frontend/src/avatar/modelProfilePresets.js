import { AIRI_LIVE2D_STAGE_DEFAULTS } from '../airi/live2d/airiLive2DConfig';

const EMOTION_KEYS = [
  'neutral',
  'warm',
  'blink',
  'happy',
  'thinking',
  'serious',
  'surprised',
  'apologetic',
  'encouraging',
];

export const NO_EXPRESSION_ALIASES = Object.fromEntries(EMOTION_KEYS.map((key) => [key, []]));

export const DEFAULT_STAGE_PROFILE = {
  anchorX: AIRI_LIVE2D_STAGE_DEFAULTS.anchorX,
  anchorY: AIRI_LIVE2D_STAGE_DEFAULTS.anchorY,
  widthFill: AIRI_LIVE2D_STAGE_DEFAULTS.widthFill,
  heightFill: AIRI_LIVE2D_STAGE_DEFAULTS.heightFill,
  scale: AIRI_LIVE2D_STAGE_DEFAULTS.scale,
  offsetX: 0,
  offsetY: 0,
  minScale: 0.05,
  maxScale: 2.35,
  beatSyncInitialStyle: AIRI_LIVE2D_STAGE_DEFAULTS.beatSyncInitialStyle,
};

export const DEFAULT_MOUTH_PROFILE = {
  gain: 1,
  openMin: 0,
  openMax: 1,
  openBias: 0,
  formGain: 1,
  formBlendMin: 0.35,
  formBlendRange: 0.65,
  staleMs: 180,
  leadSeconds: 0.07,
  lipSyncBlend: 0.66,
  energyNoiseFloor: 0.018,
  energyScale: 7.2,
  energyToLipSync: 0.55,
  cueAudioBlend: 0.72,
  pauseAudioBlend: 0.22,
  speechFloor: 0.13,
  consonantEnergyBlend: 0.22,
  smoothing: {
    open: 0.48,
    shape: 0.42,
    activeShape: 0.38,
    pauseShape: 0.22,
    targetIntervalMs: 40,
    lerpWindowMs: 120,
  },
  lipSync: {
    cap: 0.7,
    volumeScale: 0.9,
    volumeExponent: 0.7,
    mouthUpdateIntervalMs: 50,
    mouthLerpWindowMs: 50,
    shapeOpenCap: 0.72,
  },
  params: {
    open: ['ParamMouthOpenY', 'PARAM_MOUTH_OPEN_Y'],
    form: ['ParamMouthForm', 'PARAM_MOUTH_FORM'],
    form2: ['ParamMouthForm2'],
    vowels: {
      a: ['ParamA'],
      i: ['ParamI'],
      u: ['ParamU'],
      e: ['ParamE'],
      o: ['ParamO'],
    },
    extras: {
      up: ['ParamMouthUp'],
      down: ['ParamMouthDown'],
      angry: ['ParamMouthAngry'],
    },
  },
  vowelGain: {
    a: 1,
    i: 1,
    u: 1,
    e: 1,
    o: 1,
  },
};

export const DEFAULT_MOTION_STRATEGY = {
  idleLoop: ['Idle', 0],
  runtimeMotionStartDelayMs: 300,
  restartIdleAfterFinish: true,
  stopIdleOnSpeech: true,
  preferStoredRuntimeIdle: true,
};

function mergeObject(base, patch) {
  const output = { ...(base || {}) };
  for (const [key, value] of Object.entries(patch || {})) {
    if (Array.isArray(value)) {
      output[key] = [...value];
    } else if (value && typeof value === 'object') {
      output[key] = mergeObject(output[key], value);
    } else if (value !== undefined) {
      output[key] = value;
    }
  }
  return output;
}

function toIdArray(value, fallback = []) {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === 'string') return [value];
  return [...fallback];
}

function normalizeNumber(value, fallback, min = -Infinity, max = Infinity) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function normalizeParams(params = {}) {
  const base = DEFAULT_MOUTH_PROFILE.params;
  const vowels = { ...(params.vowels || {}) };
  const extras = { ...(params.extras || {}) };
  return {
    open: toIdArray(params.open, base.open),
    form: toIdArray(params.form, base.form),
    form2: toIdArray(params.form2, base.form2),
    vowels: {
      a: toIdArray(vowels.a, base.vowels.a),
      i: toIdArray(vowels.i, base.vowels.i),
      u: toIdArray(vowels.u, base.vowels.u),
      e: toIdArray(vowels.e, base.vowels.e),
      o: toIdArray(vowels.o, base.vowels.o),
    },
    extras: {
      up: toIdArray(extras.up, base.extras.up),
      down: toIdArray(extras.down, base.extras.down),
      angry: toIdArray(extras.angry, base.extras.angry),
    },
  };
}

export function normalizeStageProfile(...profiles) {
  const merged = profiles.reduce((output, profile) => mergeObject(output, profile), DEFAULT_STAGE_PROFILE);
  return {
    ...merged,
    anchorX: normalizeNumber(merged.anchorX, DEFAULT_STAGE_PROFILE.anchorX, 0, 1),
    anchorY: normalizeNumber(merged.anchorY, DEFAULT_STAGE_PROFILE.anchorY, 0, 1),
    widthFill: normalizeNumber(merged.widthFill, DEFAULT_STAGE_PROFILE.widthFill, 0.1, 1.4),
    heightFill: normalizeNumber(merged.heightFill, DEFAULT_STAGE_PROFILE.heightFill, 0.1, 1.4),
    scale: normalizeNumber(merged.scale, DEFAULT_STAGE_PROFILE.scale, 0.1, 3),
    offsetX: normalizeNumber(merged.offsetX, DEFAULT_STAGE_PROFILE.offsetX, -400, 400),
    offsetY: normalizeNumber(merged.offsetY, DEFAULT_STAGE_PROFILE.offsetY, -400, 400),
    minScale: normalizeNumber(merged.minScale, DEFAULT_STAGE_PROFILE.minScale, 0.001, 1),
    maxScale: normalizeNumber(merged.maxScale, DEFAULT_STAGE_PROFILE.maxScale, 0.5, 4),
  };
}

export function normalizeMouthProfile(...profiles) {
  const merged = profiles.reduce((output, profile) => mergeObject(output, profile), DEFAULT_MOUTH_PROFILE);
  return {
    ...merged,
    gain: normalizeNumber(merged.gain, DEFAULT_MOUTH_PROFILE.gain, 0.2, 2.4),
    openMin: normalizeNumber(merged.openMin, DEFAULT_MOUTH_PROFILE.openMin, 0, 1),
    openMax: normalizeNumber(merged.openMax, DEFAULT_MOUTH_PROFILE.openMax, 0.05, 1),
    openBias: normalizeNumber(merged.openBias, DEFAULT_MOUTH_PROFILE.openBias, 0, 0.4),
    formGain: normalizeNumber(merged.formGain, DEFAULT_MOUTH_PROFILE.formGain, 0, 2),
    formBlendMin: normalizeNumber(merged.formBlendMin, DEFAULT_MOUTH_PROFILE.formBlendMin, 0, 1),
    formBlendRange: normalizeNumber(merged.formBlendRange, DEFAULT_MOUTH_PROFILE.formBlendRange, 0, 1),
    staleMs: normalizeNumber(merged.staleMs, DEFAULT_MOUTH_PROFILE.staleMs, 40, 600),
    leadSeconds: normalizeNumber(merged.leadSeconds, DEFAULT_MOUTH_PROFILE.leadSeconds, -0.1, 0.3),
    lipSyncBlend: normalizeNumber(merged.lipSyncBlend, DEFAULT_MOUTH_PROFILE.lipSyncBlend, 0, 1),
    energyNoiseFloor: normalizeNumber(merged.energyNoiseFloor, DEFAULT_MOUTH_PROFILE.energyNoiseFloor, 0, 0.2),
    energyScale: normalizeNumber(merged.energyScale, DEFAULT_MOUTH_PROFILE.energyScale, 0.5, 20),
    energyToLipSync: normalizeNumber(merged.energyToLipSync, DEFAULT_MOUTH_PROFILE.energyToLipSync, 0, 1),
    cueAudioBlend: normalizeNumber(merged.cueAudioBlend, DEFAULT_MOUTH_PROFILE.cueAudioBlend, 0, 1),
    pauseAudioBlend: normalizeNumber(merged.pauseAudioBlend, DEFAULT_MOUTH_PROFILE.pauseAudioBlend, 0, 1),
    speechFloor: normalizeNumber(merged.speechFloor, DEFAULT_MOUTH_PROFILE.speechFloor, 0, 0.5),
    consonantEnergyBlend: normalizeNumber(merged.consonantEnergyBlend, DEFAULT_MOUTH_PROFILE.consonantEnergyBlend, 0, 1),
    smoothing: {
      open: normalizeNumber(merged.smoothing?.open, DEFAULT_MOUTH_PROFILE.smoothing.open, 0.02, 1),
      shape: normalizeNumber(merged.smoothing?.shape, DEFAULT_MOUTH_PROFILE.smoothing.shape, 0.02, 1),
      activeShape: normalizeNumber(merged.smoothing?.activeShape, DEFAULT_MOUTH_PROFILE.smoothing.activeShape, 0.02, 1),
      pauseShape: normalizeNumber(merged.smoothing?.pauseShape, DEFAULT_MOUTH_PROFILE.smoothing.pauseShape, 0.02, 1),
      targetIntervalMs: normalizeNumber(merged.smoothing?.targetIntervalMs, DEFAULT_MOUTH_PROFILE.smoothing.targetIntervalMs, 10, 120),
      lerpWindowMs: normalizeNumber(merged.smoothing?.lerpWindowMs, DEFAULT_MOUTH_PROFILE.smoothing.lerpWindowMs, 40, 260),
    },
    lipSync: {
      cap: normalizeNumber(merged.lipSync?.cap, DEFAULT_MOUTH_PROFILE.lipSync.cap, 0.1, 1),
      volumeScale: normalizeNumber(merged.lipSync?.volumeScale, DEFAULT_MOUTH_PROFILE.lipSync.volumeScale, 0.1, 3),
      volumeExponent: normalizeNumber(merged.lipSync?.volumeExponent, DEFAULT_MOUTH_PROFILE.lipSync.volumeExponent, 0.1, 2),
      mouthUpdateIntervalMs: normalizeNumber(merged.lipSync?.mouthUpdateIntervalMs, DEFAULT_MOUTH_PROFILE.lipSync.mouthUpdateIntervalMs, 10, 140),
      mouthLerpWindowMs: normalizeNumber(merged.lipSync?.mouthLerpWindowMs, DEFAULT_MOUTH_PROFILE.lipSync.mouthLerpWindowMs, 10, 260),
      shapeOpenCap: normalizeNumber(merged.lipSync?.shapeOpenCap, DEFAULT_MOUTH_PROFILE.lipSync.shapeOpenCap, 0.1, 1),
    },
    params: normalizeParams(merged.params),
    vowelGain: {
      a: normalizeNumber(merged.vowelGain?.a, DEFAULT_MOUTH_PROFILE.vowelGain.a, 0, 2),
      i: normalizeNumber(merged.vowelGain?.i, DEFAULT_MOUTH_PROFILE.vowelGain.i, 0, 2),
      u: normalizeNumber(merged.vowelGain?.u, DEFAULT_MOUTH_PROFILE.vowelGain.u, 0, 2),
      e: normalizeNumber(merged.vowelGain?.e, DEFAULT_MOUTH_PROFILE.vowelGain.e, 0, 2),
      o: normalizeNumber(merged.vowelGain?.o, DEFAULT_MOUTH_PROFILE.vowelGain.o, 0, 2),
    },
  };
}

export function normalizeMotionStrategy(...profiles) {
  const merged = profiles.reduce((output, profile) => mergeObject(output, profile), DEFAULT_MOTION_STRATEGY);
  const idleLoop = Array.isArray(merged.idleLoop) && merged.idleLoop.length
    ? [String(merged.idleLoop[0]), normalizeNumber(merged.idleLoop[1], 0, 0, 99)]
    : DEFAULT_MOTION_STRATEGY.idleLoop;
  return {
    ...merged,
    idleLoop,
    runtimeMotionStartDelayMs: normalizeNumber(
      merged.runtimeMotionStartDelayMs,
      DEFAULT_MOTION_STRATEGY.runtimeMotionStartDelayMs,
      0,
      3000,
    ),
    restartIdleAfterFinish: merged.restartIdleAfterFinish !== false,
    stopIdleOnSpeech: merged.stopIdleOnSpeech !== false,
    preferStoredRuntimeIdle: merged.preferStoredRuntimeIdle !== false,
  };
}

export const MODEL_PROFILE_PRESETS = {
  '/Epsilon/runtime/Epsilon.model3.json': {
    stage: { widthFill: 0.96, heightFill: 0.97 },
    mouth: {
      gain: 1.12,
      openMax: 0.86,
      lipSyncBlend: 0.58,
      params: { open: ['PARAM_MOUTH_OPEN_Y'], form: [], form2: [], vowels: { a: [], i: [], u: [], e: [], o: [] } },
    },
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
  '/izumi/runtime/izumi_illust.model3.json': {
    stage: { widthFill: 0.96, heightFill: 0.97 },
    mouth: {
      gain: 1.1,
      openMax: 0.84,
      lipSyncBlend: 0.58,
      params: { open: ['PARAM_MOUTH_OPEN_Y'], form: [], form2: [], vowels: { a: [], i: [], u: [], e: [], o: [] } },
    },
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
  '/live2d/hiyori/Hiyori.model3.json': {
    stage: { widthFill: 0.96, heightFill: 0.97 },
    mouth: {
      gain: 1.08,
      openMax: 0.82,
      formGain: 0.82,
      lipSyncBlend: 0.64,
      params: { open: ['ParamMouthOpenY'], form: ['ParamMouthForm'], form2: [], vowels: { a: [], i: [], u: [], e: [], o: [] } },
    },
    expressionAliases: NO_EXPRESSION_ALIASES,
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
  '/live2d/natori/Natori.model3.json': {
    stage: { widthFill: 0.96, heightFill: 0.97 },
    mouth: {
      gain: 1.1,
      openMax: 0.86,
      formGain: 0.92,
      lipSyncBlend: 0.68,
      params: { open: ['ParamMouthOpenY'], form: ['ParamMouthForm'], form2: ['ParamMouthForm2'], vowels: { a: [], i: [], u: [], e: [], o: [] } },
    },
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
  '/mao_pro_zh/runtime/mao_pro.model3.json': {
    stage: { widthFill: 0.98, heightFill: 0.98 },
    mouth: {
      gain: 1.24,
      openMax: 0.92,
      lipSyncBlend: 0.72,
      energyScale: 6.6,
      params: {
        open: [],
        form: [],
        form2: [],
        vowels: { a: ['ParamA'], i: ['ParamI'], u: ['ParamU'], e: ['ParamE'], o: ['ParamO'] },
        extras: { up: ['ParamMouthUp'], down: ['ParamMouthDown'], angry: ['ParamMouthAngry'] },
      },
      vowelGain: { a: 1.08, i: 0.94, u: 1, e: 0.98, o: 1.05 },
    },
    expressionAliases: {
      neutral: ['exp_01'],
      warm: ['exp_01'],
      blink: ['exp_02'],
      happy: ['exp_03', 'exp_04'],
      thinking: ['exp_05'],
      serious: ['exp_06'],
      surprised: ['exp_07'],
      apologetic: ['exp_08'],
      encouraging: ['exp_04'],
    },
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
  '/shizuku/runtime/shizuku.model3.json': {
    stage: { widthFill: 0.96, heightFill: 0.97 },
    mouth: {
      gain: 1.12,
      openMax: 0.84,
      lipSyncBlend: 0.56,
      params: { open: ['PARAM_MOUTH_OPEN_Y'], form: [], form2: [], vowels: { a: [], i: [], u: [], e: [], o: [] } },
    },
    expressionAliases: NO_EXPRESSION_ALIASES,
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
  '/tororo_hijiki/hijiki/runtime/hijiki.model3.json': {
    stage: { widthFill: 0.9, heightFill: 0.9 },
    mouth: {
      gain: 1.18,
      openMax: 0.82,
      lipSyncBlend: 0.5,
      params: { open: ['PARAM_MOUTH_OPEN_Y'], form: [], form2: [], vowels: { a: [], i: [], u: [], e: [], o: [] } },
    },
    expressionAliases: NO_EXPRESSION_ALIASES,
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
  '/tororo_hijiki/tororo/runtime/tororo.model3.json': {
    stage: { widthFill: 0.9, heightFill: 0.9 },
    mouth: {
      gain: 1.18,
      openMax: 0.82,
      lipSyncBlend: 0.5,
      params: { open: ['PARAM_MOUTH_OPEN_Y'], form: [], form2: [], vowels: { a: [], i: [], u: [], e: [], o: [] } },
    },
    expressionAliases: NO_EXPRESSION_ALIASES,
    motionStrategy: { idleLoop: ['Idle', 0] },
  },
};
