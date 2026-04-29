import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Database,
  FileText,
  Headphones,
  Play,
  RotateCcw,
  Send,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Volume2,
} from 'lucide-react';
import AvatarDebugPanel from './components/AvatarDebugPanel';
import LevelMeter from './components/LevelMeter';
import Live2DViewer from './Live2DViewer';
import {
  DEFAULT_AVATAR_DEBUG_CONFIG,
  actionForEmotion,
  readAvatarDebugConfig,
  writeAvatarDebugConfig,
} from './avatar/emotionSystem';
import { useChatLogic } from './hooks/useChatLogic';
import { useAvatarTelemetry } from './hooks/useAvatarTelemetry';
import {
  DEFAULT_MODEL_URL,
  FALLBACK_MODELS,
  defaultFitForModel,
  fitStorageKey,
  mergeAvatarModels,
  normalizeAvatarFit,
  profileForModel,
  readAvatarFit,
} from './avatar/modelRegistry';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const DEFAULT_TTS_VOICE = 'zh-CN-XiaoxiaoNeural';
const DEFAULT_TTS_RATE = '+8%';
const FALLBACK_TTS_VOICES = [
  { id: DEFAULT_TTS_VOICE, name: '晓晓', gender: 'Female', style: '清亮自然' },
  { id: 'zh-CN-XiaoyiNeural', name: '晓伊', gender: 'Female', style: '温柔' },
  { id: 'zh-CN-YunxiNeural', name: '云希', gender: 'Male', style: '年轻自然' },
];
const TTS_RATE_OPTIONS = [
  { value: '-10%', label: '慢速' },
  { value: '+0%', label: '标准' },
  { value: '+8%', label: '自然偏快' },
  { value: '+15%', label: '演示快语速' },
];
function sourceName(source = '') {
  const parts = String(source).split(/[\\/]/).filter(Boolean);
  return parts.at(-1) || '校园知识库';
}

function retrievalLabel(status) {
  if (status === 'connection_error') return '连接异常';
  if (status === 'answered' || status === 'retrieved' || status === 'insufficient_evidence') return '已检索';
  if (status === 'empty') return '无来源';
  return '待检索';
}

function llmLabel(status) {
  if (status === 'rate_limited') return 'GLM 限流重试';
  if (status === 'recovered') return 'GLM 已恢复';
  if (status === 'fallback') return 'v4 兜底回复';
  if (status === 'connection_error') return '连接异常';
  return '';
}

function chatModelLabel(systemStatus) {
  const model = systemStatus?.chat_model || '';
  const provider = systemStatus?.chat_provider || '';
  return provider && model ? `${provider} / ${model}` : model;
}

function speechLabel(status = {}) {
  if (status.state === 'loading') return status.message || '语音生成中';
  if (status.state === 'queued') return status.message || `语音排队 ${status.queueSize || 1}`;
  if (status.state === 'playing') return status.message || '语音播放中';
  if (status.state === 'interaction') return status.message || '互动回应中';
  if (status.state === 'idle_behavior') return status.message || 'AIRI 正在待机';
  if (status.state === 'ready') return status.message || '数字人待命';
  if (status.state === 'error') return status.message || '语音异常';
  if (status.state === 'unavailable') return status.message || '语音未就绪';
  return '数字人待命';
}

function compactPath(value = '') {
  const parts = String(value).split(/[\\/]/).filter(Boolean);
  if (parts.length <= 2) return String(value || '未配置');
  return `${parts.at(-2)}/${parts.at(-1)}`;
}

