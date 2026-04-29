export const DEFAULT_BEHAVIOR_PROFILE = {
  name: 'balanced',
  readyStatus: { state: 'ready', message: '数字人待命' },
  initialAction: { expression: 'neutral', motion: 'idle', style: 'idle', reason: 'model_ready' },
  resetAction: { expression: 'neutral', motion: 'idle', style: 'idle', reason: 'model_reset' },
  idle: {
    minDelay: 9000,
    maxDelay: 15000,
    retryMinDelay: 4000,
    retryMaxDelay: 8000,
    resumePaddingMin: 3000,
    resumePaddingMax: 6000,
    behaviors: [
      {
        action: { expression: 'neutral', motion: 'nod', style: 'idle', reason: 'idle_nod' },
        message: 'AIRI 正在等你提问',
        duration: 2200,
      },
      {
        action: { expression: 'thinking', motion: 'idle', style: 'idle', reason: 'idle_thinking' },
        message: 'AIRI 在整理思路',
        duration: 2600,
      },
      {
        action: { expression: 'warm', motion: 'encourage', style: 'idle', reason: 'idle_greeting' },
        message: 'AIRI 轻轻向你打招呼',
        duration: 2400,
      },
      {
        action: { expression: 'warm', motion: 'emphasize', style: 'idle', reason: 'idle_ready' },
        message: 'AIRI 已准备好继续回答',
        duration: 2400,
      },
    ],
  },
  interaction: {
    duration: 2200,
    headYMax: 0.44,
    handYMin: 0.58,
    handEdge: 0.32,
    head: {
      action: { expression: 'blink', motion: 'nod', style: 'interaction', reason: 'tap_head' },
      message: 'AIRI 眨了眨眼',
    },
    hand: {
      action: { expression: 'surprised', motion: 'magic', style: 'interaction', reason: 'tap_hand' },
      message: 'AIRI 轻轻挥了挥手',
    },
    body: {
      action: { expression: 'encouraging', motion: 'emphasize', style: 'interaction', reason: 'tap_body' },
      message: 'AIRI 正在回应你的互动',
    },
  },
  speech: {
    action: { expression: 'warm', motion: 'idle', style: 'speaking', reason: 'speech_playing' },
    keepMotionSilent: true,
    segment: {
      minimumWords: 4,
      maximumWords: 18,
      maximumChars: 220,
      singleChunkChars: 120,
      singleChunkWords: 28,
      boost: 2,
    },
  },
};

export const MODEL_BEHAVIOR_PROFILES = {
  '/Epsilon/runtime/Epsilon.model3.json': {
    name: 'epsilon-expressive',
    idle: {
      behaviors: [
        {
          action: { expression: 'warm', motion: 'nod', style: 'idle', reason: 'epsilon_idle_nod' },
          message: 'Epsilon 正在看向你',
          duration: 2200,
        },
        {
          action: { expression: 'happy', motion: 'encourage', style: 'idle', reason: 'epsilon_idle_wave' },
          message: 'Epsilon 轻轻挥了挥手',
          duration: 2400,
        },
        {
          action: { expression: 'thinking', motion: 'idle', style: 'idle', reason: 'epsilon_idle_think' },
          message: 'Epsilon 正在等待新的问题',
          duration: 2600,
        },
      ],
    },
  },
  '/izumi/runtime/izumi_illust.model3.json': {
    name: 'izumi-soft',
    idle: {
      behaviors: [
        {
          action: { expression: 'warm', motion: 'idle', style: 'idle', reason: 'izumi_idle_soft' },
          message: 'Izumi 安静地等你开口',
          duration: 2400,
        },
        {
          action: { expression: 'thinking', motion: 'nod', style: 'idle', reason: 'izumi_idle_focus' },
          message: 'Izumi 正在留意你的问题',
          duration: 2400,
        },
      ],
    },
  },
  '/live2d/hiyori/Hiyori.model3.json': {
    name: 'hiyori-gentle',
    interaction: {
      duration: 2100,
      handYMin: 0.62,
    },
    speech: {
      segment: {
        maximumWords: 16,
        maximumChars: 200,
        singleChunkChars: 120,
      },
    },
  },
  '/live2d/natori/Natori.model3.json': {
    name: 'natori-bright',
    idle: {
      behaviors: [
        {
          action: { expression: 'warm', motion: 'nod', style: 'idle', reason: 'natori_idle_nod' },
          message: 'Natori 正在等你提问',
          duration: 2200,
        },
        {
          action: { expression: 'happy', motion: 'encourage', style: 'idle', reason: 'natori_idle_wave' },
          message: 'Natori 轻轻回应了一下',
          duration: 2300,
        },
      ],
    },
  },
  '/mao_pro_zh/runtime/mao_pro.model3.json': {
    name: 'mao-pro-rich-mouth',
    interaction: {
      duration: 2400,
    },
    speech: {
      segment: {
        maximumWords: 20,
        maximumChars: 240,
        singleChunkChars: 140,
      },
    },
  },
  '/shizuku/runtime/shizuku.model3.json': {
    name: 'shizuku-calm',
    idle: {
      behaviors: [
        {
          action: { expression: 'neutral', motion: 'idle', style: 'idle', reason: 'shizuku_idle_still' },
          message: 'Shizuku 正在安静待机',
          duration: 2600,
        },
        {
          action: { expression: 'warm', motion: 'encourage', style: 'idle', reason: 'shizuku_idle_greet' },
          message: 'Shizuku 轻轻看向你',
          duration: 2300,
        },
      ],
    },
  },
  '/tororo_hijiki/hijiki/runtime/hijiki.model3.json': {
    name: 'hijiki-cat',
    interaction: {
      head: {
        action: { expression: 'happy', motion: 'nod', style: 'interaction', reason: 'hijiki_tap_head' },
        message: 'Hijiki 轻轻晃了晃',
      },
    },
  },
  '/tororo_hijiki/tororo/runtime/tororo.model3.json': {
    name: 'tororo-cat',
    interaction: {
      head: {
        action: { expression: 'happy', motion: 'nod', style: 'interaction', reason: 'tororo_tap_head' },
        message: 'Tororo 轻轻晃了晃',
      },
    },
  },
};

function mergeObject(base, patch) {
  const output = { ...(base || {}) };
  for (const [key, value] of Object.entries(patch || {})) {
    if (Array.isArray(value)) {
      output[key] = [...value];
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      output[key] = mergeObject(output[key], value);
    } else if (value !== undefined) {
      output[key] = value;
    }
  }
  return output;
}

export function normalizeBehaviorProfile(...profiles) {
  return profiles.reduce((merged, profile) => mergeObject(merged, profile), DEFAULT_BEHAVIOR_PROFILE);
}

export function behaviorProfileForModel(model = {}) {
  return normalizeBehaviorProfile(
    MODEL_BEHAVIOR_PROFILES[model.url],
    model.behavior,
  );
}
