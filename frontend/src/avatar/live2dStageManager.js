import * as PIXI from 'pixi.js';
import { DEFAULT_BEHAVIOR_PROFILE } from './modelBehaviorProfiles';
import { DEFAULT_MODEL_URL, normalizeAvatarFit } from './modelRegistry';
import { normalizeMotionStrategy, normalizeStageProfile } from './modelProfilePresets';
import { installAvatarPresence } from './avatarRuntime';
import { applyAvatarAction, playTextToSpeech, stopTextToSpeech } from '../utils/audioHandler';

window.PIXI = PIXI;

export const READY_STATUS = DEFAULT_BEHAVIOR_PROFILE.readyStatus;

const ACTIVE_SPEECH_STATES = new Set(['loading', 'queued', 'playing', 'interaction', 'idle_behavior']);

function randomBetween(min, max) {
  return Math.floor(min + Math.random() * (max - min));
}

function randomDelay(config = {}, minKey, maxKey, fallbackMin, fallbackMax) {
  return randomBetween(
    Number(config[minKey] ?? fallbackMin),
    Number(config[maxKey] ?? fallbackMax),
  );
}

function dispatchSpeechStatus(detail) {
  window.dispatchEvent(new CustomEvent('speech_status', { detail }));
}

function stageProfileFor(profile) {
  return normalizeStageProfile(profile?.stage);
}

function rememberInitialModelSize(model, profile) {
  const stage = stageProfileFor(profile);
  try {
    model.anchor?.set?.(stage.anchorX, stage.anchorY);
  } catch {
    // Older wrappers may not expose an anchor object.
  }
  model.scale.set(1);
  model.__airiInitialWidth = model.width || model.__airiInitialWidth || 1;
  model.__airiInitialHeight = model.height || model.__airiInitialHeight || 1;
}

function positionModel(app, model, modelFit, modelProfile) {
  const fit = normalizeAvatarFit(modelFit);
  const stage = stageProfileFor(modelProfile);
  const width = app.renderer.width;
  const height = app.renderer.height;
  const baseWidth = model.__airiInitialWidth || model.width || 1;
  const baseHeight = model.__airiInitialHeight || model.height || 1;
  const autoScale = Math.min((width * stage.widthFill) / baseWidth, (height * stage.heightFill) / baseHeight);
  const scale = Math.min(stage.maxScale, Math.max(stage.minScale, autoScale * fit.scale * stage.scale));
  model.scale.set(scale);
  model.x = (width / 2) + fit.offsetX + stage.offsetX;
  model.y = (height / 2) + fit.offsetY + stage.offsetY;
}

function normalizeDefinitionName(definition, index, prefix) {
  return String(
    definition?.Name
      || definition?.name
      || definition?.File
      || definition?.file
      || `${prefix} ${index + 1}`,
  );
}

function collectMotionCapabilities(motionManager) {
  const definitions = motionManager?.definitions || {};
  const groups = {};
  const motions = [];

  Object.entries(definitions).forEach(([group, groupDefinitions]) => {
    const list = Array.isArray(groupDefinitions) ? groupDefinitions : [];
    groups[group] = list.length;
    list.forEach((definition, index) => {
      motions.push({
        group,
        index,
        file: definition?.File || definition?.file || '',
        name: normalizeDefinitionName(definition, index, group),
      });
    });
  });

  return { groups, motions };
}

function collectExpressionCapabilities(expressionManager) {
  const definitions = expressionManager?.definitions || [];
  if (!Array.isArray(definitions)) return [];

  return definitions.map((definition, index) => ({
    index,
    name: normalizeDefinitionName(definition, index, 'Expression'),
    file: definition?.File || definition?.file || '',
  }));
}

function readCoreParameterIds(coreModel) {
  try {
    if (Array.isArray(coreModel?._parameterIds)) {
      return coreModel._parameterIds.map(String);
    }
    if (typeof coreModel?.getParameterIds === 'function') {
      return Array.from(coreModel.getParameterIds()).map(String);
    }
    const ids = coreModel?._model?.parameters?.ids;
    if (ids) return Array.from(ids).map(String);
  } catch {
    // Some wrapped Cubism models keep parameter metadata private.
  }
  return [];
}