function SourceList({ sources = [] }) {
  const [expanded, setExpanded] = useState(false);
  if (!sources.length) return null;

  const visibleSources = expanded ? sources : sources.slice(0, 2);

  return (
    <div style={{ marginTop: '12px', display: 'grid', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '12px', color: 'rgba(255,255,255,0.62)' }}>
          <FileText size={14} />
          知识来源
        </div>
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.42)' }}>{sources.length} 条</span>
      </div>
      {visibleSources.map((item, index) => (
        <div
          key={`${item.source || 'source'}-${index}`}
          className="liquid-glass"
          style={{ padding: '10px 12px', maxWidth: '520px' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', marginBottom: '5px' }}>
            <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.82)' }}>
              {sourceName(item.source)}
            </span>
            <span style={{ flex: '0 0 auto', fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
              {item.retriever || 'source'}
            </span>
          </div>
          <div style={{ fontSize: '12px', lineHeight: 1.5, color: 'rgba(255,255,255,0.58)' }}>
            {item.preview}
          </div>
        </div>
      ))}
      {sources.length > 2 && (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          style={{
            justifySelf: 'start',
            padding: '4px 0',
            color: 'rgba(255,255,255,0.68)',
            background: 'transparent',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          {expanded ? '收起来源' : `展开其余 ${sources.length - 2} 条来源`}
        </button>
      )}
    </div>
  );
}

function AnswerMeta({ llm, error }) {
  if (!llm && !error) return null;

  const llmText = llmLabel(llm?.status);

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', margin: '8px 0 4px 26px' }}>
      {llmText && (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 8px',
          borderRadius: '8px',
          color: llm?.status === 'rate_limited' ? '#ffd080' : 'rgba(255,255,255,0.72)',
          background: llm?.status === 'rate_limited' ? 'rgba(255,208,128,0.12)' : 'rgba(255,255,255,0.06)',
          fontSize: '12px',
        }}>
          <ShieldCheck size={13} />
          {llmText}
          {llm?.retry_in_sec ? ` · ${llm.retry_in_sec}s` : ''}
        </span>
      )}
      {error && (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 8px',
          borderRadius: '8px',
          color: '#ff9b9b',
          background: 'rgba(255,120,120,0.12)',
          fontSize: '12px',
        }}>
          <AlertCircle size={13} />
          {error}
        </span>
      )}
    </div>
  );
}

function SpeechStatus({ status }) {
  const isActive = ['loading', 'queued', 'playing', 'interaction', 'idle_behavior'].includes(status?.state);
  const isError = status?.state === 'error' || status?.state === 'unavailable';

  return (
    <div
      className="liquid-glass"
      style={{
        marginTop: 0,
        padding: '9px 11px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        width: 'fit-content',
        color: isError ? '#ffb0b0' : isActive ? '#7cf3bd' : 'rgba(255,255,255,0.62)',
        fontSize: '12px',
      }}
    >
      <Headphones size={14} />
      {speechLabel(status)}
    </div>
  );
}

function StatusChip({ icon, label, value }) {
  return (
    <div className="liquid-glass" style={{ padding: '10px 12px', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
        {icon}
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.48)' }}>{label}</span>
      </div>
      <div style={{
        fontSize: '13px',
        color: 'rgba(255,255,255,0.86)',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}>
        {value || '未知'}
      </div>
    </div>
  );
}

function ControlSelect({ label, value, onChange, children }) {
  return (
    <label style={{ display: 'grid', gap: '6px', minWidth: 0 }}>
      <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="liquid-glass"
        style={{
          minWidth: 0,
          width: '100%',
          padding: '10px 12px',
          color: 'rgba(255,255,255,0.9)',
          backgroundColor: 'rgba(20,26,35,0.82)',
          outline: 'none',
          cursor: 'pointer',
        }}
      >
        {children}
      </select>
    </label>
  );
}

function RangeControl({ label, value, min, max, step, onChange, displayValue }) {
  return (
    <label style={{ display: 'grid', gap: '6px', minWidth: 0 }}>
      <span style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>{label}</span>
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.74)' }}>{displayValue ?? value}</span>
      </span>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{ width: '100%', accentColor: '#7cf3bd' }}
      />
    </label>
  );
}

function voiceLabel(voice = {}) {
  const parts = [voice.name || voice.id, voice.gender === 'Male' ? '男声' : voice.gender === 'Female' ? '女声' : '', voice.style || '']
    .filter(Boolean);
  return parts.join(' · ');
}

