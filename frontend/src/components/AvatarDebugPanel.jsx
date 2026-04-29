import { useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  RotateCcw,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';
import {
  BEAT_STYLES,
  EMOTION_VALUES,
  MOTION_PRESETS,
} from '../avatar/emotionSystem';
import LevelMeter from './LevelMeter';

function DebugRange({ label, value, min = 0, max = 1.8, step = 0.01, onChange }) {
  return (
    <label style={{ display: 'grid', gap: '6px', minWidth: 0 }}>
      <span style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
        <span style={{ color: 'rgba(255,255,255,0.54)', fontSize: '11px' }}>{label}</span>
        <span style={{ color: 'rgba(255,255,255,0.76)', fontSize: '11px' }}>{Math.round(value * 100)}%</span>
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

function ChipButton({ active, children, onClick, tone = '#7cf3bd' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '7px 9px',
        borderRadius: '8px',
        color: active ? '#08110d' : 'rgba(255,255,255,0.72)',
        background: active ? tone : 'rgba(255,255,255,0.06)',
        border: active ? '1px solid transparent' : '1px solid rgba(255,255,255,0.08)',
        cursor: 'pointer',
        fontSize: '12px',
        transition: 'background 140ms ease, color 140ms ease, border-color 140ms ease',
      }}
    >
      {children}
    </button>
  );
}

export default function AvatarDebugPanel({
  open,
  onToggle,
  telemetry,
  config,
  onConfigChange,
  onReset,
  onTriggerEmotion,
  onTriggerMotion,
  onTriggerRuntimeMotion,
  onSetRuntimeMotionIdle,
  modelName,
}) {
  const emotionInfo = telemetry.emotionInfo;
  const action = telemetry.action || {};
  const tone = emotionInfo?.tone || '#7cf3bd';
  const capabilities = telemetry.capabilities || {};
  const runtimeMotions = useMemo(() => capabilities.motions || [], [capabilities.motions]);
  const [runtimeMotionValue, setRuntimeMotionValue] = useState('');
  const motionCount = capabilities.motions?.length || 0;
  const parameterCount = capabilities.parameters?.length || 0;
  const expressionCount = capabilities.expressions?.length || 0;
  const lipSyncCount = capabilities.lipSyncParams?.length || 0;
  const profileName = capabilities.profile?.name;
  const specialToken = telemetry.specialToken;
  const selectedRuntimeMotion = runtimeMotions.find((item) => `${item.group}:${item.index}` === runtimeMotionValue);

  return (
    <div className="liquid-glass-strong" style={{ padding: open ? '12px' : 0, display: 'grid', gap: '10px' }}>
      <button
        type="button"
        onClick={onToggle}
        style={{
          width: '100%',
          padding: open ? '0 0 2px' : '11px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          color: 'white',
          background: 'transparent',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '9px', minWidth: 0 }}>
          <span style={{
            width: '8px',
            height: '8px',
            flex: '0 0 auto',
            borderRadius: '50%',
            background: tone,
            boxShadow: `0 0 16px ${tone}99`,
          }} />
          <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13px', color: 'rgba(255,255,255,0.86)' }}>
            表现调试 · {emotionInfo?.label || '平静'} · {modelName || 'Live2D'}
          </span>
        </span>
        {open ? <ChevronUp size={17} color="rgba(255,255,255,0.68)" /> : <ChevronDown size={17} color="rgba(255,255,255,0.68)" />}
      </button>

      {open && (
        <>
          <div className="liquid-glass" style={{ padding: '9px 11px', color: 'rgba(255,255,255,0.62)', fontSize: '12px', lineHeight: 1.5 }}>
            模型能力 · Motion {motionCount} · 参数 {parameterCount} · 表情 {expressionCount} · 口型参数 {lipSyncCount || '默认'}
            {profileName && (
              <span style={{ marginLeft: '10px', color: 'rgba(255,255,255,0.72)' }}>
                Profile · {profileName}
              </span>
            )}
            {specialToken && (
              <span style={{ marginLeft: '10px', color: tone }}>
                AIRI token · {specialToken.type === 'delay' ? `${specialToken.seconds}s` : specialToken.emotion || specialToken.type}
              </span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 190px', gap: '10px', alignItems: 'stretch' }}>
            <div className="liquid-glass" style={{ padding: '11px', display: 'grid', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', color: 'rgba(255,255,255,0.64)', fontSize: '12px' }}>
                  <Sparkles size={14} color={tone} />
                  情绪
                </span>
                <span style={{ color: 'rgba(255,255,255,0.42)', fontSize: '11px' }}>{action.reason || 'idle'}</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '7px' }}>
                {EMOTION_VALUES.map((item) => (
                  <ChipButton
                    key={item.id}
                    active={telemetry.emotion === item.id}
                    tone={item.tone}
                    onClick={() => onTriggerEmotion(item.id)}
                  >
                    {item.label}
                  </ChipButton>
                ))}
              </div>
            </div>

            <LevelMeter energy={telemetry.energy} emotionInfo={emotionInfo} />
          </div>

          <div className="liquid-glass" style={{ padding: '11px', display: 'grid', gap: '10px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', color: 'rgba(255,255,255,0.64)', fontSize: '12px' }}>
              <SlidersHorizontal size={14} color="rgba(255,255,255,0.66)" />
              动作
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '7px' }}>
              {MOTION_PRESETS.map((item) => (
                <ChipButton
                  key={item.id}
                  active={action.motion === item.id}
                  onClick={() => onTriggerMotion(item.id)}
                >
                  {item.label}
                </ChipButton>
              ))}
            </div>
            {runtimeMotions.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto auto', gap: '8px', alignItems: 'center' }}>
                <select
                  value={runtimeMotionValue}
                  onChange={(event) => setRuntimeMotionValue(event.target.value)}
                  className="liquid-glass"
                  style={{
                    minWidth: 0,
                    width: '100%',
                    padding: '9px 10px',
                    color: 'rgba(255,255,255,0.84)',
                    backgroundColor: 'rgba(20,26,35,0.82)',
                    outline: 'none',
                    cursor: 'pointer',
                    fontSize: '12px',
                  }}
                >
                  <option value="">选择当前模型的原生 motion</option>
                  {runtimeMotions.map((item) => (
                    <option key={`${item.group}:${item.index}:${item.file}`} value={`${item.group}:${item.index}`}>
                      {item.group}[{item.index}] {item.file || item.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={!selectedRuntimeMotion}
                  onClick={() => selectedRuntimeMotion && onTriggerRuntimeMotion?.(selectedRuntimeMotion)}
                  style={{
                    padding: '9px 11px',
                    borderRadius: '8px',
                    color: selectedRuntimeMotion ? 'rgba(255,255,255,0.86)' : 'rgba(255,255,255,0.34)',
                    background: 'rgba(255,255,255,0.06)',
                    cursor: selectedRuntimeMotion ? 'pointer' : 'not-allowed',
                    fontSize: '12px',
                  }}
                >
                  播放
                </button>
                <button
                  type="button"
                  disabled={!selectedRuntimeMotion}
                  onClick={() => selectedRuntimeMotion && onSetRuntimeMotionIdle?.(selectedRuntimeMotion)}
                  style={{
                    padding: '9px 11px',
                    borderRadius: '8px',
                    color: selectedRuntimeMotion ? 'rgba(255,255,255,0.86)' : 'rgba(255,255,255,0.34)',
                    background: 'rgba(255,255,255,0.06)',
                    cursor: selectedRuntimeMotion ? 'pointer' : 'not-allowed',
                    fontSize: '12px',
                  }}
                >
                  待机
                </button>
              </div>
            )}
          </div>

          <div className="liquid-glass" style={{ padding: '11px', display: 'grid', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <span style={{ color: 'rgba(255,255,255,0.64)', fontSize: '12px' }}>实时参数</span>
              <button
                type="button"
                onClick={onReset}
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
              <DebugRange label="视线追踪" value={config.focusGain} onChange={(value) => onConfigChange({ focusGain: value })} />
              <DebugRange label="说话身体" value={config.speechMotionGain} onChange={(value) => onConfigChange({ speechMotionGain: value })} />
              <DebugRange label="呼吸幅度" value={config.breathGain} onChange={(value) => onConfigChange({ breathGain: value })} />
              <DebugRange label="情绪脸颊" value={config.cheekGain} onChange={(value) => onConfigChange({ cheekGain: value })} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '10px', alignItems: 'end' }}>
              <label style={{ display: 'grid', gap: '6px', minWidth: 0 }}>
                <span style={{ color: 'rgba(255,255,255,0.54)', fontSize: '11px' }}>说话节奏</span>
                <select
                  value={config.beatStyle}
                  onChange={(event) => onConfigChange({ beatStyle: event.target.value })}
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
                  {BEAT_STYLES.map((item) => (
                    <option key={item.id} value={item.id}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', height: '39px', color: 'rgba(255,255,255,0.68)', fontSize: '12px' }}>
                <input
                  type="checkbox"
                  checked={config.autoBeatStyle}
                  onChange={(event) => onConfigChange({ autoBeatStyle: event.target.checked })}
                  style={{ accentColor: '#7cf3bd' }}
                />
                自动节奏
              </label>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 16px', alignItems: 'center' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'rgba(255,255,255,0.68)', fontSize: '12px' }}>
                <input
                  type="checkbox"
                  checked={config.live2dIdleAnimationEnabled}
                  onChange={(event) => onConfigChange({ live2dIdleAnimationEnabled: event.target.checked })}
                  style={{ accentColor: '#7cf3bd' }}
                />
                AIRI idle motion
              </label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'rgba(255,255,255,0.68)', fontSize: '12px' }}>
                <input
                  type="checkbox"
                  checked={config.live2dAutoBlinkEnabled}
                  onChange={(event) => onConfigChange({ live2dAutoBlinkEnabled: event.target.checked })}
                  style={{ accentColor: '#7cf3bd' }}
                />
                AIRI 自动眨眼
              </label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'rgba(255,255,255,0.68)', fontSize: '12px' }}>
                <input
                  type="checkbox"
                  checked={config.live2dForceAutoBlinkEnabled}
                  onChange={(event) => onConfigChange({ live2dForceAutoBlinkEnabled: event.target.checked })}
                  style={{ accentColor: '#7cf3bd' }}
                />
                强制眨眼
              </label>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
