/* global React, TOKENS, SIGNAL, Card, Mono, SignalBadge, Tag, TIER_COLORS */

// =========== MACRO STATE (from engine/macro_gate.py: green=38%, yellow=33%, red=20% elastic target) ===========
const MACRO_STATES = [
  { key: 'green',  label: '增长期', target: 38, color: TOKENS.bull,    desc: '超大云厂商 CapEx 加速上调 · 加仓弹性' },
  { key: 'yellow', label: '平稳期', target: 33, color: TOKENS.neutral, desc: 'CapEx 持平 / 数据分歧 · 保持配置' },
  { key: 'red',    label: '收缩期', target: 20, color: TOKENS.bear,    desc: 'CapEx 下调 · 回撤至防御仓位' },
];
const CURRENT_MACRO_KEY = 'green';
const CURRENT_MACRO = MACRO_STATES.find(s => s.key === CURRENT_MACRO_KEY);

// =========== CLOUD CAPEX (methodology.md: Big-4, 2026 guidance vs 2025 actual) ===========
const CLOUD_CAPEX = [
  { co: 'Microsoft', sym: 'MSFT', cloud: 'Azure',        q4_25: 137.5, q1_26: 200.0, yoy: +45, trend: 'up' },
  { co: 'Amazon',    sym: 'AMZN', cloud: 'AWS',          q4_25: 175.0, q1_26: 250.0, yoy: +43, trend: 'up' },
  { co: 'Google',    sym: 'GOOG', cloud: 'GCP',          q4_25: 125.0, q1_26: 187.5, yoy: +50, trend: 'up' },
  { co: 'Meta',      sym: 'META', cloud: 'AI Infra',     q4_25:  95.0, q1_26: 150.0, yoy: +58, trend: 'up' },
];