function collectModelCapabilities(model, profile) {
  const internalModel = model?.internalModel;
  const motionCapabilities = collectMotionCapabilities(internalModel?.motionManager);

  return {
    modelName: internalModel?.settings?.name || profile?.name || '',
    motionGroups: motionCapabilities.groups,
    motions: motionCapabilities.motions,
    expressions: collectExpressionCapabilities(internalModel?.motionManager?.expressionManager),
    parameters: readCoreParameterIds(internalModel?.coreModel),
    lipSyncParams: Array.isArray(profile?.lip_sync_params) ? profile.lip_sync_params : [],
    profile: {
      name: profile?.behavior?.name || profile?.name || '',
      mouthParams: profile?.mouth?.params || {},
      motionStrategy: profile?.motionStrategy || {},
      stage: profile?.stage || {},
    },
  };
}

function readRuntimeMotionSelection(profile) {
  const strategy = normalizeMotionStrategy(profile?.motionStrategy);
  const group = window.localStorage?.getItem?.('selected-runtime-motion-group');
  const indexValue = window.localStorage?.getItem?.('selected-runtime-motion-index');
  const index = Number.parseInt(indexValue, 10);
  if (strategy.preferStoredRuntimeIdle && group !== null && Number.isFinite(index)) return { group, index };
  return { group: strategy.idleLoop[0], index: strategy.idleLoop[1] };
}

function playRuntimeMotion(model, selection = readRuntimeMotionSelection()) {
  if (!model || !selection) return;
  try {
    const forcePriority = window.__AIRI_MOTION_PRIORITY_FORCE;
    if (forcePriority !== undefined) model.motion(selection.group, selection.index, forcePriority);
    else model.motion(selection.group, selection.index);
  } catch (error) {
    console.warn('[avatar] runtime motion failed:', selection, error);
  }
}

function installRuntimeMotionLoop(model, getState = () => ({})) {
  const motionManager = model?.internalModel?.motionManager;
  if (!motionManager?.on) return () => {};

  const restartSelectedMotion = () => {
    const runtimeState = getState();
    const profile = runtimeState.profile;
    const strategy = normalizeMotionStrategy(profile?.motionStrategy);
    if (!strategy.restartIdleAfterFinish || runtimeState.busy) return;
    const selection = readRuntimeMotionSelection(profile);
    if (!selection) return;
    window.requestAnimationFrame(() => playRuntimeMotion(model, selection));
  };

  window.setTimeout(
    restartSelectedMotion,
    normalizeMotionStrategy(getState().profile?.motionStrategy).runtimeMotionStartDelayMs,
  );
  motionManager.on('motionFinish', restartSelectedMotion);

  return () => {
    if (motionManager.off) motionManager.off('motionFinish', restartSelectedMotion);
    else motionManager.removeListener?.('motionFinish', restartSelectedMotion);
  };
}

export class Live2DStageManager {
  constructor({ canvas, getModelFit, getModelProfile }) {
    this.canvas = canvas;
    this.getModelFit = getModelFit;
    this.getModelProfile = getModelProfile;
    this.app = null;
    this.model = null;
    this.cleanupPresence = null;
    this.resizeObserver = null;
    this.interactionTimer = null;
    this.idleTimer = null;
    this.idleResetTimer = null;
    this.cleanupRuntimeMotionLoop = null;
    this.avatarBusy = false;
    this.idleSuspendedUntil = 0;
    this.disposed = false;
    this.loadedModelUrl = '';
    this.capabilities = null;

    this.handleSpeakEvent = (event) => {
      playTextToSpeech(event.detail, this.model, this.app);
    };
    this.handleSpeechCancel = (event) => {
      stopTextToSpeech(this.model, event.detail?.message);
    };
    this.handleAvatarAction = (event) => {
      this.suspendIdle(8000);
      applyAvatarAction(this.model, event.detail);
    };
    this.handleSpeechStatus = (event) => {
      const state = event.detail?.state;
      if (ACTIVE_SPEECH_STATES.has(state)) {
        this.avatarBusy = true;
        this.clearIdleTimers();
        if (state === 'playing' && normalizeMotionStrategy(this.getModelProfile?.()?.motionStrategy).stopIdleOnSpeech) {
          this.stopIdleMotions();
        }
        return;
      }

      if (state === 'ready' || state === 'idle' || state === 'error' || state === 'unavailable') {
        this.avatarBusy = false;
        this.scheduleIdleBehavior();
      }
    };
    this.handlePointerDown = (event) => this.handleInteraction(event);
    this.handleModelHit = (hitAreas) => this.handleHitAreas(hitAreas);
  }