function SystemPanel({
  systemStatus,
  systemError,
  lastRetrieval,
  lastLlm,
  avatarModels,
  selectedModelUrl,
  onModelChange,
  ttsVoices,
  selectedVoice,
  onVoiceChange,
  selectedRate,
  onRateChange,
  avatarFit,
  onAvatarFitChange,
  onAvatarFitReset,
  onPreviewVoice,
}) {
  const [expanded, setExpanded] = useState(false);
  const rag = systemStatus?.rag;
  const tts = systemStatus?.tts;
  const corpus = rag?.corpus;
  const llmStatus = llmLabel(lastLlm?.status);
  const ragName = rag?.retriever?.engine || rag?.strategy || 'RAG';
  const ragState = rag?.retriever?.loading ? '索引加载中' : rag?.retriever?.loaded ? '索引已就绪' : ragName;
  const corpusText = corpus?.exists ? `${corpus.file_count} 文件` : '知识库待确认';
  const selectedModel = avatarModels.find((item) => item.url === selectedModelUrl);
  const selectedVoiceItem = ttsVoices.find((item) => item.id === selectedVoice);

  return (
    <div className="liquid-glass-strong" style={{ padding: expanded ? '14px' : 0, display: 'grid', gap: '10px' }}>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        style={{
          width: '100%',
          padding: expanded ? '0 0 2px' : '12px 14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
          color: 'white',
          background: 'transparent',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <span style={{
            width: '8px',
            height: '8px',
            flex: '0 0 auto',
            borderRadius: '50%',
            background: systemError ? '#ff7878' : '#7cf3bd',
            boxShadow: systemError ? '0 0 16px rgba(255,120,120,0.8)' : '0 0 16px rgba(124,243,189,0.8)',
          }} />
          <span style={{
            fontSize: '13px',
            color: 'rgba(255,255,255,0.86)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {systemError ? '后端未连接' : '后端已连接'} · {ragState} · {corpusText}
          </span>
        </span>
        {expanded ? (
          <ChevronUp size={17} color="rgba(255,255,255,0.68)" />
        ) : (
          <ChevronDown size={17} color="rgba(255,255,255,0.68)" />
        )}
      </button>

      {expanded && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
            <StatusChip
              icon={<Sparkles size={15} color="rgba(255,255,255,0.65)" />}
              label="大模型"
              value={chatModelLabel(systemStatus)}
            />
            <StatusChip
              icon={<Database size={15} color="rgba(255,255,255,0.65)" />}
              label="RAG"
              value={ragState}
            />
            <StatusChip
              icon={<BookOpen size={15} color="rgba(255,255,255,0.65)" />}
              label="知识库"
              value={corpus?.exists ? `${corpus.file_count} 文件 / ${corpus.size_mb} MB` : compactPath(rag?.knowledge_dir)}
            />
            <StatusChip
              icon={<Volume2 size={15} color="rgba(255,255,255,0.65)" />}
              label="语音"
              value={`${tts?.engine || 'TTS'} / ${voiceLabel(selectedVoiceItem) || tts?.voice || '默认音色'}`}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
            <ControlSelect label="数字人模型" value={selectedModelUrl} onChange={onModelChange}>
              {avatarModels.map((item) => (
                <option key={item.url} value={item.url}>
                  {item.name} {item.lip_sync_params?.length ? `· 口型 ${item.lip_sync_params.length}` : ''}
                </option>
              ))}
            </ControlSelect>
            <ControlSelect label="TTS 音色" value={selectedVoice} onChange={onVoiceChange}>
              {ttsVoices.map((item) => (
                <option key={item.id} value={item.id}>
                  {voiceLabel(item)}
                </option>
              ))}
            </ControlSelect>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '10px', alignItems: 'end' }}>
            <ControlSelect label="TTS 语速" value={selectedRate} onChange={onRateChange}>
              {TTS_RATE_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </ControlSelect>
            <button
              type="button"
              className="liquid-glass hover-scale active-scale"
              onClick={onPreviewVoice}
              style={{
                height: '40px',
                minWidth: '86px',
                padding: '0 14px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '7px',
                color: 'rgba(255,255,255,0.86)',
                cursor: 'pointer',
                fontSize: '12px',
              }}
            >
              <Play size={14} />
              试听
            </button>
          </div>

          <div className="liquid-glass" style={{ padding: '12px', display: 'grid', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <SlidersHorizontal size={15} color="rgba(255,255,255,0.66)" />
                <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.62)' }}>数字人校准</span>
              </div>
              <button
                type="button"
                onClick={onAvatarFitReset}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 8px',
                  color: 'rgba(255,255,255,0.64)',
                  background: 'rgba(255,255,255,0.05)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '11px',
                }}
              >
                <RotateCcw size={12} />
                重置
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px 14px' }}>
              <RangeControl
                label="显示大小"
                value={avatarFit.scale}
                min={0.65}
                max={1.45}
                step={0.01}
                onChange={(value) => onAvatarFitChange({ scale: value })}
                displayValue={`${Math.round(avatarFit.scale * 100)}%`}
              />
              <RangeControl
                label="口型强度"
                value={avatarFit.mouthGain}
                min={0.55}
                max={1.7}
                step={0.01}
                onChange={(value) => onAvatarFitChange({ mouthGain: value })}
                displayValue={`${Math.round(avatarFit.mouthGain * 100)}%`}
              />
              <RangeControl
                label="横向位置"
                value={avatarFit.offsetX}
                min={-220}
                max={220}
                step={1}
                onChange={(value) => onAvatarFitChange({ offsetX: value })}
                displayValue={`${Math.round(avatarFit.offsetX)}px`}
              />
              <RangeControl
                label="纵向位置"
                value={avatarFit.offsetY}
                min={-220}
                max={220}
                step={1}
                onChange={(value) => onAvatarFitChange({ offsetY: value })}
                displayValue={`${Math.round(avatarFit.offsetY)}px`}
              />
            </div>
          </div>

          <div className="liquid-glass" style={{ padding: '11px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={15} color="rgba(255,255,255,0.66)" />
                <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.58)' }}>最近检索</span>
              </div>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.72)' }}>
                {lastRetrieval ? retrievalLabel(lastRetrieval.status) : '暂无'}
              </span>
            </div>
            <div style={{ marginTop: '6px', fontSize: '12px', lineHeight: 1.5, color: 'rgba(255,255,255,0.62)' }}>
              来源 {lastRetrieval?.source_count ?? 0} 条
              {llmStatus && (
                <>
                  <span style={{ margin: '0 8px', color: 'rgba(255,255,255,0.28)' }}>/</span>
                  生成 {llmStatus}
                </>
              )}
              {selectedModel && (
                <>
                  <span style={{ margin: '0 8px', color: 'rgba(255,255,255,0.28)' }}>/</span>
                  模型 {selectedModel.name}
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function App() {
  const {
    inputText,
    handleInputTextChange,
    messages,
    isLoading,
    statusText,
    lastRetrieval,
    lastLlm,
    handleSendMessage,
  } = useChatLogic();
  const [systemStatus, setSystemStatus] = useState(null);
  const [systemError, setSystemError] = useState('');
  const [speechStatus, setSpeechStatus] = useState({ state: 'idle', queueSize: 0 });
  const avatarTelemetry = useAvatarTelemetry();
  const [avatarDebugOpen, setAvatarDebugOpen] = useState(false);
  const [avatarDebugConfig, setAvatarDebugConfig] = useState(() => readAvatarDebugConfig());
  const [avatarModels, setAvatarModels] = useState(() => mergeAvatarModels(FALLBACK_MODELS));
  const [selectedModelUrl, setSelectedModelUrl] = useState(
    () => window.localStorage.getItem('airi.avatar.model') || DEFAULT_MODEL_URL,
  );
  const [ttsVoices, setTtsVoices] = useState(FALLBACK_TTS_VOICES);
  const [selectedVoice, setSelectedVoice] = useState(
    () => window.localStorage.getItem('airi.tts.voice') || DEFAULT_TTS_VOICE,
  );
  const [selectedRate, setSelectedRate] = useState(
    () => window.localStorage.getItem('airi.tts.rate') || DEFAULT_TTS_RATE,
  );
  const [avatarFit, setAvatarFit] = useState(() => readAvatarFit(
    window.localStorage.getItem('airi.avatar.model') || DEFAULT_MODEL_URL,
  ));
  const chatEndRef = useRef(null);
  const selectedModel = useMemo(
    () => profileForModel(avatarModels.find((item) => item.url === selectedModelUrl) || { url: selectedModelUrl }),
    [avatarModels, selectedModelUrl],
  );

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const handleSpeechStatus = (event) => {
      setSpeechStatus(event.detail || { state: 'idle', queueSize: 0 });
    };

    window.addEventListener('speech_status', handleSpeechStatus);
    return () => window.removeEventListener('speech_status', handleSpeechStatus);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/system/status`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!cancelled) {
          setSystemStatus(data);
          setSystemError('');
        }
      } catch (error) {
        if (!cancelled) {
          setSystemError(error.message || 'status_error');
        }
      }
    };

    loadStatus();
    const timer = window.setInterval(loadStatus, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadAvatarModels = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/avatar/models`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const models = mergeAvatarModels(Array.isArray(data.models) && data.models.length ? data.models : FALLBACK_MODELS);
        if (cancelled) return;
        setAvatarModels(models);
        setSelectedModelUrl((current) => {
          const saved = window.localStorage.getItem('airi.avatar.model');
          const preferred = saved || current || data.default_url || DEFAULT_MODEL_URL;
          if (models.some((item) => item.url === preferred)) return preferred;
          if (models.some((item) => item.url === data.default_url)) return data.default_url;
          return models[0]?.url || DEFAULT_MODEL_URL;
        });
      } catch (error) {
        console.warn('Avatar model list failed:', error);
      }
    };

    const loadTtsVoices = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/tts/voices`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const voices = Array.isArray(data.voices) && data.voices.length ? data.voices : FALLBACK_TTS_VOICES;
        if (cancelled) return;
        setTtsVoices(voices);
        setSelectedVoice((current) => {
          const saved = window.localStorage.getItem('airi.tts.voice');
          const preferred = saved || current || data.selected || DEFAULT_TTS_VOICE;
          if (voices.some((item) => item.id === preferred)) return preferred;
          if (voices.some((item) => item.id === data.selected)) return data.selected;
          return voices[0]?.id || DEFAULT_TTS_VOICE;
        });
      } catch (error) {
        console.warn('TTS voice list failed:', error);
      }
    };

    loadAvatarModels();
    loadTtsVoices();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem('airi.avatar.model', selectedModelUrl);
    setAvatarFit(readAvatarFit(selectedModelUrl));
  }, [selectedModelUrl]);

  useEffect(() => {
    const handleModelLoadFailed = (event) => {
      const failedUrl = event.detail?.url;
      const fallbackUrl = event.detail?.fallbackUrl || DEFAULT_MODEL_URL;
      setSelectedModelUrl((current) => (current === failedUrl ? fallbackUrl : current));
    };

    window.addEventListener('avatar_model_load_failed', handleModelLoadFailed);
    return () => window.removeEventListener('avatar_model_load_failed', handleModelLoadFailed);
  }, []);

  useEffect(() => {
    window.localStorage.setItem('airi.tts.voice', selectedVoice);
    window.localStorage.setItem('airi.tts.rate', selectedRate);
    window.__AIRI_TTS_CONFIG = { voice: selectedVoice, rate: selectedRate };
  }, [selectedVoice, selectedRate]);

  useEffect(() => {
    window.__AIRI_AVATAR_CONFIG = { ...avatarFit, modelProfile: selectedModel };
  }, [avatarFit, selectedModel]);

  useEffect(() => {
    window.__AIRI_AVATAR_DEBUG_CONFIG = avatarDebugConfig;
    window.dispatchEvent(new CustomEvent('avatar_debug_config', { detail: avatarDebugConfig }));
  }, [avatarDebugConfig]);

  const handleModelChange = (modelUrl) => {
    setSelectedModelUrl(modelUrl);
    setAvatarFit(readAvatarFit(modelUrl));
  };

  const handleAvatarFitChange = (patch) => {
    setAvatarFit((current) => {
      const next = normalizeAvatarFit({ ...current, ...patch });
      window.localStorage.setItem(fitStorageKey(selectedModelUrl), JSON.stringify(next));
      window.__AIRI_AVATAR_CONFIG = { ...next, modelProfile: selectedModel };
      return next;
    });
  };

  const handleAvatarFitReset = () => {
    const next = defaultFitForModel(selectedModelUrl);
    window.localStorage.setItem(fitStorageKey(selectedModelUrl), JSON.stringify(next));
    window.__AIRI_AVATAR_CONFIG = { ...next, modelProfile: selectedModel };
    setAvatarFit(next);
  };

  const handlePreviewVoice = () => {
    window.dispatchEvent(new CustomEvent('ai_speech_cancel', {
      detail: { message: '正在切换试听语音' },
    }));
    window.dispatchEvent(new CustomEvent('ai_speak', {
      detail: {
        text: '你好，我是 AIRI。这个音色会用于接下来的回答。',
        action: { expression: 'warm', motion: 'idle', style: 'normal', reason: 'voice_preview' },
        intent: 'replace',
        turnId: `preview-${Date.now()}`,
      },
    }));
  };

  const handleAvatarDebugConfigChange = (patch) => {
    setAvatarDebugConfig((current) => writeAvatarDebugConfig({ ...current, ...patch }));
  };

  const handleAvatarDebugReset = () => {
    setAvatarDebugConfig(writeAvatarDebugConfig(DEFAULT_AVATAR_DEBUG_CONFIG));
  };

  const handleTriggerEmotion = (emotionId) => {
    window.dispatchEvent(new CustomEvent('avatar_action', {
      detail: actionForEmotion(emotionId, { reason: `debug_emotion_${emotionId}` }),
    }));
  };

  const handleTriggerMotion = (motion) => {
    window.dispatchEvent(new CustomEvent('avatar_action', {
      detail: actionForEmotion(avatarTelemetry.emotion, {
        motion,
        style: motion === 'idle' ? 'idle' : 'interaction',
        reason: `debug_motion_${motion}`,
      }),
    }));
  };

  const handleTriggerRuntimeMotion = (motion) => {
    window.dispatchEvent(new CustomEvent('avatar_action', {
      detail: actionForEmotion(avatarTelemetry.emotion, {
        motion: { group: motion.group, index: motion.index },
        style: 'interaction',
        reason: `debug_runtime_motion_${motion.group}_${motion.index}`,
      }),
    }));
  };

  const handleSetRuntimeMotionIdle = (motion) => {
    window.localStorage.setItem('selected-runtime-motion-group', motion.group);
    window.localStorage.setItem('selected-runtime-motion-index', String(motion.index));
    handleTriggerRuntimeMotion(motion);
  };

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute',
        inset: 0,
        zIndex: 0,
        backgroundImage: 'url("https://images.unsplash.com/photo-1534447677768-be436bb09401?q=80&w=2094&auto=format&fit=crop")',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        opacity: 0.8,
      }} />

      <div style={{
        position: 'relative',
        zIndex: 10,
        display: 'flex',
        width: '100%',
        height: '100%',
        padding: '24px',
        boxSizing: 'border-box',
        gap: '24px',
      }}>
        <section className="liquid-glass-strong" style={{
          width: '52%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          padding: '32px',
          boxSizing: 'border-box',
        }}>
          <h2 style={{ margin: 0, fontWeight: 600, fontSize: '1.5rem' }}>
            airi <span className="font-serif">ai</span>
          </h2>

          <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
            <Live2DViewer modelUrl={selectedModelUrl} modelFit={avatarFit} modelProfile={selectedModel} />
          </div>

          <div style={{ marginTop: 'auto' }}>
            <div style={{
              fontSize: '10px',
              letterSpacing: 0,
              textTransform: 'uppercase',
              color: 'rgba(255,255,255,0.5)',
              marginBottom: '8px',
            }}>
              Visionary Assistant
            </div>
            <div style={{ fontSize: '1.2rem' }}>
              "We imagined a realm with <span className="font-serif">no ending.</span>"
            </div>
            <div style={{ marginTop: '14px', display: 'flex', alignItems: 'stretch', gap: '10px', flexWrap: 'wrap' }}>
              <SpeechStatus status={speechStatus} />
              <LevelMeter compact energy={avatarTelemetry.energy} emotionInfo={avatarTelemetry.emotionInfo} />
            </div>
          </div>
        </section>

        <section style={{ width: '48%', height: '100%', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <SystemPanel
            systemStatus={systemStatus}
            systemError={systemError}
            lastRetrieval={lastRetrieval}
            lastLlm={lastLlm}
            avatarModels={avatarModels}
            selectedModelUrl={selectedModelUrl}
            onModelChange={handleModelChange}
            ttsVoices={ttsVoices}
            selectedVoice={selectedVoice}
            onVoiceChange={setSelectedVoice}
            selectedRate={selectedRate}
            onRateChange={setSelectedRate}
            avatarFit={avatarFit}
            onAvatarFitChange={handleAvatarFitChange}
            onAvatarFitReset={handleAvatarFitReset}
            onPreviewVoice={handlePreviewVoice}
          />

          <div style={{
            flex: '0 0 auto',
            maxHeight: avatarDebugOpen ? '46vh' : 'auto',
            overflowY: avatarDebugOpen ? 'auto' : 'visible',
            paddingRight: avatarDebugOpen ? '2px' : 0,
          }}>
            <AvatarDebugPanel
              open={avatarDebugOpen}
              onToggle={() => setAvatarDebugOpen((value) => !value)}
              telemetry={avatarTelemetry}
              config={avatarDebugConfig}
              onConfigChange={handleAvatarDebugConfigChange}
              onReset={handleAvatarDebugReset}
              onTriggerEmotion={handleTriggerEmotion}
              onTriggerMotion={handleTriggerMotion}
              onTriggerRuntimeMotion={handleTriggerRuntimeMotion}
              onSetRuntimeMotionIdle={handleSetRuntimeMotionIdle}
              modelName={selectedModel.name}
            />
          </div>

          <div className="liquid-glass-strong" style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            padding: '24px',
            boxSizing: 'border-box',
            minHeight: 0,
          }}>
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px', paddingBottom: '20px' }}>
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  style={{
                    alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: '82%',
                  }}
                >
                  {msg.role === 'user' ? (
                    <div className="liquid-glass" style={{ padding: '12px 20px', fontSize: '14px', lineHeight: 1.6 }}>
                      {msg.content}
                    </div>
                  ) : (
                    <div style={{ padding: '12px', fontSize: '14px', lineHeight: 1.6, color: 'rgba(255,255,255,0.9)' }}>
                      <span className="font-serif" style={{ marginRight: '8px', fontSize: '18px' }}>✧</span>
                      {msg.content}
                      <AnswerMeta llm={msg.llm} error={msg.error} />
                      <SourceList sources={msg.sources} />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.55)', padding: '12px' }}>
                  <span className="font-serif">{statusText || '处理中...'}</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: 'auto' }}>
              <input
                className="liquid-glass"
                type="text"
                value={inputText}
                onInput={(event) => handleInputTextChange(event.currentTarget.value)}
                onChange={(event) => handleInputTextChange(event.currentTarget.value)}
                onKeyDown={(event) => event.key === 'Enter' && handleSendMessage()}
                placeholder="向 AIRI 提问校园规章、办事流程或服务信息..."
                style={{
                  flex: 1,
                  padding: '16px 20px',
                  fontSize: '14px',
                  color: 'white',
                  outline: 'none',
                }}
              />
              <button
                className="liquid-glass hover-scale active-scale"
                onClick={handleSendMessage}
                disabled={isLoading}
                style={{
                  width: '52px',
                  height: '52px',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.5 : 1,
                }}
              >
                <Send size={20} color="white" />
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
