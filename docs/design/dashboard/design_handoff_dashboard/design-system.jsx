/* global React */
const { Fragment } = React;

// =========== TOKENS ===========
const TOKENS = {
  bg: '#0E1117',
  surface: '#1C1C2E',
  surfaceAlt: '#161623',
  border: 'rgba(255,255,255,0.06)',
  borderStrong: 'rgba(255,255,255,0.12)',
  text: '#E8EAED',
  textMuted: '#9AA0AC',
  textDim: '#5C616E',
  accent: '#4F8EF7',
  bull: '#00C47A',
  neutral: '#F5A623',
  bear: '#E84040',
  stop: '#FF0000',
};

const SIGNAL = {
  strong_add: { color: '#00C47A', label: '强力加仓', en: 'strong_add' },
  hold_add:   { color: '#4F8EF7', label: '持有加仓', en: 'hold_add' },
  hold:       { color: '#888888', label: '持有观望', en: 'hold' },
  reduce:     { color: '#E84040', label: '减仓',     en: 'reduce' },
  stop_loss:  { color: '#FF0000', label: '止损',     en: 'stop_loss' },
};

// =========== PRIMITIVES ===========
const Card = ({ children, style, pad = 12 }) => (
  <div style={{
    background: TOKENS.surface,
    border: `1px solid ${TOKENS.border}`,
    borderRadius: 8,
    padding: pad,
    ...style,
  }}>{children}</div>
);