  behaviorProfile() {
    return this.getModelProfile?.()?.behavior || DEFAULT_BEHAVIOR_PROFILE;
  }

  readyStatus() {
    return this.behaviorProfile().readyStatus || READY_STATUS;
  }

  resetAction() {
    return this.behaviorProfile().resetAction || DEFAULT_BEHAVIOR_PROFILE.resetAction;
  }

  initialAction() {
    return this.behaviorProfile().initialAction || DEFAULT_BEHAVIOR_PROFILE.initialAction;
  }

  async initialize(modelUrl = DEFAULT_MODEL_URL) {
    if (!this.canvas || this.disposed) return;
    await this.ensurePixiApp();
    this.attachEvents();
    await this.loadModel(modelUrl);
  }

  async ensurePixiApp() {
    if (this.app) return;
    this.app = new PIXI.Application({
      view: this.canvas,
      autoStart: true,
      backgroundAlpha: 0,
      resizeTo: this.canvas.parentElement,
    });
  }

  async loadModel(modelUrl = DEFAULT_MODEL_URL) {
    const requestedUrl = modelUrl || DEFAULT_MODEL_URL;
    try {
      const { Live2DModel, SoundManager, MotionPriority, config } = await import('pixi-live2d-display/cubism4');
      window.__AIRI_MOTION_PRIORITY_FORCE = MotionPriority?.FORCE;
      if (config) {
        config.sound = false;
        config.motionSync = false;
      }
      if (SoundManager) {
        SoundManager.volume = 0;
      }

      const nextModel = await Live2DModel.from(requestedUrl);
      if (this.disposed) {
        nextModel.destroy();
        return;
      }

      this.replaceModel(nextModel);
      this.loadedModelUrl = requestedUrl;
      dispatchSpeechStatus(this.readyStatus());
      window.dispatchEvent(new CustomEvent('avatar_model_loaded', {
        detail: { url: requestedUrl },
      }));
      this.scheduleIdleBehavior(9000);
      console.log('[avatar] Live2D model loaded:', requestedUrl);
    } catch (error) {
      console.error('[avatar] Live2D init failed:', error);
      const fallbackUrl = this.loadedModelUrl || DEFAULT_MODEL_URL;
      window.dispatchEvent(new CustomEvent('avatar_model_load_failed', {
        detail: { url: requestedUrl, fallbackUrl },
      }));
      dispatchSpeechStatus({ state: 'error', message: '数字人加载失败，已保留可用模型' });
      if (!this.model && requestedUrl !== DEFAULT_MODEL_URL) {
        await this.loadModel(DEFAULT_MODEL_URL);
      }
    }
  }

  replaceModel(nextModel) {
    this.clearIdleTimers();
    stopTextToSpeech(this.model, '模型切换，语音已停止');
    this.cleanupPresence?.();
    this.cleanupPresence = null;
    this.cleanupRuntimeMotionLoop?.();
    this.cleanupRuntimeMotionLoop = null;

    if (this.model && this.app) {
      this.app.stage.removeChild(this.model);
      this.model.destroy();
    }

    this.model = nextModel;
    this.updateProfile();
    rememberInitialModelSize(nextModel, this.getModelProfile?.());
    this.app.stage.addChild(nextModel);
    this.updateModelFit();
    this.cleanupPresence = installAvatarPresence({
      model: nextModel,
      element: this.canvas.parentElement || this.canvas,
    });
    this.cleanupRuntimeMotionLoop = installRuntimeMotionLoop(nextModel, () => ({
      profile: this.getModelProfile?.(),
      busy: this.avatarBusy,
    }));
    nextModel.on?.('hit', this.handleModelHit);
    applyAvatarAction(nextModel, this.initialAction());
    this.publishCapabilities();
    this.installResizeObserver();
  }

