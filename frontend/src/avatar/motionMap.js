export const avatarCapabilities = {
  expressions: {
    neutral: ['Normal', 'Normal.exp3.json', 'exp_01', 'f01.exp3.json'],
    warm: ['Smile', 'Smile.exp3.json', 'exp_01', 'f01.exp3.json'],
    blink: ['Normal', 'Normal.exp3.json', 'exp_02', 'f02.exp3.json'],
    happy: ['Smile', 'Smile.exp3.json', 'exp_04', 'f01.exp3.json'],
    thinking: ['Normal', 'Normal.exp3.json', 'exp_04', 'f02.exp3.json'],
    serious: ['Angry', 'Angry.exp3.json', 'exp_05'],
    surprised: ['Surprised', 'Surprised.exp3.json', 'exp_06'],
    apologetic: ['Sad', 'Sad.exp3.json', 'exp_07'],
    encouraging: ['Smile', 'Smile.exp3.json', 'exp_08', 'f01.exp3.json'],
  },
  motions: {
    idle: [['Idle', 0]],
    explain: [['TapBody', 0], ['Tap', 0], ['', 0], ['FlickRight', 0], ['Idle', 1]],
    nod: [['TapBody', 1], ['Tap', 1], ['', 1], ['FlickDown', 0], ['FlickUp', 0], ['Idle', 0]],
    emphasize: [['TapBody', 2], ['Tap', 2], ['', 2], ['Flick3', 0], ['FlickRight', 1], ['Idle', 2]],
    magic: [['TapBody', 3], ['Shake', 0], ['', 3], ['Flick3', 1], ['Idle', 0]],
    encourage: [['TapBody', 4], ['Tap', 1], ['', 4], ['Flick', 0], ['Idle', 1]],
    celebrate: [['TapBody', 5], ['Shake', 1], ['', 5], ['Flick', 1], ['Idle', 2]],
  },
  lipSyncParams: ['ParamMouthOpenY', 'ParamMouthForm', 'ParamMouthForm2', 'ParamA', 'ParamI', 'ParamU', 'ParamE', 'ParamO'],
};

function currentAvatarProfile(profile) {
  return profile || window.__AIRI_AVATAR_CONFIG?.modelProfile || {};
}

function expressionExists(name, available = []) {
  if (!available?.length) return true;
  const normalized = String(name || '').toLowerCase().replace(/\.exp3\.json$/, '');
  return available.some((item) => {
    const value = String(item || '').toLowerCase();
    return value === String(name || '').toLowerCase() || value.replace(/\.exp3\.json$/, '') === normalized;
  });
}

function motionCountForGroup(group, motionGroups = {}) {
  if (!motionGroups || typeof motionGroups !== 'object') return 0;
  if (Object.prototype.hasOwnProperty.call(motionGroups, group)) {
    return Number(motionGroups[group]) || 0;
  }
  const match = Object.entries(motionGroups).find(([key]) => key.toLowerCase() === String(group).toLowerCase());
  return Number(match?.[1]) || 0;
}

export function resolveExpression(expression, profile) {
  const modelProfile = currentAvatarProfile(profile);
  const expressionAliases = {
    ...(modelProfile.behavior?.expressionAliases || {}),
    ...(modelProfile.expressionAliases || {}),
  };
  const candidates = expressionAliases[expression] || avatarCapabilities.expressions[expression] || avatarCapabilities.expressions.warm;
  return candidates.filter((name) => expressionExists(name, modelProfile.expressions));
}

export function resolveMotion(motion, profile) {
  const modelProfile = currentAvatarProfile(profile);
  const aliases = {
    ...(modelProfile.behavior?.motionAliases || {}),
    ...(modelProfile.motionAliases || {}),
  };
  const directCandidates = Array.isArray(motion)
    ? (Array.isArray(motion[0]) ? motion : [motion])
    : motion && typeof motion === 'object' && motion.group
      ? [[motion.group, motion.index ?? 0]]
      : null;
  const candidates = directCandidates || aliases[motion] || avatarCapabilities.motions[motion] || avatarCapabilities.motions.explain;
  const motionGroups = modelProfile.motion_groups || {};
  const resolved = [];

  for (const [group, index = 0] of candidates) {
    const count = motionCountForGroup(group, motionGroups);
    if (!Object.keys(motionGroups).length || count > 0) {
      resolved.push([group, count > 0 ? Math.min(index, count - 1) : index]);
    }
  }

  if (resolved.length) return resolved;
  return [['Idle', 0]];
}