const SectionTitle = ({ children, sub }) => (
  <div style={{ marginBottom: 12 }}>
    <div style={{ color: TOKENS.text, fontSize: 15, fontWeight: 600, letterSpacing: '0.02em' }}>{children}</div>
    {sub && <div style={{ color: TOKENS.textMuted, fontSize: 11, marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>{sub}</div>}
  </div>
);

const Mono = ({ children, style }) => (
  <span style={{ fontFamily: 'JetBrains Mono, ui-monospace, monospace', ...style }}>{children}</span>
);

// =========== DESIGN SYSTEM SHEET ===========
function DesignSystem() {
  return (
    <div style={{
      width: 1280,
      background: TOKENS.bg,
      color: TOKENS.text,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      padding: 28,
      boxSizing: 'border-box',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: `1px solid ${TOKENS.border}`, paddingBottom: 16, marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, letterSpacing: '0.18em', fontFamily: 'JetBrains Mono, monospace' }}>DESIGN SYSTEM · v0.1</div>
          <div style={{ fontSize: 26, fontWeight: 600, marginTop: 4 }}>my-invest-global / 设计规范</div>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginTop: 6 }}>A股 AI 基建组合监控仪表盘 · Streamlit Dark · 中文优先</div>
        </div>
        <Mono style={{ fontSize: 11, color: TOKENS.textDim }}>更新于 2026-05-17</Mono>
      </div>

      {/* COLORS */}
      <SectionTitle sub="01 / COLORS">颜色系统</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 28 }}>
        <Card pad={16}>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginBottom: 12 }}>表面 / 中性</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {[
              ['页面背景', TOKENS.bg, '--bg'],
              ['卡片背景', TOKENS.surface, '--surface'],
              ['替代表面', TOKENS.surfaceAlt, '--surface-alt'],
              ['描边', TOKENS.border, '--border'],
              ['主文本', TOKENS.text, '--text'],
              ['次文本', TOKENS.textMuted, '--text-muted'],
              ['弱文本', TOKENS.textDim, '--text-dim'],
            ].map(([name, hex, token]) => (
              <div key={token} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 32, height: 32, background: hex, borderRadius: 4, border: `1px solid ${TOKENS.borderStrong}` }} />
                <div style={{ flex: 1, fontSize: 12 }}>{name}</div>
                <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>{token}</Mono>
                <Mono style={{ fontSize: 11, color: TOKENS.text, width: 80, textAlign: 'right' }}>{hex.toUpperCase()}</Mono>
              </div>
            ))}
          </div>
        </Card>
        <Card pad={16}>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginBottom: 12 }}>状态 / 信号</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {[
              ['看涨 / 增长', TOKENS.bull, '--bull', '+x%'],
              ['中性 / 平稳', TOKENS.neutral, '--neutral', '±0%'],
              ['看跌 / 收缩', TOKENS.bear, '--bear', '-x%'],
              ['止损 (强)', TOKENS.stop, '--stop', 'STOP'],
              ['品牌主色', TOKENS.accent, '--accent', '链接 · Tab'],
            ].map(([name, hex, token, usage]) => (
              <div key={token} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 32, height: 32, background: hex, borderRadius: 4 }} />
                <div style={{ flex: 1, fontSize: 12 }}>{name}</div>
                <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{usage}</Mono>
                <Mono style={{ fontSize: 11, color: TOKENS.textMuted, width: 90, textAlign: 'right' }}>{token}</Mono>
                <Mono style={{ fontSize: 11, width: 80, textAlign: 'right' }}>{hex.toUpperCase()}</Mono>
              </div>
            ))}
          </div>
          {/* PnL gradient strip */}
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 6 }}>盈亏热力梯度 (-20% → 0 → +20%)</div>
            <div style={{ height: 18, borderRadius: 3, background: `linear-gradient(90deg, ${TOKENS.bear} 0%, #2a2a3a 50%, ${TOKENS.bull} 100%)` }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: TOKENS.textMuted }}>
              <span>-20%</span><span>-10%</span><span>0</span><span>+10%</span><span>+20%</span>
            </div>
          </div>
        </Card>
      </div>

      {/* TYPOGRAPHY */}
      <SectionTitle sub="02 / TYPOGRAPHY">字体系统</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16, marginBottom: 28 }}>
        <Card pad={18}>
          <div style={{ display: 'grid', gap: 14 }}>
            {[
              { label: 'Display · 24/32 · 600', sample: '持仓总览', size: 24, w: 600, f: 'Noto Sans SC' },
              { label: 'H1 · 18/24 · 600', sample: '资产配置偏离', size: 18, w: 600, f: 'Noto Sans SC' },
              { label: 'H2 · 15/20 · 600', sample: '弹性股 / 光通信', size: 15, w: 600, f: 'Noto Sans SC' },
              { label: 'Body · 13/18 · 400', sample: '5个交易日中3个偏涨、2个偏跌', size: 13, w: 400, f: 'Noto Sans SC' },
              { label: 'Label · 11/14 · 500 · UPPER', sample: '当前占比 · 目标占比', size: 11, w: 500, f: 'Noto Sans SC' },
              { label: 'Mono Big · 26/32 · 600', sample: '+18.59%', size: 26, w: 600, f: 'JetBrains Mono', mono: true },
              { label: 'Mono · 13/18 · 500 · tabular', sample: '300308 · ¥100,800.00', size: 13, w: 500, f: 'JetBrains Mono', mono: true },
            ].map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'baseline', gap: 16, borderBottom: i < 6 ? `1px dashed ${TOKENS.border}` : 'none', paddingBottom: 10 }}>
                <Mono style={{ fontSize: 10, color: TOKENS.textDim, width: 220, flexShrink: 0 }}>{t.label}</Mono>
                <div style={{ fontFamily: t.mono ? 'JetBrains Mono, monospace' : '"Noto Sans SC", sans-serif', fontSize: t.size, fontWeight: t.w, fontVariantNumeric: 'tabular-nums' }}>{t.sample}</div>
              </div>
            ))}
          </div>
        </Card>
        <Card pad={18}>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginBottom: 10 }}>字体家族</div>
          <div style={{ display: 'grid', gap: 12, fontSize: 12 }}>
            <div>
              <div style={{ fontSize: 11, color: TOKENS.textDim }}>UI · 中文 / 拉丁</div>
              <div style={{ fontFamily: '"Noto Sans SC", sans-serif', fontSize: 18, marginTop: 2 }}>Noto Sans SC 思源黑体</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: TOKENS.textDim }}>数字 / 代码</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, marginTop: 2 }}>JetBrains Mono · 0123456789</div>
            </div>
            <div style={{ borderTop: `1px solid ${TOKENS.border}`, paddingTop: 10, marginTop: 4 }}>
              <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 6 }}>所有数值必须启用</div>
              <Mono style={{ fontSize: 11, color: TOKENS.accent }}>font-variant-numeric: tabular-nums</Mono>
              <div style={{ fontSize: 11, color: TOKENS.textDim, marginTop: 4 }}>表格列、KPI、PnL%、占比 — 等宽对齐</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 6 }}>
              <div style={{ background: TOKENS.surfaceAlt, padding: 10, borderRadius: 4 }}>
                <div style={{ fontSize: 10, color: TOKENS.textDim }}>对齐 · 左</div>
                <div style={{ fontFamily: 'Noto Sans SC' }}>股票名 类别</div>
              </div>
              <div style={{ background: TOKENS.surfaceAlt, padding: 10, borderRadius: 4 }}>
                <div style={{ fontSize: 10, color: TOKENS.textDim }}>对齐 · 右</div>
                <Mono style={{ display: 'block', textAlign: 'right' }}>+18.59%</Mono>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* SPACING / RADII */}
      <SectionTitle sub="03 / SPACING & RADII">间距与圆角</SectionTitle>
      <Card pad={18} style={{ marginBottom: 28 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12 }}>
          {[
            ['4', 4, '内部图标间隙'],
            ['8', 8, '标签 ↔ 数值'],
            ['12', 12, '卡片内 padding · 默认'],
            ['16', 16, '卡片间隙'],
            ['20', 20, '分区间隙'],
            ['28', 28, '页面 padding'],
          ].map(([n, px, use]) => (
            <div key={n} style={{ background: TOKENS.surfaceAlt, borderRadius: 4, padding: 12 }}>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 32, marginBottom: 8 }}>
                <div style={{ width: px, height: px, background: TOKENS.accent, borderRadius: 2 }} />
              </div>
              <Mono style={{ fontSize: 16, fontWeight: 600 }}>{n}<span style={{ color: TOKENS.textDim, fontSize: 11, marginLeft: 2 }}>px</span></Mono>
              <div style={{ fontSize: 10, color: TOKENS.textMuted, marginTop: 2 }}>{use}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 16, marginTop: 16, paddingTop: 16, borderTop: `1px solid ${TOKENS.border}` }}>
          {[['4', 'badge'], ['6', 'tag'], ['8', '卡片 default'], ['12', 'modal']].map(([r, u]) => (
            <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 36, height: 36, background: TOKENS.surface, border: `1px solid ${TOKENS.borderStrong}`, borderRadius: Number(r) }} />
              <div>
                <Mono style={{ fontSize: 13 }}>radius {r}</Mono>
                <div style={{ fontSize: 10, color: TOKENS.textMuted }}>{u}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* COMPONENTS */}
      <SectionTitle sub="04 / COMPONENTS">组件库</SectionTitle>

      {/* Tabs */}
      <div style={{ fontSize: 12, color: TOKENS.textMuted, margin: '4px 0 8px' }}>4.1 顶部 Tab 导航</div>
      <Card pad={0} style={{ marginBottom: 16, overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: `1px solid ${TOKENS.border}` }}>
          {['持仓总览', '个股深度', '行业概览', '信号建议'].map((t, i) => (
            <div key={t} style={{
              padding: '14px 22px',
              fontSize: 14,
              fontWeight: i === 0 ? 600 : 400,
              color: i === 0 ? TOKENS.text : TOKENS.textMuted,
              borderBottom: i === 0 ? `2px solid ${TOKENS.accent}` : '2px solid transparent',
              cursor: 'pointer',
            }}>
              <span style={{ color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, marginRight: 8 }}>0{i + 1}</span>
              {t}
            </div>
          ))}
        </div>
      </Card>

      {/* KPI cards */}
      <div style={{ fontSize: 12, color: TOKENS.textMuted, margin: '12px 0 8px' }}>4.2 KPI 卡片 · label 顶 / 数值大 / 副文本</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <KPICard label="组合总市值" value="¥910,800" sub="较昨日 +¥4,128" tone="bull" />
        <KPICard label="总盈亏%" value="+5.18%" sub="¥+44,889" tone="bull" big />
        <KPICard label="最大单只占比" value="11.07%" sub="300308 · 超阈值" tone="bear" />
        <KPICard label="白马 / 弹性" value="67.5 / 32.5" sub="目标 67 / 33" tone="neutral" unit="%" />
      </div>

      {/* Badges */}
      <div style={{ fontSize: 12, color: TOKENS.textMuted, margin: '12px 0 8px' }}>4.3 信号徽章 · Signal Badges</div>
      <Card pad={16} style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center' }}>
          {Object.entries(SIGNAL).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <SignalBadge type={k} />
              <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{v.en}</Mono>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 14, paddingTop: 14, borderTop: `1px solid ${TOKENS.border}` }}>
          <Tag>白马股</Tag>
          <Tag>弹性股</Tag>
          <Tag muted>光通信</Tag>
          <Tag muted>半导体</Tag>
          <Tag muted>算力</Tag>
          <Tag tone="bull">条件触发</Tag>
          <Tag tone="bear">超阈值</Tag>
          <Tag tone="neutral">方向分歧</Tag>
        </div>
      </Card>

      {/* Table */}
      <div style={{ fontSize: 12, color: TOKENS.textMuted, margin: '12px 0 8px' }}>4.4 表格 · 行高 36 · 表头小写灰</div>
      <Card pad={0} style={{ marginBottom: 16, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: TOKENS.surfaceAlt }}>
              {['股票名', '类别', '当前占比', '目标占比', '偏差', '操作建议'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 500, fontSize: 11, color: TOKENS.textMuted, letterSpacing: '0.04em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <TableRow stock="中际旭创" code="300308" cat="弹性股" cur="11.07" target="6.00" dev="+5.07" sig="reduce" highlight="warn" />
            <TableRow stock="海康威视" code="002415" cat="白马股" cur="23.06" target="20.00" dev="+3.06" sig="hold" />
            <TableRow stock="景嘉微" code="300474" cat="弹性股" cur="3.07" target="5.00" dev="-1.93" sig="hold_add" />
          </tbody>
        </table>
      </Card>

      {/* Heatmap cell */}
      <div style={{ fontSize: 12, color: TOKENS.textMuted, margin: '12px 0 8px' }}>4.5 热力单元 · 尺寸=市值 · 色=PnL%</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 20 }}>
        <HeatCell name="中际旭创" code="300308" pnl={18.59} />
        <HeatCell name="海康威视" code="002415" pnl={5.2} />
        <HeatCell name="招商银行" code="600036" pnl={-1.2} />
        <HeatCell name="景嘉微" code="300474" pnl={-8.2} />
      </div>

      {/* Footer note */}
      <div style={{ borderTop: `1px solid ${TOKENS.border}`, paddingTop: 14, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: TOKENS.textDim }}>
        <Mono>my-invest-global · personal · A-share AI infra portfolio</Mono>
        <Mono>本设计规范用于 4 个 dashboard tabs 的统一基准</Mono>
      </div>
    </div>
  );
}