  publishCapabilities() {
    this.capabilities = collectModelCapabilities(this.model, this.getModelProfile?.());
    window.__AIRI_AVATAR_CAPABILITIES = this.capabilities;
    if (window.__AIRI_AVATAR_RUNTIME?.model === this.model) {
      window.__AIRI_AVATAR_RUNTIME.capabilities = this.capabilities;
    }
    window.dispatchEvent(new CustomEvent('avatar_model_capabilities', {
      detail: this.capabilities,
    }));
  }

  installResizeObserver() {
    this.resizeObserver?.disconnect();
    this.resizeObserver = new ResizeObserver(() => {
      window.requestAnimationFrame(() => this.updateModelFit());
    });
    if (this.canvas.parentElement) {
      this.resizeObserver.observe(this.canvas.parentElement);
    }
  }

  updateModelFit() {
    if (!this.model || !this.app) return;
    positionModel(this.app, this.model, this.getModelFit?.(), this.getModelProfile?.());
  }

  updateProfile() {
    const modelProfile = this.getModelProfile?.();
    window.__AIRI_AVATAR_CONFIG = {
      ...(window.__AIRI_AVATAR_CONFIG || {}),
      modelProfile,
    };
    window.dispatchEvent(new CustomEvent('avatar_model_profile', { detail: modelProfile }));
  }

  attachEvents() {
    if (this.eventsAttached) return;
    this.eventsAttached = true;
    window.addEventListener('ai_speak', this.handleSpeakEvent);
    window.addEventListener('ai_speech_cancel', this.handleSpeechCancel);
    window.addEventListener('avatar_action', this.handleAvatarAction);
    window.addEventListener('speech_status', this.handleSpeechStatus);
    this.canvas.addEventListener('pointerdown', this.handlePointerDown);
  }

  detachEvents() {
    if (!this.eventsAttached) return;
    this.eventsAttached = false;
    window.removeEventListener('ai_speak', this.handleSpeakEvent);
    window.removeEventListener('ai_speech_cancel', this.handleSpeechCancel);
    window.removeEventListener('avatar_action', this.handleAvatarAction);
    window.removeEventListener('speech_status', this.handleSpeechStatus);
    this.canvas.removeEventListener('pointerdown', this.handlePointerDown);
  }

  clearIdleSchedule() {
    window.clearTimeout(this.idleTimer);
    this.idleTimer = null;
  }

  clearIdleReset() {
    window.clearTimeout(this.idleResetTimer);
    this.idleResetTimer = null;
  }

  clearIdleTimers() {
    this.clearIdleSchedule();
    this.clearIdleReset();
  }

  scheduleIdleBehavior(delay = null) {
    const idle = this.behaviorProfile().idle || DEFAULT_BEHAVIOR_PROFILE.idle;
    const targetDelay = delay ?? randomDelay(idle, 'minDelay', 'maxDelay', 9000, 15000);
    this.clearIdleSchedule();
    this.idleTimer = window.setTimeout(() => {
      if (this.disposed || !this.model) return;

      if (this.avatarBusy || Date.now() < this.idleSuspendedUntil) {
        this.scheduleIdleBehavior(randomDelay(idle, 'retryMinDelay', 'retryMaxDelay', 4000, 8000));
        return;
      }

      const behaviors = idle.behaviors?.length ? idle.behaviors : DEFAULT_BEHAVIOR_PROFILE.idle.behaviors;
      const behavior = behaviors[Math.floor(Math.random() * behaviors.length)];
      this.avatarBusy = true;
      applyAvatarAction(this.model, behavior.action);
      dispatchSpeechStatus({ state: 'idle_behavior', message: behavior.message });
      this.clearIdleReset();
      this.idleResetTimer = window.setTimeout(() => {
        if (this.disposed || !this.model) return;
        this.avatarBusy = false;
        applyAvatarAction(this.model, this.resetAction());
        dispatchSpeechStatus(this.readyStatus());
      }, behavior.duration || 2400);
    }, targetDelay);
  }

