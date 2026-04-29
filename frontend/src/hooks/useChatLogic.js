import { useRef, useState } from 'react';
import {
  actionForLlm,
  actionForQuestion,
  actionForSentence,
  actionForStatus,
  normalizeAvatarAction,
} from '../avatar/semanticActions';
import {
  createAiriSpecialTokenQueue,
  createAiriSpecialTokenStreamParser,
  stripAiriSpecialTokens,
} from '../airi/specialTokens';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const STREAM_SENTENCE_PATTERN = /^(.+?[。！？；.!?;])/;

function speechSentenceKey(text = '') {
  return stripAiriSpecialTokens(String(text))
    .replace(/\s+/g, '')
    .replace(/[，,。！？!?；;、：:]+$/g, '')
    .trim();
}

function parseSseBlocks(buffer) {
  const blocks = buffer.split('\n\n');
  return {
    complete: blocks.slice(0, -1),
    rest: blocks[blocks.length - 1],
  };
}

function parseSseBlock(block) {
  const lines = block.split('\n');
  let event = 'message';
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (!dataLines.length) {
    return { event, data: {} };
  }

  try {
    return { event, data: JSON.parse(dataLines.join('\n')) };
  } catch {
    return { event, data: { text: dataLines.join('\n') } };
  }
}

export function useChatLogic() {
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      content: '你好，我是 AIRI。你可以问我校园规章、办事流程，也可以和我聊聊你的偏好。',
      sources: [],
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState('准备就绪');
  const [lastRetrieval, setLastRetrieval] = useState(null);
  const [lastLlm, setLastLlm] = useState(null);
  const answerStartedRef = useRef(false);
  const sentenceIndexRef = useRef(0);
  const speechSentenceIndexRef = useRef(0);
  const speechTurnIdRef = useRef(0);
  const pendingSpeechBufferRef = useRef('');
  const spokenSentenceKeysRef = useRef(new Set());
  const speechSuppressedRef = useRef(false);
  const draftInterruptedRef = useRef(false);
  const lastAvatarActionAtRef = useRef(0);
  const specialTokenQueueRef = useRef(null);
  const specialTokenParserRef = useRef(null);

  const emitAvatarAction = (action, minGap = 300) => {
    const now = Date.now();
    if (minGap > 0 && now - lastAvatarActionAtRef.current < minGap) return;
    lastAvatarActionAtRef.current = now;
    window.dispatchEvent(new CustomEvent('avatar_action', {
      detail: normalizeAvatarAction(action),
    }));
  };

  const ensureSpecialTokenQueue = () => {
    if (!specialTokenQueueRef.current) {
      specialTokenQueueRef.current = createAiriSpecialTokenQueue({
        emitAction: (action) => emitAvatarAction(action, 0),
        emitStatus: (detail) => {
          window.dispatchEvent(new CustomEvent('avatar_special_token', { detail }));
        },
      });
    }
    return specialTokenQueueRef.current;
  };

  const updateLastAiMessage = (updater) => {
    setMessages((prev) => {
      const updated = [...prev];
      for (let index = updated.length - 1; index >= 0; index -= 1) {
        if (updated[index].role === 'ai') {
          updated[index] = typeof updater === 'function'
            ? updater(updated[index])
            : { ...updated[index], ...updater };
          return updated;
        }
      }
      return updated;
    });
  };

  const appendToLastAiMessage = (text) => {
    updateLastAiMessage((message) => ({
      ...message,
      content: message.content + text,
    }));
  };

  const handleCleanTokenText = (tokenText) => {
    if (!tokenText) return;
    appendToLastAiMessage(tokenText);
    if (!answerStartedRef.current) {
      answerStartedRef.current = true;
      emitAvatarAction({ expression: 'warm', motion: 'idle', style: 'speaking', reason: 'answer_started' }, 0);
    }
    if (!speechSuppressedRef.current) {
      pendingSpeechBufferRef.current += tokenText;
      flushSpeculativeSpeech(false);
    }
  };

  const resetSpecialTokenProcessing = () => {
    ensureSpecialTokenQueue().reset();
    specialTokenParserRef.current = createAiriSpecialTokenStreamParser({
      onText: handleCleanTokenText,
      onSpecial: (rawToken) => ensureSpecialTokenQueue().enqueue(rawToken),
    });
  };

  const processStreamTokenText = (tokenText) => {
    if (!specialTokenParserRef.current) {
      resetSpecialTokenProcessing();
    }
    specialTokenParserRef.current.write(tokenText);
  };

  const flushStreamTokenText = () => {
    specialTokenParserRef.current?.flush();
  };

  const interruptSpeechForDraft = () => {
    speechSuppressedRef.current = true;
    pendingSpeechBufferRef.current = '';
    window.dispatchEvent(new CustomEvent('ai_speech_cancel', {
      detail: { message: 'AIRI 正在听你说' },
    }));
    emitAvatarAction({ expression: 'thinking', motion: 'idle', style: 'listening', reason: 'user_typing_interrupt' }, 0);
    if (!isLoading) {
      setStatusText('正在听你说');
    }
  };

  const handleInputTextChange = (value) => {
    setInputText(value);
    if (!String(value || '').trim()) {
      draftInterruptedRef.current = false;
      if (!isLoading) {
        speechSuppressedRef.current = false;
      }
      return;
    }

    if (!draftInterruptedRef.current) {
      draftInterruptedRef.current = true;
      interruptSpeechForDraft();
    }
  };

  const toSpeakingAction = (action, fallback) => normalizeAvatarAction({
    ...normalizeAvatarAction(action, fallback),
    motion: 'idle',
    style: 'speaking',
    reason: `${action?.reason || fallback?.reason || 'sentence'}_speaking`,
  });

  const dispatchSpeech = (sentence, action, sentenceIndex, source = 'sentence', dedupeIndex = sentenceIndex) => {
    const text = String(sentence || '').trim();
    const key = speechSentenceKey(text);
    const indexedKey = `${dedupeIndex}:${key}`;
    if (!key || spokenSentenceKeysRef.current.has(indexedKey)) return false;

    spokenSentenceKeysRef.current.add(indexedKey);
    window.dispatchEvent(new CustomEvent('ai_speak', {
      detail: {
        text,
        action,
        turnId: speechTurnIdRef.current,
        sentenceIndex,
        source,
      },
    }));
    return true;
  };

  const removePendingSpeech = (sentence) => {
    const text = String(sentence || '').trim();
    const key = speechSentenceKey(text);
    if (!key || !pendingSpeechBufferRef.current.trim()) return;

    const pending = pendingSpeechBufferRef.current;
    const directIndex = pending.indexOf(text);
    if (directIndex >= 0) {
      pendingSpeechBufferRef.current = `${pending.slice(0, directIndex)}${pending.slice(directIndex + text.length)}`;
      return;
    }

    if (speechSentenceKey(pending) === key) {
      pendingSpeechBufferRef.current = '';
    }
  };

  const flushSpeculativeSpeech = (force = false) => {
    let buffer = pendingSpeechBufferRef.current;

    while (buffer.trim()) {
      const trimmed = buffer.trimStart();
      const leadingLength = buffer.length - trimmed.length;
      const match = STREAM_SENTENCE_PATTERN.exec(trimmed);
      if (!match) break;

      const sentence = match[1].trim();
      buffer = buffer.slice(leadingLength + match[1].length);
      if (!speechSentenceKey(sentence)) continue;

      const speechIndex = speechSentenceIndexRef.current;
      const action = toSpeakingAction(actionForSentence(sentence, speechIndex));
      if (dispatchSpeech(sentence, action, speechIndex, 'token', speechIndex)) {
        speechSentenceIndexRef.current += 1;
        emitAvatarAction(action, 550);
      }
    }

    if (force && buffer.trim()) {
      const sentence = buffer.trim();
      const speechIndex = speechSentenceIndexRef.current;
      const action = toSpeakingAction(actionForSentence(sentence, speechIndex));
      if (dispatchSpeech(sentence, action, speechIndex, 'token_final', speechIndex)) {
        speechSentenceIndexRef.current += 1;
        emitAvatarAction(action, 550);
      }
      buffer = '';
    }

    pendingSpeechBufferRef.current = buffer;
  };

  const handleStreamEvent = ({ event, data }) => {
    if (event === 'status') {
      setStatusText(data.text || data.state || '处理中');
      emitAvatarAction(actionForStatus(data.state), 250);
      return;
    }

    if (event === 'sources') {
      updateLastAiMessage({ sources: data.items || [] });
      return;
    }

    if (event === 'retrieval') {
      setLastRetrieval(data);
      updateLastAiMessage({ rag: data });
      return;
    }

    if (event === 'llm') {
      setLastLlm(data);
      updateLastAiMessage({ llm: data });
      const action = actionForLlm(data);
      if (action) emitAvatarAction(action, 250);
      return;
    }

    if (event === 'avatar') {
      emitAvatarAction(data, 0);
      return;
    }

    if (event === 'token') {
      const tokenText = data.text || '';
      processStreamTokenText(tokenText);
      return;
    }

    if (event === 'sentence') {
      const sentenceIndex = sentenceIndexRef.current;
      const cleanSentence = stripAiriSpecialTokens(data.text || '').trim();
      if (!cleanSentence) return;
      const fallbackAction = actionForSentence(cleanSentence, sentenceIndex);
      const action = normalizeAvatarAction(data.action, fallbackAction);
      const speechAction = toSpeakingAction(action, fallbackAction);
      sentenceIndexRef.current += 1;
      if (speechSuppressedRef.current) {
        removePendingSpeech(cleanSentence);
        return;
      }
      emitAvatarAction(speechAction, 550);
      removePendingSpeech(cleanSentence);
      if (dispatchSpeech(cleanSentence, speechAction, speechSentenceIndexRef.current, 'sentence', sentenceIndex)) {
        speechSentenceIndexRef.current += 1;
      }
      return;
    }

    if (event === 'error') {
      flushStreamTokenText();
      pendingSpeechBufferRef.current = '';
      speechSuppressedRef.current = false;
      updateLastAiMessage({ error: data.message || '未知错误' });
      appendToLastAiMessage(`\n（系统错误：${data.message || '未知错误'}）`);
      setStatusText('请求出错');
      emitAvatarAction({ expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'stream_error' }, 0);
      return;
    }

    if (event === 'done') {
      flushStreamTokenText();
      if (!speechSuppressedRef.current) {
        flushSpeculativeSpeech(true);
      }
      speechSuppressedRef.current = false;
      setStatusText('准备就绪');
      emitAvatarAction({ expression: 'warm', motion: 'idle', style: 'idle', reason: 'done' }, 0);
    }
  };

  const handleSendMessage = async () => {
    const messageText = inputText.trim();
    if (!messageText || isLoading) return;

    const historyToSend = messages
      .filter((msg) => msg.content.trim() !== '')
      .map((msg) => ({ role: msg.role, content: msg.content }));

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: messageText },
      { role: 'ai', content: '', sources: [], rag: null, llm: null, error: null },
    ]);
    setInputText('');
    setIsLoading(true);
    setLastRetrieval(null);
    setLastLlm(null);
    answerStartedRef.current = false;
    sentenceIndexRef.current = 0;
    speechSentenceIndexRef.current = 0;
    pendingSpeechBufferRef.current = '';
    spokenSentenceKeysRef.current = new Set();
    speechSuppressedRef.current = false;
    draftInterruptedRef.current = false;
    resetSpecialTokenProcessing();
    speechTurnIdRef.current += 1;
    setStatusText('正在连接后端');
    window.dispatchEvent(new CustomEvent('ai_speech_cancel', {
      detail: { message: '新问题已收到，旧语音已停止' },
    }));
    emitAvatarAction(actionForQuestion(messageText), 0);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_message: messageText,
          user_id: 'test_user',
          chat_history: historyToSend,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (!value) continue;

        buffer += decoder.decode(value, { stream: true });
        const { complete, rest } = parseSseBlocks(buffer);
        buffer = rest;
        complete.map(parseSseBlock).forEach(handleStreamEvent);
      }

      if (buffer.trim()) {
        handleStreamEvent(parseSseBlock(buffer));
      }
    } catch (error) {
      console.error('Chat request failed:', error);
      updateLastAiMessage({
        content: '（网络连接出错了，请确认后端服务已经启动。）',
        sources: [],
      });
      setLastRetrieval({ status: 'connection_error', source_count: 0, confidence: null });
      setLastLlm({ status: 'connection_error' });
      setStatusText('后端未连接');
      emitAvatarAction({ expression: 'apologetic', motion: 'nod', style: 'soft', reason: 'network_error' }, 0);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    inputText,
    setInputText,
    handleInputTextChange,
    messages,
    isLoading,
    statusText,
    lastRetrieval,
    lastLlm,
    handleSendMessage,
  };
}
