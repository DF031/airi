import { createBeatSyncController } from '../airi/live2d/beatSync';
import {
  AIRI_BEAT_SYNC_DEFAULTS,
  AIRI_LIVE2D_MODEL_PARAMETERS,
} from '../airi/live2d/airiLive2DConfig';
import { createLive2DIdleEyeFocus, disableIdleEyeFocusCurves } from '../airi/live2d/idleEyeFocus';
import {
  createLive2DMotionManagerUpdate,
  createMotionUpdatePluginAutoEyeBlink,
  createMotionUpdatePluginBeatSync,
  createMotionUpdatePluginIdleDisable,
  createMotionUpdatePluginPresence,
} from '../airi/live2d/motionManager';
import { normalizeAvatarDebugConfig } from './emotionSystem';
import { normalizeMouthProfile } from './modelProfilePresets';

const PRESENCE_PARAMS = {
  angleX: 'ParamAngleX',
  angleY: 'ParamAngleY',
  angleZ: 'ParamAngleZ',
  bodyX: 'ParamBodyAngleX',
  bodyY: 'ParamBodyAngleY',
  bodyZ: 'ParamBodyAngleZ',
  breath: 'ParamBreath',
  cheek: 'ParamCheek',
  eyeLOpen: 'ParamEyeLOpen',
  eyeROpen: 'ParamEyeROpen',
  eyeX: 'ParamEyeBallX',
  eyeY: 'ParamEyeBallY',
  mouthA: 'ParamA',
  mouthI: 'ParamI',
  mouthU: 'ParamU',
  mouthE: 'ParamE',
  mouthO: 'ParamO',
  mouthUp: 'ParamMouthUp',
  mouthDown: 'ParamMouthDown',
  mouthAngry: 'ParamMouthAngry',
  mouthOpenY: 'ParamMouthOpenY',
  mouthForm: 'ParamMouthForm',
  mouthForm2: 'ParamMouthForm2',
  mouthOpenYUpper: 'PARAM_MOUTH_OPEN_Y',
  mouthFormUpper: 'PARAM_MOUTH_FORM',
};

const DEFAULT_MODEL_PARAMETERS = AIRI_LIVE2D_MODEL_PARAMETERS;

const MODEL_PARAMETER_IDS = {
  angleX: 'ParamAngleX',
  angleY: 'ParamAngleY',
  angleZ: 'ParamAngleZ',
  leftEyeOpen: 'ParamEyeLOpen',
  rightEyeOpen: 'ParamEyeROpen',
  leftEyeSmile: 'ParamEyeSmile',
  rightEyeSmile: 'ParamEyeSmile',
  leftEyebrowLR: 'ParamBrowLX',
  rightEyebrowLR: 'ParamBrowRX',
  leftEyebrowY: 'ParamBrowLY',
  rightEyebrowY: 'ParamBrowRY',
  leftEyebrowAngle: 'ParamBrowLAngle',
  rightEyebrowAngle: 'ParamBrowRAngle',
  leftEyebrowForm: 'ParamBrowLForm',
  rightEyebrowForm: 'ParamBrowRForm',
  mouthOpen: 'ParamMouthOpenY',
  mouthForm: 'ParamMouthForm',
  cheek: 'ParamCheek',
  bodyAngleX: 'ParamBodyAngleX',
  bodyAngleY: 'ParamBodyAngleY',
  bodyAngleZ: 'ParamBodyAngleZ',
  breath: 'ParamBreath',
};