  suspendIdle(duration = 5000) {
    const idle = this.behaviorProfile().idle || DEFAULT_BEHAVIOR_PROFILE.idle;
    this.idleSuspendedUntil = Date.now() + duration;
    this.clearIdleTimers();
    this.scheduleIdleBehavior(
      duration + randomDelay(idle, 'resumePaddingMin', 'resumePaddingMax', 3000, 6000),
    );
  }

  stopIdleMotions() {
    try {
      this.model?.internalModel?.motionManager?.stopAllMotions?.();
    } catch {
      // The motion manager API differs slightly across Live2D wrappers.
    }
  }

  runInteraction(interaction, interactionProfile) {
    if (!this.model || !interaction) return;
    this.avatarBusy = true;
    this.clearIdleTimers();
    applyAvatarAction(this.model, interaction.action);
    dispatchSpeechStatus({ state: 'interaction', message: interaction.message });
    window.clearTimeout(this.interactionTimer);
    this.interactionTimer = window.setTimeout(() => {
      this.avatarBusy = false;
      applyAvatarAction(this.model, this.resetAction());
      dispatchSpeechStatus(this.readyStatus());
    }, interaction.duration || interactionProfile.duration || 2200);
  }

  handleHitAreas(hitAreas = []) {
    if (!Array.isArray(hitAreas) || !hitAreas.length) return;
    const lower = hitAreas.map((area) => String(area).toLowerCase());
    const interactionProfile = this.behaviorProfile().interaction || DEFAULT_BEHAVIOR_PROFILE.interaction;
    const interaction = lower.some((area) => area.includes('head'))
      ? interactionProfile.head
      : lower.some((area) => area.includes('hand'))
        ? interactionProfile.hand
        : interactionProfile.body;
    this.runInteraction(interaction, interactionProfile);
  }

  handleInteraction(event) {
    if (!this.model) return;
    const rect = this.canvas.getBoundingClientRect();
    const yRatio = rect.height ? (event.clientY - rect.top) / rect.height : 0.5;
    const xRatio = rect.width ? (event.clientX - rect.left) / rect.width : 0.5;
    const interactionProfile = this.behaviorProfile().interaction || DEFAULT_BEHAVIOR_PROFILE.interaction;
    const isHeadArea = yRatio < (interactionProfile.headYMax ?? 0.44);
    const isHandArea = yRatio > (interactionProfile.handYMin ?? 0.58)
      && (xRatio < (interactionProfile.handEdge ?? 0.32) || xRatio > 1 - (interactionProfile.handEdge ?? 0.32));
    const interaction = isHeadArea
      ? interactionProfile.head
      : isHandArea
        ? interactionProfile.hand
        : interactionProfile.body;

    this.runInteraction(interaction, interactionProfile);
  }

  destroy() {
    this.disposed = true;
    this.detachEvents();
    window.clearTimeout(this.interactionTimer);
    this.clearIdleTimers();
    stopTextToSpeech(this.model, '数字人舞台已关闭');
    this.cleanupPresence?.();
    this.cleanupPresence = null;
    this.cleanupRuntimeMotionLoop?.();
    this.cleanupRuntimeMotionLoop = null;
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;

    if (this.model && this.app) {
      this.app.stage.removeChild(this.model);
      this.model.destroy();
      this.model = null;
    }

    if (this.app) {
      this.app.destroy(false, { children: true });
      this.app = null;
    }
  }
}

export function makeLive2DStageManager(options) {
  return new Live2DStageManager(options);
}
