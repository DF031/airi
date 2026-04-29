import { Activity } from 'lucide-react';

const BAR_COUNT = 14;

function percent(value) {
  return `${Math.round(Math.max(0, Math.min(1, Number(value || 0))) * 100)}%`;
}

export default function LevelMeter({ energy, emotionInfo, compact = false }) {
  const mouth = Math.max(0, Math.min(1, Number(energy?.value || 0)));
  const audio = Math.max(0, Math.min(1, Number(energy?.energy || 0)));
  const lipSync = energy?.lipSync == null ? 0 : Math.max(0, Math.min(1, Number(energy.lipSync || 0)));
  const tone = emotionInfo?.tone || '#7cf3bd';
  const active = Math.max(mouth, audio, lipSync);

  return (
    <div
      className="liquid-glass"
      style={{
        padding: compact ? '8px 9px' : '10px 11px',
        display: 'grid',
        gap: '8px',
        minWidth: compact ? '150px' : '190px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', color: 'rgba(255,255,255,0.68)', fontSize: '12px' }}>
          <Activity size={14} color={tone} />
          Level
        </span>
        <span style={{ color: tone, fontSize: '12px' }}>{percent(active)}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${BAR_COUNT}, minmax(3px, 1fr))`, gap: '4px', alignItems: 'end', height: '34px' }}>
        {Array.from({ length: BAR_COUNT }).map((_, index) => {
          const threshold = (index + 1) / BAR_COUNT;
          const filled = active >= threshold * 0.78;
          const height = 20 + (((index * 7) % 13) * 2);
          return (
            <span
              key={index}
              style={{
                height: `${height}px`,
                borderRadius: '4px',
                background: filled ? tone : 'rgba(255,255,255,0.11)',
                opacity: filled ? 0.9 : 0.75,
                boxShadow: filled ? `0 0 12px ${tone}66` : 'none',
                transition: 'background 120ms ease, opacity 120ms ease, box-shadow 120ms ease',
              }}
            />
          );
        })}
      </div>

      {!compact && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '8px', color: 'rgba(255,255,255,0.56)', fontSize: '11px' }}>
          <span>嘴型 {percent(mouth)}</span>
          <span>音量 {percent(audio)}</span>
          <span>唇形 {energy?.lipSync == null ? '无' : percent(lipSync)}</span>
        </div>
      )}
    </div>
  );
}