const REST_MOUTH_SHAPE = {
  a: 0.06,
  i: 0.02,
  u: 0.02,
  e: 0.02,
  o: 0.03,
  up: 0,
  down: 0,
  angry: 0,
  form: 0,
  form2: 0,
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function setCoreParam(coreModel, id, value) {
  try {
    coreModel?.setParameterValueById?.(id, value);
  } catch {
    // Individual Live2D models expose different parameter sets.
  }
}

function setCoreParams(coreModel, ids = [], value) {
  for (const id of new Set(ids.filter(Boolean))) {
    setCoreParam(coreModel, id, value);
  }
}

function currentModelProfile() {
  return window.__AIRI_AVATAR_CONFIG?.modelProfile || {};
}

function currentMouthProfile(profile = currentModelProfile()) {
  return normalizeMouthProfile(profile?.mouth);
}

export function setAvatarParam(model, id, value) {
  setCoreParam(model?.internalModel?.coreModel, id, value);
}

export function ensureEyesOpen(model) {
  setAvatarParam(model, PRESENCE_PARAMS.eyeLOpen, 1);
  setAvatarParam(model, PRESENCE_PARAMS.eyeROpen, 1);
}

export function setMouthFormOnCore(coreModel, openness, shape = {}, mouthProfile = currentMouthProfile()) {
  const profile = normalizeMouthProfile(mouthProfile);
  const value = clamp(
    openness > 0
      ? openness + profile.openBias
      : openness,
    profile.openMin,
    profile.openMax,
  );
  const weights = {
    ...REST_MOUTH_SHAPE,
    a: 1,
    ...shape,
  };
  const standardForm = clamp(
    weights.form || (weights.i * 0.55 + weights.e * 0.35 + weights.up * 0.25 - weights.u * 0.5 - weights.o * 0.55 - weights.down * 0.2),
    -1,
    1,
  );
  const standardForm2 = clamp(weights.form2 || standardForm, -1, 1);
  const formBlend = profile.formBlendMin + value * profile.formBlendRange;
  const params = profile.params;

  setCoreParams(coreModel, params.open, value);
  setCoreParams(coreModel, params.form, standardForm * formBlend * profile.formGain);
  setCoreParams(coreModel, params.form2, standardForm2 * formBlend * profile.formGain);

  setCoreParams(coreModel, params.vowels.a, value * weights.a * profile.vowelGain.a);
  setCoreParams(coreModel, params.vowels.i, value * weights.i * profile.vowelGain.i);
  setCoreParams(coreModel, params.vowels.u, value * weights.u * profile.vowelGain.u);
  setCoreParams(coreModel, params.vowels.e, value * weights.e * profile.vowelGain.e);
  setCoreParams(coreModel, params.vowels.o, value * weights.o * profile.vowelGain.o);
  setCoreParams(coreModel, params.extras.up, clamp(value * weights.up, -1, 1));
  setCoreParams(coreModel, params.extras.down, clamp(value * weights.down, -1, 1));
  setCoreParams(coreModel, params.extras.angry, clamp(value * weights.angry, -1, 1));
}

export function setMouthForm(model, openness, shape = {}, mouthProfile = currentMouthProfile()) {
  setMouthFormOnCore(model?.internalModel?.coreModel, openness, shape, mouthProfile);
}

export function resetMouthForm(model) {
  setMouthForm(model, 0);
}

export function prepareAiriLive2DModel(model) {
  if (!model?.internalModel) return;

  const profile = currentModelProfile();
  const modelParameters = {
    ...AIRI_LIVE2D_MODEL_PARAMETERS,
    ...(profile.modelParameters || {}),
  };
  for (const [key, value] of Object.entries(modelParameters)) {
    setAvatarParam(model, MODEL_PARAMETER_IDS[key], value);
  }
  disableIdleEyeFocusCurves(model, [PRESENCE_PARAMS.eyeX, PRESENCE_PARAMS.eyeY]);
}

function createPresenceState(modelProfile = currentModelProfile()) {
  return {
    mode: 'idle',
    modelProfile,
    pointerTarget: { x: 0, y: 0 },
    currentFocus: { x: 0, y: 0 },
    speechEnergy: 0,
    speechEnergyTarget: 0,
    lastPointerAt: 0,
    modelParameters: { ...DEFAULT_MODEL_PARAMETERS },
    debugConfig: normalizeAvatarDebugConfig(window.__AIRI_AVATAR_DEBUG_CONFIG),
    mouthSync: {
      targetOpen: 0,
      open: 0,
      targetShape: { ...REST_MOUTH_SHAPE },
      shape: { ...REST_MOUTH_SHAPE },
      lastAt: 0,
    },
  };
}

function modeFromSpeechStatus(state, fallback) {
  if (state === 'playing') return 'speaking';
  if (state === 'loading' || state === 'queued') return 'thinking';
  if (state === 'interaction') return 'interaction';
  if (state === 'idle_behavior') return 'idle_behavior';
  if (state === 'ready' || state === 'idle' || state === 'error' || state === 'unavailable') return 'idle';
  return fallback;
}

function modeFromAvatarAction(style, fallback) {
  if (style === 'speaking') return 'speaking';
  if (style === 'listening') return 'listening';
  if (style === 'thinking') return 'thinking';
  return fallback;
}

function hookMotionManager(model, state, idleEyeFocus, beatSync) {
  const internalModel = model?.internalModel;
  const motionManager = internalModel?.motionManager;
  if (!internalModel?.coreModel || !motionManager?.update) return () => {};

  const originalUpdate = motionManager.update;
  const motionUpdate = createLive2DMotionManagerUpdate({
    internalModel,
    motionManager,
    modelParameters: state.modelParameters,
    live2dIdleAnimationEnabled: () => state.debugConfig.live2dIdleAnimationEnabled,
    live2dAutoBlinkEnabled: () => state.debugConfig.live2dAutoBlinkEnabled,
    live2dForceAutoBlinkEnabled: () => state.debugConfig.live2dForceAutoBlinkEnabled,
  });

  motionUpdate.register(createMotionUpdatePluginIdleDisable(PRESENCE_PARAMS), 'pre');
  motionUpdate.register(createMotionUpdatePluginPresence({
    state,
    idleEyeFocus,
    params: PRESENCE_PARAMS,
  }), 'post');
  motionUpdate.register(createMotionUpdatePluginBeatSync(beatSync, PRESENCE_PARAMS), 'post');
  motionUpdate.register(createMotionUpdatePluginAutoEyeBlink({
    params: PRESENCE_PARAMS,
    autoEnabled: () => state.debugConfig.live2dAutoBlinkEnabled,
    forceEnabled: () => state.debugConfig.live2dForceAutoBlinkEnabled,
  }), 'post');

  const updateWithAiriRuntime = function updateWithAiriRuntime(coreModel, now) {
    return motionUpdate.hookUpdate(coreModel, now, originalUpdate);
  };
  motionManager.update = updateWithAiriRuntime;

  return () => {
    if (motionManager.update === updateWithAiriRuntime) {
      motionManager.update = originalUpdate;
    }
  };
}

function applyMouthSyncToCore(coreModel, mouthSync) {
  if (!coreModel || !mouthSync) return;

  const mouthProfile = currentMouthProfile(window.__AIRI_AVATAR_RUNTIME?.state?.modelProfile);
  const now = performance.now();
  const stale = !mouthSync.lastAt || now - mouthSync.lastAt > mouthProfile.staleMs;
  const targetOpen = stale ? 0 : clamp(mouthSync.targetOpen || 0, 0, 1);
  const targetShape = stale ? REST_MOUTH_SHAPE : mouthSync.targetShape;

  mouthSync.open += (targetOpen - mouthSync.open) * mouthProfile.smoothing.open;
  for (const key of Object.keys(REST_MOUTH_SHAPE)) {
    mouthSync.shape[key] += (
      ((targetShape || REST_MOUTH_SHAPE)[key] ?? REST_MOUTH_SHAPE[key]) - mouthSync.shape[key]
    ) * mouthProfile.smoothing.shape;
  }

  setMouthFormOnCore(coreModel, mouthSync.open, mouthSync.shape, mouthProfile);

  try {
    coreModel.update?.();
  } catch {
    // Some wrapped core models update themselves inside the renderer.
  }
}

function hookDrawMouthSync(model, state) {
  const internalModel = model?.internalModel;
  const coreModel = internalModel?.coreModel;
  if (!internalModel?.draw || !coreModel) return () => {};

  const originalDraw = internalModel.draw;
  const drawWithMouthSync = function drawWithMouthSync(...args) {
    applyMouthSyncToCore(coreModel, state.mouthSync);
    return originalDraw.apply(this, args);
  };
  internalModel.draw = drawWithMouthSync;

  return () => {
    if (internalModel.draw === drawWithMouthSync) {
      internalModel.draw = originalDraw;
    }
  };
}

export function installAvatarPresence({ model, element }) {
  if (!model || !element) return () => {};

  prepareAiriLive2DModel(model);

  let disposed = false;
  const state = createPresenceState();
  const idleEyeFocus = createLive2DIdleEyeFocus();
  const beatSync = createBeatSyncController({
    baseAngles: () => ({
      x: state.modelParameters.angleX,
      y: state.modelParameters.angleY,
      z: state.modelParameters.angleZ,
    }),
    initialStyle: state.modelProfile?.stage?.beatSyncInitialStyle || AIRI_BEAT_SYNC_DEFAULTS.initialStyle,
  });
  beatSync.setStyle(state.debugConfig.beatStyle);
  beatSync.setAutoStyleShift(state.debugConfig.autoBeatStyle);
  const restoreMotionManager = hookMotionManager(model, state, idleEyeFocus, beatSync);
  const restoreDrawMouthSync = hookDrawMouthSync(model, state);

  const updateTarget = (event) => {
    if (disposed) return;
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    state.pointerTarget.x = clamp(((event.clientX - rect.left) / rect.width - 0.5) * 2, -1, 1);
    state.pointerTarget.y = clamp(((event.clientY - rect.top) / rect.height - 0.5) * 2, -1, 1);
    state.lastPointerAt = performance.now();
  };

  const resetTarget = () => {
    state.pointerTarget.x = 0;
    state.pointerTarget.y = 0;
    state.lastPointerAt = 0;
  };

  const handleSpeechStatus = (event) => {
    state.mode = modeFromSpeechStatus(event.detail?.state, state.mode);
  };

  const handleAvatarAction = (event) => {
    state.mode = modeFromAvatarAction(event.detail?.style, state.mode);
  };

  const handleSpeechEnergy = (event) => {
    const value = clamp(Number(event.detail?.value || 0), 0, 1);
    state.speechEnergyTarget = Math.max(state.speechEnergyTarget, value);
    if (value > 0.2) {
      beatSync.scheduleBeat(performance.now());
    }
  };

  const handleDebugConfig = (event) => {
    state.debugConfig = normalizeAvatarDebugConfig({
      ...state.debugConfig,
      ...(event.detail || {}),
    });
    beatSync.setStyle(state.debugConfig.beatStyle);
    beatSync.setAutoStyleShift(state.debugConfig.autoBeatStyle);
  };

  const handleModelProfile = (event) => {
    state.modelProfile = event.detail || currentModelProfile();
  };

  const handleMouthSync = (event) => {
    const detail = event.detail || {};
    state.mouthSync.targetOpen = clamp(Number(detail.value || 0), 0, 1);
    state.mouthSync.targetShape = {
      ...REST_MOUTH_SHAPE,
      ...(detail.shape || {}),
    };
    state.mouthSync.lastAt = performance.now();
  };

  window.__AIRI_AVATAR_RUNTIME = {
    model,
    state,
    readParam: (id) => {
      try {
        return model?.internalModel?.coreModel?.getParameterValueById?.(id);
      } catch {
        return null;
      }
    },
    setMouth: (value) => {
      state.mouthSync.targetOpen = clamp(Number(value || 0), 0, 1);
      state.mouthSync.lastAt = performance.now();
    },
  };

  window.addEventListener('pointermove', updateTarget, { passive: true });
  window.addEventListener('blur', resetTarget);
  window.addEventListener('speech_status', handleSpeechStatus);
  window.addEventListener('avatar_action', handleAvatarAction);
  window.addEventListener('avatar_speech_energy', handleSpeechEnergy);
  window.addEventListener('avatar_debug_config', handleDebugConfig);
  window.addEventListener('avatar_model_profile', handleModelProfile);
  window.addEventListener('avatar_mouth_sync', handleMouthSync);
  element.addEventListener('pointerleave', resetTarget);

  return () => {
    disposed = true;
    window.removeEventListener('pointermove', updateTarget);
    window.removeEventListener('blur', resetTarget);
    window.removeEventListener('speech_status', handleSpeechStatus);
    window.removeEventListener('avatar_action', handleAvatarAction);
    window.removeEventListener('avatar_speech_energy', handleSpeechEnergy);
    window.removeEventListener('avatar_debug_config', handleDebugConfig);
    window.removeEventListener('avatar_model_profile', handleModelProfile);
    window.removeEventListener('avatar_mouth_sync', handleMouthSync);
    element.removeEventListener('pointerleave', resetTarget);
    if (window.__AIRI_AVATAR_RUNTIME?.model === model) {
      delete window.__AIRI_AVATAR_RUNTIME;
    }
    restoreDrawMouthSync();
    restoreMotionManager();
  };
}