// =========== SUB COMPONENTS ===========
function KPICard({ label, value, sub, tone = 'neutral', big, unit }) {
  const toneColor = { bull: TOKENS.bull, bear: TOKENS.bear, neutral: TOKENS.text }[tone];
  return (
    <div style={{
      background: TOKENS.surface,
      border: `1px solid ${TOKENS.border}`,
      borderRadius: 8,
      padding: 12,
    }}>
      <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 8 }}>{label}</div>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: big ? 24 : 20,
        fontWeight: 600,
        color: toneColor,
        fontVariantNumeric: 'tabular-nums',
        lineHeight: 1.1,
      }}>
        {value}{unit && <span style={{ fontSize: 12, color: TOKENS.textMuted, marginLeft: 4 }}>{unit}</span>}
      </div>
      <div style={{ fontSize: 11, color: TOKENS.textDim, marginTop: 6, fontFamily: 'JetBrains Mono, monospace' }}>{sub}</div>
    </div>
  );
}

function SignalBadge({ type, size = 'md' }) {
  const s = SIGNAL[type];
  const padY = size === 'sm' ? 2 : 4;
  const padX = size === 'sm' ? 6 : 8;
  const fs = size === 'sm' ? 10 : 11;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: `${padY}px ${padX}px`,
      background: `${s.color}22`,
      border: `1px solid ${s.color}55`,
      color: s.color,
      borderRadius: 4,
      fontSize: fs,
      fontWeight: 600,
      letterSpacing: '0.02em',
      lineHeight: 1.2,
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: s.color }} />
      {s.label}
    </span>
  );
}

