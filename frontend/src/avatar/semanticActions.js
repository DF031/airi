import { avatarCapabilities } from './motionMap';

const DEFAULT_ACTION = { expression: 'warm', motion: 'idle', style: 'normal', reason: 'default' };
const STATUS_ACTIONS = {
  memory: { expression: 'thinking', motion: 'idle', style: 'thinking', reason: 'memory' },
  retrieving: { expression: 'thinking', motion: 'magic', style: 'thinking', reason: 'retrieving' },
  index_loading: { expression: 'thinking', motion: 'magic', style: 'thinking', reason: 'index_loading' },
  retrieval_timeout: { expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'retrieval_timeout' },
  retrieval_error: { expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'retrieval_error' },
  rate_limited: { expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'rate_limited' },
  llm_fallback: { expression: 'serious', motion: 'explain', style: 'serious', reason: 'fallback' },
  generating: { expression: 'warm', motion: 'explain', style: 'normal', reason: 'generating' },
};

const expressionNames = new Set(Object.keys(avatarCapabilities.expressions));
const motionNames = new Set(Object.keys(avatarCapabilities.motions));

function hasAny(text, terms) {
  return terms.some((term) => text.includes(term));
}

function stripText(value = '') {
  return String(value)
    .replace(/[#*_`>[\]()]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function normalizeAvatarAction(action, fallback = DEFAULT_ACTION) {
  const safeFallback = fallback || DEFAULT_ACTION;
  if (!action || typeof action !== 'object') return { ...safeFallback };

  const expression = expressionNames.has(action.expression) ? action.expression : safeFallback.expression;
  const motion = motionNames.has(action.motion) ? action.motion : safeFallback.motion;
  return {
    ...safeFallback,
    ...action,
    expression,
    motion,
    style: action.style || safeFallback.style || 'normal',
    reason: action.reason || safeFallback.reason || 'semantic',
  };
}

export function actionForStatus(state) {
  return normalizeAvatarAction(STATUS_ACTIONS[state] || DEFAULT_ACTION);
}

export function actionForQuestion(question = '') {
  const text = stripText(question);
  if (!text) return normalizeAvatarAction({ expression: 'thinking', motion: 'idle', reason: 'empty_question' });

  if (hasAny(text, ['你好', '您好', '早上好', '晚上好'])) {
    return normalizeAvatarAction({ expression: 'happy', motion: 'nod', style: 'bright', reason: 'greeting' });
  }
  if (hasAny(text, ['谢谢', '感谢', '辛苦'])) {
    return normalizeAvatarAction({ expression: 'happy', motion: 'encourage', style: 'bright', reason: 'thanks' });
  }
  if (hasAny(text, ['后果', '处分', '处罚', '严禁', '不得', '违规', '弄虚作假'])) {
    return normalizeAvatarAction({ expression: 'serious', motion: 'emphasize', style: 'serious', reason: 'risk_question' });
  }
  if (hasAny(text, ['怎么办', '如何', '怎么', '流程', '办理', '申请', '认定', '转换', '查询'])) {
    return normalizeAvatarAction({ expression: 'thinking', motion: 'magic', style: 'thinking', reason: 'procedure_question' });
  }
  return normalizeAvatarAction({ expression: 'thinking', motion: 'idle', style: 'thinking', reason: 'question_received' });
}

export function actionForLlm(llm = {}) {
  if (llm.status === 'rate_limited') {
    return normalizeAvatarAction({ expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'llm_rate_limited' });
  }
  if (llm.status === 'fallback') {
    return normalizeAvatarAction({ expression: 'serious', motion: 'explain', style: 'serious', reason: 'llm_fallback' });
  }
  if (llm.status === 'recovered') {
    return normalizeAvatarAction({ expression: 'happy', motion: 'nod', style: 'bright', reason: 'llm_recovered' });
  }
  if (llm.status === 'connection_error') {
    return normalizeAvatarAction({ expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'llm_connection_error' });
  }
  return null;
}

export function actionForSentence(sentence = '', index = 0) {
  const text = stripText(sentence);
  if (!text) return normalizeAvatarAction(DEFAULT_ACTION);

  if (hasAny(text, ['抱歉', '无法', '不能确定', '没有找到', '未检索到', '暂时不能'])) {
    return normalizeAvatarAction({ expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'uncertain_sentence' });
  }
  if (hasAny(text, ['注意', '必须', '严禁', '不得', '禁止', '后果', '处分', '取消资格', '责任', '影响'])) {
    return normalizeAvatarAction({ expression: 'serious', motion: 'emphasize', style: 'serious', reason: 'important_notice' });
  }
  if (hasAny(text, ['首先', '其次', '最后', '第一', '第二', '第三', '步骤', '流程', '办理', '申请', '提交', '审核'])) {
    return normalizeAvatarAction({ expression: 'warm', motion: 'explain', style: 'normal', reason: 'procedure_sentence' });
  }
  if (hasAny(text, ['根据', '依据', '规定', '办法', '通知', '文件', '来源', '材料'])) {
    return normalizeAvatarAction({ expression: 'serious', motion: 'explain', style: 'serious', reason: 'source_sentence' });
  }
  if (hasAny(text, ['地点', '地址', '电话', '邮箱', '网站', '系统', '平台', '办公室', '部门'])) {
    return normalizeAvatarAction({ expression: 'warm', motion: 'nod', style: 'normal', reason: 'service_info' });
  }
  if (hasAny(text, ['可以', '建议', '符合', '完成', '通过', '成功', '优秀', '恭喜'])) {
    return normalizeAvatarAction({ expression: 'encouraging', motion: 'encourage', style: 'bright', reason: 'positive_sentence' });
  }
  if (hasAny(text, ['如果', '需要的话', '还可以', '我可以继续'])) {
    return normalizeAvatarAction({ expression: 'encouraging', motion: 'nod', style: 'normal', reason: 'follow_up' });
  }

  const rhythm = [
    { expression: 'warm', motion: 'explain', style: 'normal', reason: 'answer_rhythm_explain' },
    { expression: 'warm', motion: 'nod', style: 'normal', reason: 'answer_rhythm_confirm' },
    { expression: 'encouraging', motion: 'emphasize', style: 'normal', reason: 'answer_rhythm_emphasize' },
  ];
  return normalizeAvatarAction(rhythm[index % rhythm.length]);
}