function MacroCyclePanel() {
  const stateIdx = MACRO_STATES.findIndex(s => s.key === CURRENT_MACRO_KEY);
  const totalCapex = CLOUD_CAPEX.reduce((s, r) => s + r.q1_26, 0);
  const avgYoY = CLOUD_CAPEX.reduce((s, r) => s + r.yoy, 0) / CLOUD_CAPEX.length;

  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>美股 AI CapEx 周期</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>3-state gauge · 决定弹性股目标仓位 (green 38% / yellow 33% / red 20%)</div>
        </div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>更新于 2026-05-17 · 阶段持续 47 天</Mono>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 24 }}>
        {/* Traffic light */}
        <div>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginBottom: 16 }}>
            {MACRO_STATES.map((s, i) => {
              const active = i === stateIdx;
              return (
                <div key={s.key} style={{
                  flex: 1,
                  background: active ? `${s.color}1A` : TOKENS.surfaceAlt,
                  border: `1px solid ${active ? s.color : TOKENS.border}`,
                  borderRadius: 10,
                  padding: '16px 12px',
                  textAlign: 'center',
                  position: 'relative',
                  opacity: active ? 1 : 0.5,
                }}>
                  <div style={{
                    width: 36, height: 36,
                    borderRadius: '50%',
                    background: active ? s.color : `${s.color}22`,
                    margin: '0 auto 10px',
                    boxShadow: active ? `0 0 22px ${s.color}88` : 'none',
                  }} />
                  <div style={{ fontSize: 14, fontWeight: 600, color: active ? s.color : TOKENS.textMuted }}>{s.label}</div>
                  <Mono style={{ fontSize: 11, color: TOKENS.textDim, display: 'block', marginTop: 2 }}>弹性目标 {s.target}%</Mono>
                  {active && (
                    <div style={{
                      position: 'absolute',
                      bottom: -8, left: '50%', transform: 'translateX(-50%)',
                      fontSize: 9,
                      background: s.color,
                      color: '#fff',
                      padding: '1px 6px',
                      borderRadius: 2,
                      letterSpacing: '0.05em',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}>CURRENT</div>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ background: `${CURRENT_MACRO.color}0F`, border: `1px solid ${CURRENT_MACRO.color}33`, borderLeft: `3px solid ${CURRENT_MACRO.color}`, padding: '10px 12px', borderRadius: 6, fontSize: 12, lineHeight: 1.5 }}>
            <strong style={{ color: CURRENT_MACRO.color }}>{CURRENT_MACRO.label}状态</strong> · {CURRENT_MACRO.desc} · 四大云厂商 2026 指引同比 <Mono style={{ color: TOKENS.bull }}>+{avgYoY.toFixed(0)}%</Mono>
          </div>
        </div>

        {/* Cloud capex table */}
        <div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
            <span>Big-4 云厂商 CapEx 趋势</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', color: TOKENS.bull }}>2026E 合计 ${totalCapex.toFixed(0)}B</span>
          </div>
          <div style={{ background: TOKENS.surfaceAlt, borderRadius: 6, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={cT()}>公司</th>
                  <th style={cT('right')}>2025A</th>
                  <th style={cT('right')}>2026E</th>
                  <th style={cT('right')}>YoY</th>
                  <th style={cT('right')}>趋势</th>
                </tr>
              </thead>
              <tbody>
                {CLOUD_CAPEX.map(r => (
                  <tr key={r.sym} style={{ borderTop: `1px solid ${TOKENS.border}` }}>
                    <td style={cR()}>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                        <span style={{ fontWeight: 500 }}>{r.co}</span>
                        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{r.cloud}</Mono>
                      </div>
                    </td>
                    <td style={cR('right')}><Mono style={{ color: TOKENS.textMuted }}>${r.q4_25.toFixed(0)}B</Mono></td>
                    <td style={cR('right')}><Mono>${r.q1_26.toFixed(0)}B</Mono></td>
                    <td style={cR('right')}><Mono style={{ color: TOKENS.bull, fontWeight: 600 }}>+{r.yoy}%</Mono></td>
                    <td style={cR('right')}>
                      <span style={{ color: TOKENS.bull, fontSize: 14 }}>↑</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Card>
  );
}

function cT(align = 'left') { return { textAlign: align, padding: '8px 10px', fontSize: 10, fontWeight: 500, color: TOKENS.textMuted, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'JetBrains Mono, monospace' }; }
function cR(align = 'left') { return { textAlign: align, padding: '8px 10px', fontSize: 12 }; }

// =========== SCARCITY MATRIX (sourced from methodology.md §2.1) ===========
const SCARCITY_MATRIX = {
  1: {
    title: '极高',
    desc: '全球唯一/双供 · 技术代差 · 良率壁垒',
    stocks: [
      { code: '300308', name: '中际旭创', sector: '光模块',  score: 78, owned: true },
      { code: '300502', name: '新易盛',   sector: '光模块',  score: 72, owned: false },
      { code: '002837', name: '英维克',   sector: '液冷',    score: 75, owned: false },
      { code: '688008', name: '澜起科技', sector: 'HBM接口', score: 81, owned: false },
      { code: '002179', name: '中航光电', sector: '光模块',  score: 71, owned: true },
      { code: 'HW-AS', name: '华为昇腾',   sector: 'AI 芯片', score: 88, owned: false, unlisted: true },
    ],
  },
  2: {
    title: '高',
    desc: '少数玩家 · 切换成本高 · 国产替代',
    stocks: [
      { code: '002916', name: '深南电路', sector: 'AI PCB', score: 68, owned: false },
      { code: '002463', name: '沪电股份', sector: 'AI PCB', score: 62, owned: false },
      { code: '600183', name: '生益科技', sector: '高频CCL', score: 58, owned: false },
      { code: '002371', name: '北方华创', sector: '半导体设备', score: 72, owned: false },
      { code: '688012', name: '中微公司', sector: '半导体设备', score: 64, owned: false },
      { code: '688981', name: '中芯国际', sector: '晶圆代工', score: 58, owned: true },
      { code: '301236', name: '锐捷网络', sector: 'AI 交换机', score: 55, owned: false },
    ],
  },
  3: {
    title: '中',
    desc: '组装/制造 · 玩家较多 · 弹性中等',
    stocks: [
      { code: '000977', name: '浪潮信息', sector: 'AI 服务器', score: 52, owned: false },
      { code: '603019', name: '中科曙光', sector: 'AI 服务器', score: 48, owned: false },
      { code: '002335', name: '科华数据', sector: 'UPS',       score: 45, owned: false },
      { code: '002518', name: '科士达',   sector: 'UPS',       score: 42, owned: false },
      { code: '300474', name: '景嘉微',   sector: 'GPU 国替',   score: 50, owned: true },
    ],
  },
  4: {
    title: '低',
    desc: '产能过剩 · 同质化 · 不建议建仓',
    stocks: [
      { code: '600487', name: '亨通光电', sector: '光纤光缆', score: 35, owned: false },
      { code: '600522', name: '中天科技', sector: '光纤光缆', score: 32, owned: false },
      { code: '601138', name: '工业富联', sector: 'IDC 布线', score: 38, owned: false },
      { code: 'TCL',   name: 'TCL中环',    sector: '光伏材料', score: 28, owned: true, warn: true },
    ],
  },
};

function chipColor(score) {
  if (score >= 70) return TOKENS.bull;
  if (score >= 50) return TOKENS.neutral;
  return TOKENS.bear;
}

function ScarcityMatrix() {
  const counts = Object.entries(SCARCITY_MATRIX).map(([t, c]) => ({ tier: t, n: c.stocks.length, owned: c.stocks.filter(s => s.owned).length }));
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>板块紧缺度矩阵</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>四级稀缺体系 · 标的颜色 = 综合信号分 (绿 ≥70 · 黄 50~70 · 红 &lt;50) · ◉ 已持仓</div>
        </div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>
          覆盖 {counts.reduce((s, c) => s + c.n, 0)} 只 · 已持仓 {counts.reduce((s, c) => s + c.owned, 0)} 只
        </Mono>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
        {[1, 2, 3, 4].map(t => {
          const tc = TIER_COLORS[t];
          const col = SCARCITY_MATRIX[t];
          return (
            <div key={t} style={{
              background: TOKENS.surfaceAlt,
              borderRadius: 6,
              border: `1px solid ${tc.c}33`,
              borderTop: `3px solid ${tc.c}`,
              overflow: 'hidden',
            }}>
              <div style={{ padding: '10px 12px', borderBottom: `1px solid ${TOKENS.border}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <Mono style={{ fontSize: 11, color: tc.c, fontWeight: 600, letterSpacing: '0.04em' }}>TIER-{t}</Mono>
                  <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{col.stocks.length} 只</Mono>
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2, color: tc.c }}>{col.title}</div>
                <div style={{ fontSize: 10, color: TOKENS.textMuted, marginTop: 4, lineHeight: 1.4, minHeight: 28 }}>{col.desc}</div>
              </div>
              <div style={{ padding: 10, display: 'grid', gap: 6 }}>
                {col.stocks.map(s => {
                  const c = chipColor(s.score);
                  return (
                    <div key={s.code} style={{
                      background: `${c}14`,
                      border: `1px solid ${c}44`,
                      borderRadius: 4,
                      padding: '7px 9px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 3,
                      position: 'relative',
                      opacity: s.unlisted ? 0.7 : 1,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 6 }}>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                          {s.owned && <span style={{ color: TOKENS.accent, fontSize: 9 }}>◉</span>}
                          <span style={{ fontSize: 12, fontWeight: 500, color: '#fff' }}>{s.name}</span>
                          {s.warn && <span style={{ fontSize: 9, color: TOKENS.bear }}>⚠</span>}
                        </div>
                        <Mono style={{ fontSize: 11, fontWeight: 600, color: c }}>{s.score}</Mono>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Mono style={{ fontSize: 9, color: TOKENS.textDim }}>{s.code}</Mono>
                        <span style={{ fontSize: 9, color: TOKENS.textMuted }}>{s.sector}</span>
                      </div>
                      {/* mini score bar */}
                      <div style={{ height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 1, marginTop: 1 }}>
                        <div style={{ width: `${s.score}%`, height: '100%', background: c, borderRadius: 1 }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// =========== POSITION GAUGES + REBALANCE TRIGGERS ===========
const TARGET_ELASTIC = CURRENT_MACRO.target; // dynamic by macro state
const TARGET_BAIMA   = 100 - TARGET_ELASTIC;
const CURR_ELASTIC   = 32.5; // from holdings
const CURR_BAIMA     = 67.5;

function Gauge({ label, current, target, tone }) {
  const dev = current - target;
  const adev = Math.abs(dev);
  const inBand = adev < 5;
  const c = !inBand ? TOKENS.bear : tone === 'baima' ? TOKENS.accent : TOKENS.bull;
  // Semi-circular gauge
  const R = 70;
  const range = 50; // ±50% around target shown
  const angleAt = (v) => {
    const offset = v - target;
    const clamped = Math.max(-range, Math.min(range, offset));
    return (clamped / range) * 90 - 90; // -90..90 from top
  };
  const polar = (a) => {
    const rad = (a - 90) * Math.PI / 180;
    return [100 + R * Math.cos(rad), 100 + R * Math.sin(rad)];
  };
  const arcPath = (a1, a2) => {
    const [x1, y1] = polar(a1);
    const [x2, y2] = polar(a2);
    const large = Math.abs(a2 - a1) > 180 ? 1 : 0;
    const sweep = a2 > a1 ? 1 : 0;
    return `M ${x1} ${y1} A ${R} ${R} 0 ${large} ${sweep} ${x2} ${y2}`;
  };

  // Convert angle interpretation: -90 (left) → 90 (right). 0 = target (top of arc rotated).
  // We'll draw arc from -90 to 90 (180° span at top), target at 0.
  // Actually: half-doughnut from 180° (left) to 0° (right), target marker at 90° (top).
  const polarH = (deg) => {
    const rad = (180 - deg) * Math.PI / 180; // 0 = right, 180 = left
    return [100 + R * Math.cos(rad), 120 - R * Math.sin(rad)];
  };
  // 0..180 maps target-range .. target+range
  const valToDeg = (v) => {
    const offset = (v - target);
    const clamped = Math.max(-range, Math.min(range, offset));
    return 90 + (clamped / range) * 90; // 0..180
  };
  const arcH = (d1, d2) => {
    const [x1, y1] = polarH(d1);
    const [x2, y2] = polarH(d2);
    const large = Math.abs(d2 - d1) > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`;
  };
  const curDeg = valToDeg(current);
  const [px, py] = polarH(curDeg);

  return (
    <div style={{ background: TOKENS.surfaceAlt, borderRadius: 8, padding: 14, textAlign: 'center' }}>
      <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 4 }}>{label}</div>
      <svg width={200} height={140} viewBox="0 0 200 140">
        {/* base half ring */}
        <path d={arcH(0, 180)} stroke="rgba(255,255,255,0.06)" strokeWidth="14" fill="none" strokeLinecap="round" />
        {/* tolerance band (±5%) */}
        <path d={arcH(valToDeg(target - 5), valToDeg(target + 5))} stroke={TOKENS.bull + '44'} strokeWidth="14" fill="none" />
        {/* deviation arc from target to current */}
        <path d={curDeg > 90 ? arcH(90, curDeg) : arcH(curDeg, 90)} stroke={c} strokeWidth="14" fill="none" strokeLinecap="round" />
        {/* target tick */}
        <line x1="100" y1="42" x2="100" y2="58" stroke="#fff" strokeWidth="2" />
        <text x="100" y="36" fontSize="9" fill={TOKENS.textMuted} textAnchor="middle" fontFamily="JetBrains Mono">目标 {target}%</text>
        {/* current pointer */}
        <circle cx={px} cy={py} r="6" fill={c} stroke="#fff" strokeWidth="2" />
      </svg>
      <Mono style={{ fontSize: 24, fontWeight: 600, color: c, display: 'block', marginTop: -8, lineHeight: 1 }}>{current.toFixed(1)}%</Mono>
      <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 4 }}>
        偏差 <Mono style={{ color: dev >= 0 ? TOKENS.bull : TOKENS.bear }}>{dev >= 0 ? '+' : ''}{dev.toFixed(1)}%</Mono>
        {' · '}
        <span style={{ color: inBand ? TOKENS.bull : TOKENS.bear }}>{inBand ? '区间内' : '超阈值'}</span>
      </div>
    </div>
  );
}

// 7 triggers from methodology.md §5.3 risk control signal lights
const TRIGGERS = [
  { name: '超大云厂商 CapEx 季度指引',          status: 'green',  desc: '指引上调 → 加仓信号',              last: '2026-05-02', value: '+48% YoY · 上调' },
  { name: '板块 PE 分位数',                     status: 'yellow', desc: '50–75% 区间 → 持有',              last: '2026-05-15', value: '64.2% (历史)' },
  { name: 'GPU 交货周期',                        status: 'green',  desc: '延长 → 需求强',                   last: '2026-05-10', value: '6.5 个月 (↑)' },
  { name: '美联储利率方向',                      status: 'yellow', desc: '暂停 → 持有',                     last: '2026-05-07', value: 'Hold @ 4.25–4.50%' },
  { name: '地缘科技管制',                        status: 'green',  desc: '管制升级 → 国产替代受益',           last: '2026-04-28', value: 'BIS 拟扩大 (↑)' },
  { name: '组合弹性股偏离阈值 (±10%)',           status: 'green',  desc: '偏差 -0.5% → 区间内',              last: '—',           value: '32.5% vs 38%' },
  { name: '单只弹性股占比 (≤8%)',                status: 'red',    desc: '300308 = 11.07% → 减仓',           last: '2026-05-17', value: '+3.07% 超阈值' },
];

const STATUS_META = {
  green:  { c: TOKENS.bull,    label: '正常', icon: '●' },
  yellow: { c: TOKENS.neutral, label: '观察', icon: '●' },
  red:    { c: TOKENS.bear,    label: '触发', icon: '●' },
};

function RebalanceTriggers() {
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>动态仓位 & 再平衡触发器</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>左: 仓位偏离仪表 · 右: 7 项触发器 (源自 methodology §5.3)</div>
        </div>
        <Tag tone="bear">1 项触发中</Tag>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: 16 }}>
        {/* Gauges */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Gauge label="白马股 仓位" current={CURR_BAIMA} target={TARGET_BAIMA} tone="baima" />
          <Gauge label="弹性股 仓位" current={CURR_ELASTIC} target={TARGET_ELASTIC} tone="tanxing" />
        </div>

        {/* Triggers table */}
        <div style={{ background: TOKENS.surfaceAlt, borderRadius: 6, overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '24px 1fr 110px 130px', padding: '8px 12px', borderBottom: `1px solid ${TOKENS.border}`, fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.06em', fontFamily: 'JetBrains Mono, monospace', textTransform: 'uppercase' }}>
            <span></span>
            <span>触发器 · 当前值</span>
            <span>最近变动</span>
            <span style={{ textAlign: 'right' }}>状态</span>
          </div>
          {TRIGGERS.map((t, i) => {
            const m = STATUS_META[t.status];
            return (
              <div key={i} style={{
                display: 'grid',
                gridTemplateColumns: '24px 1fr 110px 130px',
                alignItems: 'center',
                padding: '8px 12px',
                borderTop: i > 0 ? `1px solid ${TOKENS.border}` : 'none',
                background: t.status === 'red' ? `${TOKENS.bear}10` : 'transparent',
              }}>
                <span style={{ color: m.c, fontSize: 11 }}>{m.icon}</span>
                <div>
                  <div style={{ fontSize: 12, color: TOKENS.text }}>{t.name}</div>
                  <div style={{ fontSize: 10, color: TOKENS.textMuted, marginTop: 2 }}>
                    <Mono style={{ color: m.c }}>{t.value}</Mono>
                    <span style={{ color: TOKENS.textDim }}> · {t.desc}</span>
                  </div>
                </div>
                <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{t.last}</Mono>
                <span style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: 10,
                    color: m.c,
                    background: `${m.c}1A`,
                    border: `1px solid ${m.c}44`,
                    padding: '2px 8px',
                    borderRadius: 3,
                    fontWeight: 600,
                    letterSpacing: '0.04em',
                  }}>{m.label}</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

// =========== REBALANCE HISTORY TIMELINE ===========
const HISTORY = [
  { d: '2026-04-19', day: -28, type: 'add',    stock: '英维克 (002837)', amt: '+¥18,000', reason: '液冷渗透率突破 18% 阈值' },
  { d: '2026-04-23', day: -24, type: 'reduce', stock: '亨通光电 (600487)', amt: '-¥12,000', reason: 'Tier-4 降级, 出仓' },
  { d: '2026-04-29', day: -18, type: 'add',    stock: '中芯国际 (688981)', amt: '+¥15,000', reason: 'BIS 管制升级 · 国产替代' },
  { d: '2026-05-02', day: -15, type: 'macro',  stock: '宏观切换',         amt: 'yellow→green', reason: 'CapEx +48% YoY · 弹性目标 33% → 38%' },
  { d: '2026-05-09', day: -8,  type: 'alert',  stock: 'TCL中环 (002129)',  amt: 'stop_loss',  reason: '光伏链景气下行 · 触发 -20% 止损' },
  { d: '2026-05-14', day: -3,  type: 'add',    stock: '澜起科技 (688008)', amt: '+¥22,000',  reason: 'HBM 接口需求超预期' },
  { d: '2026-05-17', day:  0,  type: 'alert',  stock: '中际旭创 (300308)', amt: 'reduce',    reason: '单只占比 11.07% 超 8% 阈值' },
];

const HIST_META = {
  add:    { c: TOKENS.bull,    label: '加仓', icon: '+' },
  reduce: { c: TOKENS.neutral, label: '减仓', icon: '−' },
  macro:  { c: TOKENS.accent,  label: '宏观', icon: '◆' },
  alert:  { c: TOKENS.bear,    label: '预警', icon: '⚠' },
};

function HistoryTimeline() {
  const W = 1180;
  const minDay = -30, maxDay = 1;
  const xAt = (day) => 80 + ((day - minDay) / (maxDay - minDay)) * (W - 100);
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>再平衡历史 · 30 天</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>{HISTORY.length} 起事件 · 包含 1 起宏观切换 · 2 起预警</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {Object.entries(HIST_META).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 11, color: TOKENS.textMuted }}>
              <span style={{ color: v.c }}>{v.icon}</span> {v.label}
            </div>
          ))}
        </div>
      </div>
      <svg width={W} height={140} style={{ display: 'block' }}>
        {/* axis */}
        <line x1={60} x2={W - 20} y1={70} y2={70} stroke={TOKENS.border} />
        {/* day ticks */}
        {[-30, -25, -20, -15, -10, -5, 0].map(d => {
          const x = xAt(d);
          return (
            <g key={d}>
              <line x1={x} x2={x} y1={66} y2={74} stroke={TOKENS.borderStrong} />
              <text x={x} y={90} fontSize="10" fill={TOKENS.textDim} textAnchor="middle" fontFamily="JetBrains Mono">
                {d === 0 ? '今天' : `${d}d`}
              </text>
            </g>
          );
        })}
        {/* events */}
        {HISTORY.map((e, i) => {
          const m = HIST_META[e.type];
          const x = xAt(e.day);
          const above = i % 2 === 0;
          const lineY = above ? 18 : 122;
          const boxY = above ? 4 : 108;
          return (
            <g key={i}>
              <line x1={x} y1={70} x2={x} y2={above ? 30 : 110} stroke={m.c} strokeWidth="1" strokeDasharray="2 2" />
              <circle cx={x} cy={70} r="6" fill={m.c} stroke={TOKENS.surface} strokeWidth="2" />
              <circle cx={x} cy={70} r="3" fill="#fff" />
              {/* label box */}
              <foreignObject x={x - 90} y={boxY} width={180} height={32}>
                <div style={{
                  background: `${m.c}1A`,
                  border: `1px solid ${m.c}55`,
                  borderLeft: `2px solid ${m.c}`,
                  borderRadius: 4,
                  padding: '4px 6px',
                  fontSize: 10,
                  color: TOKENS.text,
                  lineHeight: 1.25,
                  fontFamily: '"Noto Sans SC", sans-serif',
                  textAlign: 'left',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 4 }}>
                    <span style={{ fontWeight: 600, color: m.c, fontSize: 9 }}>{m.icon} {m.label}</span>
                    <span style={{ fontSize: 9, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>{e.d.slice(5)}</span>
                  </div>
                  <div style={{ fontSize: 10, color: TOKENS.text, marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.stock}</div>
                </div>
              </foreignObject>
            </g>
          );
        })}
      </svg>
      {/* below: legend table */}
      <div style={{ marginTop: 10, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}` }}>
        <div style={{ display: 'grid', gridTemplateColumns: '80px 60px 220px 110px 1fr', gap: 8, fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.05em', textTransform: 'uppercase', fontFamily: 'JetBrains Mono, monospace', paddingBottom: 6, borderBottom: `1px solid ${TOKENS.border}` }}>
          <span>日期</span><span>类型</span><span>标的</span><span>动作</span><span>原因</span>
        </div>
        {HISTORY.slice().reverse().map((e, i) => {
          const m = HIST_META[e.type];
          return (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '80px 60px 220px 110px 1fr', gap: 8, alignItems: 'center', padding: '6px 0', borderBottom: `1px dashed ${TOKENS.border}`, fontSize: 12 }}>
              <Mono style={{ color: TOKENS.textMuted, fontSize: 11 }}>{e.d}</Mono>
              <span style={{ fontSize: 10, color: m.c, background: `${m.c}1A`, border: `1px solid ${m.c}44`, padding: '1px 6px', borderRadius: 3, fontWeight: 600, width: 'fit-content' }}>{m.icon} {m.label}</span>
              <span style={{ color: TOKENS.text }}>{e.stock}</span>
              <Mono style={{ fontSize: 11, color: m.c, fontWeight: 600 }}>{e.amt}</Mono>
              <span style={{ fontSize: 11, color: TOKENS.textMuted }}>{e.reason}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// =========== TAB 4 ROOT ===========
function Tab4SignalDashboard() {
  const tabs = ['持仓总览', '每日策略简报', '个股深度分析', '信号仪表盘'];
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 18 }}>
        <div>
          <Mono style={{ fontSize: 11, color: TOKENS.textDim, letterSpacing: '0.16em' }}>MY-INVEST-GLOBAL · TAB 04</Mono>
          <div style={{ fontSize: 28, fontWeight: 600, marginTop: 4, letterSpacing: '-0.01em' }}>信号仪表盘</div>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginTop: 4 }}>宏观 · 板块 · 仓位 · 历史 — 时寒冰方法论实时映射</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Mono style={{ fontSize: 11, color: TOKENS.textDim }}>macro_state.json: <span style={{ color: TOKENS.bull }}>green</span></Mono>
          <button style={{
            background: 'transparent',
            color: TOKENS.textMuted,
            border: `1px solid ${TOKENS.border}`,
            padding: '6px 12px',
            borderRadius: 6,
            fontFamily: 'inherit',
            fontSize: 11,
            cursor: 'pointer',
          }}>手动覆盖宏观状态</button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ marginBottom: 16 }}>
        <div style={{
          display: 'flex',
          background: TOKENS.surface,
          border: `1px solid ${TOKENS.border}`,
          borderRadius: 8,
          overflow: 'hidden',
        }}>
          {tabs.map((t, i) => (
            <div key={t} style={{
              padding: '12px 22px',
              fontSize: 13,
              fontWeight: i === 3 ? 600 : 400,
              color: i === 3 ? TOKENS.text : TOKENS.textMuted,
              borderBottom: i === 3 ? `2px solid ${TOKENS.accent}` : '2px solid transparent',
              background: i === 3 ? 'rgba(79,142,247,0.06)' : 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{ color: i === 3 ? TOKENS.accent : TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>0{i + 1}</span>
              {t}
            </div>
          ))}
          <div style={{ flex: 1 }} />
        </div>
      </div>

      <div style={{ display: 'grid', gap: 12 }}>
        <MacroCyclePanel />
        <ScarcityMatrix />
        <RebalanceTriggers />
        <HistoryTimeline />
      </div>

      <div style={{ marginTop: 18, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
        <span>稀缺矩阵源自 methodology.md §2 · 触发器源自 §5.3 信号灯框架</span>
        <span>engine/macro_gate.py · engine/portfolio.py · 缓存 2026-05-17 14:32:08</span>
      </div>
    </div>
  );
}

Object.assign(window, { Tab4SignalDashboard });