function Tag({ children, tone, muted }) {
  const colors = {
    bull: { c: TOKENS.bull, b: '#00C47A33' },
    bear: { c: TOKENS.bear, b: '#E8404033' },
    neutral: { c: TOKENS.neutral, b: '#F5A62333' },
    default: { c: TOKENS.accent, b: '#4F8EF733' },
    muted: { c: TOKENS.textMuted, b: 'rgba(255,255,255,0.08)' },
  };
  const cfg = muted ? colors.muted : (colors[tone] || colors.default);
  return (
    <span style={{
      padding: '3px 8px',
      background: cfg.b,
      color: cfg.c,
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 500,
      lineHeight: 1.3,
    }}>{children}</span>
  );
}

function TableRow({ stock, code, cat, cur, target, dev, sig, highlight }) {
  const devNum = parseFloat(dev);
  const isPos = devNum > 0;
  let rowBg = 'transparent';
  if (highlight === 'warn') rowBg = `${TOKENS.neutral}14`;
  if (highlight === 'danger') rowBg = `${TOKENS.bear}1A`;
  return (
    <tr style={{ background: rowBg, borderTop: `1px solid ${TOKENS.border}` }}>
      <td style={{ padding: '10px 14px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontWeight: 500 }}>{stock}</span>
          <Mono style={{ fontSize: 11, color: TOKENS.textDim }}>{code}</Mono>
        </div>
      </td>
      <td style={{ padding: '10px 14px' }}><Tag muted={cat === '白马股' ? false : false}>{cat}</Tag></td>
      <td style={{ padding: '10px 14px', textAlign: 'right' }}><Mono>{cur}%</Mono></td>
      <td style={{ padding: '10px 14px', textAlign: 'right', color: TOKENS.textMuted }}><Mono>{target}%</Mono></td>
      <td style={{ padding: '10px 14px', textAlign: 'right' }}>
        <Mono style={{ color: isPos ? TOKENS.bull : TOKENS.bear }}>{isPos ? '+' : ''}{dev}%</Mono>
      </td>
      <td style={{ padding: '10px 14px' }}><SignalBadge type={sig} size="sm" /></td>
    </tr>
  );
}

function pnlColor(pnl) {
  const t = Math.max(-1, Math.min(1, pnl / 20));
  if (t > 0) {
    // green
    const a = 0.15 + t * 0.55;
    return `rgba(0, 196, 122, ${a})`;
  } else if (t < 0) {
    const a = 0.15 + Math.abs(t) * 0.55;
    return `rgba(232, 64, 64, ${a})`;
  }
  return 'rgba(255,255,255,0.04)';
}

function HeatCell({ name, code, pnl }) {
  const isPos = pnl >= 0;
  return (
    <div style={{
      background: pnlColor(pnl),
      border: `1px solid ${isPos ? '#00C47A55' : '#E8404055'}`,
      borderRadius: 6,
      padding: '12px 14px',
      minHeight: 70,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
    }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{name}</div>
        <Mono style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)' }}>{code}</Mono>
      </div>
      <Mono style={{ fontSize: 16, fontWeight: 600, color: '#fff' }}>{isPos ? '+' : ''}{pnl.toFixed(2)}%</Mono>
    </div>
  );
}

Object.assign(window, {
  DesignSystem, TOKENS, SIGNAL, Card, SectionTitle, Mono,
  KPICard, SignalBadge, Tag, TableRow, HeatCell, pnlColor,
});
