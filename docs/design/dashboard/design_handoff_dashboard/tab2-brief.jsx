/* global React, TOKENS, SIGNAL, Card, Mono, SignalBadge, Tag, HOLDINGS */
const { useState } = React;

// =========== US LEADING DATA ===========
const US_STOCKS = [
  { sym: 'NVDA', name: 'NVIDIA',         pct:  +2.84, price: 1182.40, vol: '74.2M' },
  { sym: 'AVGO', name: 'Broadcom',       pct:  +1.92, price: 1641.20, vol: '12.8M' },
  { sym: 'VRT',  name: 'Vertiv',         pct:  +3.51, price:  124.85, vol:  '9.4M' },
  { sym: 'ANET', name: 'Arista',         pct:  -0.74, price:  386.10, vol:  '4.1M' },
  { sym: 'MU',   name: 'Micron',         pct:  -1.85, price:  108.74, vol: '21.7M' },
];

const CAPEX_STATE = {
  type: 'growth', // 'growth' | 'flat' | 'shrink'
  label: '增长期',
  desc: 'AI 基建 CapEx 连续 4 季度同比 >+25% · 光通信 / HBM 供给紧张',
  color: TOKENS.bull,
  dot: '🟢',
};

// =========== TOP BANNER ===========
function MacroBanner() {
  return (
    <div style={{
      background: `linear-gradient(135deg, ${TOKENS.surface} 0%, #1a2533 100%)`,
      border: `1px solid ${CAPEX_STATE.color}33`,
      borderLeft: `3px solid ${CAPEX_STATE.color}`,
      borderRadius: 8,
      padding: '16px 20px',
      display: 'flex',
      alignItems: 'center',
      gap: 24,
    }}>
      {/* Pill */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '10px 18px',
        background: `${CAPEX_STATE.color}1F`,
        border: `1px solid ${CAPEX_STATE.color}66`,
        borderRadius: 999,
      }}>
        <span style={{ fontSize: 18 }}>{CAPEX_STATE.dot}</span>
        <div>
          <div style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.1em' }}>美股 AI CAPEX 周期</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: CAPEX_STATE.color, lineHeight: 1 }}>{CAPEX_STATE.label}</div>
        </div>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: TOKENS.text, lineHeight: 1.4 }}>{CAPEX_STATE.desc}</div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim, marginTop: 4, display: 'block' }}>
          状态切换阈值: 平稳期 if YoY ∈ [+10%, +25%]  ·  收缩期 if YoY &lt; +10%
        </Mono>
      </div>
      {/* Overnight chips */}
      <div style={{ display: 'flex', gap: 8 }}>
        {US_STOCKS.map(s => {
          const isPos = s.pct >= 0;
          const c = isPos ? TOKENS.bull : TOKENS.bear;
          return (
            <div key={s.sym} style={{
              padding: '6px 10px',
              background: `${c}1A`,
              border: `1px solid ${c}40`,
              borderRadius: 4,
              minWidth: 76,
              textAlign: 'center',
            }}>
              <Mono style={{ fontSize: 10, color: TOKENS.textMuted, display: 'block' }}>{s.sym}</Mono>
              <Mono style={{ fontSize: 13, fontWeight: 600, color: c, display: 'block', lineHeight: 1.2 }}>
                {isPos ? '+' : ''}{s.pct.toFixed(2)}%
              </Mono>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// =========== STRATEGY BRIEF (COLLAPSIBLE) ===========
const BRIEF_SECTIONS = [
  {
    icon: '📊',
    title: '市场判断',
    summary: '光通信链短期强势延续，半导体链分化',
    color: TOKENS.accent,
    body: (
      <div style={{ display: 'grid', gap: 10, fontSize: 13, lineHeight: 1.6 }}>
        <p style={{ margin: 0 }}>
          隔夜美股 AI 链整体偏强：<Mono style={{ color: TOKENS.bull }}>NVDA +2.84% · AVGO +1.92% · VRT +3.51%</Mono>，
          光模块需求确认延续，A 股映射板块 <strong>预计高开 1.5–2.5%</strong>。
        </p>
        <p style={{ margin: 0 }}>
          上证 BBI 上穿确认日线偏多结构，连续 5 日预测 <Mono style={{ color: TOKENS.bull }}>4/5 偏涨</Mono>，
          但 <Mono style={{ color: TOKENS.bear }}>MU -1.85%</Mono> 提示存储芯片短期承压，存储芯片(国产替代)需观察今日量能。
        </p>
        <p style={{ margin: 0, color: TOKENS.textMuted }}>
          策略建议：以"持有为主，弱者减仓"应对，光通信龙头出现 +20% 浮盈个股可分批了结 1/3 仓位。
        </p>
      </div>
    ),
  },
  {
    icon: '📋',
    title: '个股操作',
    summary: '6 条操作建议 · 1 减仓 · 3 持有加仓 · 2 持有',
    color: TOKENS.neutral,
    body: (
      <div style={{ display: 'grid', gap: 0, fontSize: 13 }}>
        {[
          { sig: 'reduce',    s: '中际旭创', c: '300308', txt: '占比 11.07% 超阈值 +3%, 减至 8% 以内, 释放约 ¥28,000', tone: 'bear' },
          { sig: 'hold_add',  s: '中芯国际', c: '688981', txt: '回调至 60 日均线 + 国产替代催化, 加仓 1/3 至目标 6%', tone: 'bull' },
          { sig: 'hold_add',  s: '景嘉微',   c: '300474', txt: '算力涨价预期持续, 当前占比 3.07% 低于目标, 补足至 5%', tone: 'bull' },
          { sig: 'hold_add',  s: '美的集团', c: '000333', txt: '白马股+家电出口超预期, 加仓至目标 10%', tone: 'bull' },
          { sig: 'hold',      s: '中航光电', c: '002179', txt: '已持仓充分, +12.4% 浮盈, 持有观察 PB 估值', tone: 'neutral' },
          { sig: 'hold',      s: '海康威视', c: '002415', txt: '占比偏高 (23%), 不加仓不减仓, 等待目标价 ¥35', tone: 'neutral' },
        ].map((r, i) => (
          <div key={i} style={{
            display: 'grid',
            gridTemplateColumns: '90px 130px 1fr',
            gap: 12,
            alignItems: 'center',
            padding: '10px 0',
            borderTop: i > 0 ? `1px dashed ${TOKENS.border}` : 'none',
          }}>
            <SignalBadge type={r.sig} size="sm" />
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ fontWeight: 500 }}>{r.s}</span>
              <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{r.c}</Mono>
            </div>
            <div style={{ color: TOKENS.textMuted, fontSize: 12 }}>{r.txt}</div>
          </div>
        ))}
      </div>
    ),
  },
  {
    icon: '⚠',
    title: '风险提示',
    summary: '2 条止损 / 止盈预警',
    color: TOKENS.bear,
    body: (
      <div style={{ display: 'grid', gap: 10 }}>
        <AlertBox type="danger" title="止损监控 · 中芯国际 (688981)" body="当前盈亏 -3.5%。若下一交易日跌破 ¥58.40 (持仓成本 -8%), 触发止损单, 强制清仓。" />
        <AlertBox type="warn"   title="止盈提示 · 中际旭创 (300308)" body="盈亏 +18.59%, 已接近第一目标位 +20%。建议设置移动止盈, 跌破日内 5 日 EMA 减仓 1/3。" />
        <AlertBox type="info"   title="行业观察 · 存储芯片" body="MU 隔夜 -1.85%, HBM 价格周指数 -0.4%。若持仓含存储芯片标的, 注意明日开盘 30 分钟量价。" />
      </div>
    ),
  },
];

function AlertBox({ type, title, body }) {
  const cfg = {
    danger: { c: TOKENS.bear,    bg: 'rgba(232,64,64,0.08)',   bd: 'rgba(232,64,64,0.4)',   ic: '⛔' },
    warn:   { c: TOKENS.neutral, bg: 'rgba(245,166,35,0.08)',  bd: 'rgba(245,166,35,0.4)',  ic: '⚠'  },
    info:   { c: TOKENS.accent,  bg: 'rgba(79,142,247,0.06)',  bd: 'rgba(79,142,247,0.3)',  ic: 'ⓘ'  },
  }[type];
  return (
    <div style={{
      background: cfg.bg,
      border: `1px solid ${cfg.bd}`,
      borderLeft: `3px solid ${cfg.c}`,
      borderRadius: 6,
      padding: '10px 14px',
      display: 'grid',
      gridTemplateColumns: '24px 1fr',
      gap: 10,
      alignItems: 'flex-start',
    }}>
      <div style={{ color: cfg.c, fontSize: 16, lineHeight: 1.2 }}>{cfg.ic}</div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: cfg.c, marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 12, color: TOKENS.text, lineHeight: 1.5 }}>{body}</div>
      </div>
    </div>
  );
}

function StrategyBrief() {
  const [open, setOpen] = useState([true, true, true]); // open all by default for design viewing
  return (
    <Card pad={0}>
      <div style={{ padding: '14px 18px', borderBottom: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>LLM 策略简报</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>每日 08:30 自动生成 · 基于 GPT-4 + 内部因子模型</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>生成于 2026-05-17 08:31:42</Mono>
          <Tag tone="bull">实时可用</Tag>
        </div>
      </div>
      {BRIEF_SECTIONS.map((s, i) => (
        <div key={s.title} style={{ borderTop: i > 0 ? `1px solid ${TOKENS.border}` : 'none' }}>
          <button
            onClick={() => setOpen(o => o.map((v, j) => j === i ? !v : v))}
            style={{
              width: '100%',
              display: 'grid',
              gridTemplateColumns: '32px 1fr auto',
              gap: 12,
              alignItems: 'center',
              padding: '14px 18px',
              background: 'transparent',
              border: 'none',
              color: TOKENS.text,
              fontFamily: 'inherit',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <span style={{ fontSize: 18 }}>{s.icon}</span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: s.color }}>{s.title}</div>
              <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>{s.summary}</div>
            </div>
            <div style={{
              width: 22, height: 22, borderRadius: 4,
              background: 'rgba(255,255,255,0.05)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: TOKENS.textMuted, fontSize: 12,
              transform: open[i] ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 160ms',
            }}>▾</div>
          </button>
          {open[i] && (
            <div style={{ padding: '0 18px 18px 62px' }}>
              {s.body}
            </div>
          )}
        </div>
      ))}
    </Card>
  );
}

// =========== SIGNAL SCORE TABLE ===========
const SCORE_ROWS = [
  { stock: '中际旭创', code: '300308', cat: '弹性·光通信',  A: 78, B: 82, C: 88, sig: 'reduce',     note: '占比超阈, 估值偏高' },
  { stock: '中航光电', code: '002179', cat: '弹性·光通信',  A: 71, B: 76, C: 70, sig: 'hold',       note: '+12.4% 浮盈, 观察' },
  { stock: '中芯国际', code: '688981', cat: '弹性·半导体',  A: 58, B: 84, C: 65, sig: 'hold_add',   note: '国产替代催化' },
  { stock: '景嘉微',   code: '300474', cat: '弹性·算力',    A: 62, B: 70, C: 75, sig: 'hold_add',   note: '位低占比, 补足' },
  { stock: '海康威视', code: '002415', cat: '白马·安防',    A: 65, B: 80, C: 60, sig: 'hold',       note: '位置已足, 不动' },
  { stock: '贵州茅台', code: '600519', cat: '白马·白酒',    A: 55, B: 88, C: 50, sig: 'hold',       note: '基本面稳, 弱势' },
  { stock: '美的集团', code: '000333', cat: '白马·家电',    A: 72, B: 78, C: 68, sig: 'hold_add',   note: '出口超预期' },
  { stock: '招商银行', code: '600036', cat: '白马·银行',    A: 42, B: 70, C: 45, sig: 'hold',       note: '低位震荡' },
  { stock: 'TCL中环',  code: '002129', cat: '弹性·半导体',  A: 38, B: 35, C: 28, sig: 'stop_loss',  note: '光伏链景气下行' },
];

function ScoreBar({ value, weight, color }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '38px 1fr', gap: 8, alignItems: 'center' }}>
      <Mono style={{ fontSize: 13, fontWeight: 600, color: TOKENS.text, textAlign: 'right' }}>{value}</Mono>
      <div style={{ position: 'relative', height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 2 }}>
        <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${value}%`, background: color, borderRadius: 2 }} />
      </div>
    </div>
  );
}

function ScoreTable() {
  return (
    <Card pad={0}>
      <div style={{ padding: '14px 18px', borderBottom: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>信号评分矩阵</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>
            综合分 = 技术 A × 30% + 基本面 B × 40% + 情绪 C × 30% · 阈值: ≥75 strong_add · 60~75 hold_add · 45~60 hold · 30~45 reduce · &lt;30 stop_loss
          </div>
        </div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{SCORE_ROWS.length} 行 · 1 止损覆盖</Mono>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: TOKENS.surfaceAlt }}>
            <th style={tStyle('left', 240)}>股票</th>
            <th style={tStyle('left', 180)}>技术 A <span style={{ color: TOKENS.textDim }}>· 30%</span></th>
            <th style={tStyle('left', 180)}>基本面 B <span style={{ color: TOKENS.textDim }}>· 40%</span></th>
            <th style={tStyle('left', 180)}>情绪 C <span style={{ color: TOKENS.textDim }}>· 30%</span></th>
            <th style={tStyle('right')}>综合分</th>
            <th style={tStyle('left', 130)}>操作建议</th>
            <th style={tStyle('left')}>备注</th>
          </tr>
        </thead>
        <tbody>
          {SCORE_ROWS.map(r => {
            const composite = r.A * 0.3 + r.B * 0.4 + r.C * 0.3;
            const isStop = r.sig === 'stop_loss';
            return (
              <tr key={r.code} style={{
                background: isStop ? 'rgba(232,64,64,0.12)' : 'transparent',
                borderTop: `1px solid ${TOKENS.border}`,
              }}>
                <td style={cellStyle()}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                    <span style={{ fontWeight: 500, color: isStop ? TOKENS.bear : TOKENS.text }}>{r.stock}</span>
                    <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{r.code}</Mono>
                  </div>
                  <div style={{ fontSize: 10, color: TOKENS.textMuted, marginTop: 2 }}>{r.cat}</div>
                </td>
                <td style={cellStyle()}><ScoreBar value={r.A} color={scoreColor(r.A)} /></td>
                <td style={cellStyle()}><ScoreBar value={r.B} color={scoreColor(r.B)} /></td>
                <td style={cellStyle()}><ScoreBar value={r.C} color={scoreColor(r.C)} /></td>
                <td style={cellStyle('right')}>
                  <Mono style={{ fontSize: 18, fontWeight: 600, color: scoreColor(composite) }}>
                    {composite.toFixed(1)}
                  </Mono>
                </td>
                <td style={cellStyle()}><SignalBadge type={r.sig} size="sm" /></td>
                <td style={cellStyle()}>
                  <span style={{ fontSize: 12, color: isStop ? TOKENS.bear : TOKENS.textMuted }}>{r.note}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function scoreColor(v) {
  if (v >= 75) return TOKENS.bull;
  if (v >= 60) return TOKENS.accent;
  if (v >= 45) return '#9AA0AC';
  if (v >= 30) return TOKENS.neutral;
  return TOKENS.bear;
}
function tStyle(align = 'left', w) {
  return {
    textAlign: align,
    padding: '10px 14px',
    fontWeight: 500,
    fontSize: 10,
    color: TOKENS.textMuted,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    fontFamily: 'JetBrains Mono, monospace',
    width: w,
  };
}
function cellStyle(align = 'left') {
  return { textAlign: align, padding: '11px 14px', fontSize: 13, verticalAlign: 'middle' };
}

// =========== US LEADING BAR CHART ===========
function USLeadingChart() {
  const maxAbs = Math.max(...US_STOCKS.map(s => Math.abs(s.pct)));
  const scale = 1 / (maxAbs * 1.15); // 0..1
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>隔夜美股先行指标</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>NVDA · AVGO · VRT · ANET · MU — A 股映射板块定向参考</div>
        </div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>截至 2026-05-17 05:00 ET</Mono>
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {US_STOCKS.map(s => {
          const isPos = s.pct >= 0;
          const c = isPos ? TOKENS.bull : TOKENS.bear;
          const widthPct = Math.abs(s.pct) * scale * 50; // half of 100%
          return (
            <div key={s.sym} style={{
              display: 'grid',
              gridTemplateColumns: '70px 110px 1fr 100px',
              alignItems: 'center',
              gap: 10,
            }}>
              <Mono style={{ fontSize: 13, fontWeight: 600 }}>{s.sym}</Mono>
              <div style={{ fontSize: 11, color: TOKENS.textMuted }}>{s.name}</div>
              {/* bar with center axis */}
              <div style={{ position: 'relative', height: 22, background: TOKENS.surfaceAlt, borderRadius: 3 }}>
                {/* center line */}
                <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: 'rgba(255,255,255,0.18)' }} />
                {/* bar */}
                <div style={{
                  position: 'absolute',
                  top: 3,
                  bottom: 3,
                  left: isPos ? '50%' : `calc(50% - ${widthPct}%)`,
                  width: `${widthPct}%`,
                  background: `linear-gradient(90deg, ${c}88, ${c})`,
                  borderRadius: 2,
                }} />
                {/* value label */}
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  left: isPos ? `calc(50% + ${widthPct}% + 8px)` : `calc(50% - ${widthPct}% - 8px)`,
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 12,
                  fontWeight: 600,
                  color: c,
                  whiteSpace: 'nowrap',
                  ...(isPos ? {} : { transform: 'translate(-100%, -50%)' }),
                }}>
                  {isPos ? '+' : ''}{s.pct.toFixed(2)}%
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Mono style={{ fontSize: 12, color: TOKENS.text, display: 'block' }}>${s.price.toFixed(2)}</Mono>
                <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>VOL {s.vol}</Mono>
              </div>
            </div>
          );
        })}
      </div>
      {/* footer interpretation */}
      <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <MiniStat label="平均涨跌" value="+1.14%" tone="bull" />
        <MiniStat label="涨家数" value="3 / 5" sub="NVDA · AVGO · VRT" tone="bull" />
        <MiniStat label="跌家数" value="2 / 5" sub="ANET · MU" tone="bear" />
      </div>
    </Card>
  );
}

function MiniStat({ label, value, sub, tone }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : TOKENS.text;
  return (
    <div>
      <div style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.06em' }}>{label}</div>
      <Mono style={{ fontSize: 16, fontWeight: 600, color: c, display: 'block', marginTop: 2 }}>{value}</Mono>
      {sub && <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{sub}</Mono>}
    </div>
  );
}

// =========== A股映射板块预期 (companion to US chart) ===========
function MappingPanel() {
  const map = [
    { us: 'NVDA · AVGO',  cn: '光通信',   stocks: '300308 · 002179', expect: '+1.8% ~ +2.5%', tone: 'bull' },
    { us: 'VRT',          cn: '电源 / 液冷', stocks: '300472 · 002615', expect: '+1.5% ~ +2.2%', tone: 'bull' },
    { us: 'ANET',         cn: '交换机',   stocks: '300383 · 002916', expect: '-0.2% ~ +0.3%',  tone: 'neutral' },
    { us: 'MU',           cn: '存储芯片', stocks: '688008 · 002156', expect: '-1.0% ~ -1.5%', tone: 'bear' },
  ];
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>A 股映射板块预期</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>基于隔夜美股 + 历史相关性的开盘 30 分钟区间预测</div>
        </div>
        <Tag>开盘 09:30</Tag>
      </div>
      <div style={{ display: 'grid', gap: 0 }}>
        {map.map((m, i) => {
          const c = m.tone === 'bull' ? TOKENS.bull : m.tone === 'bear' ? TOKENS.bear : TOKENS.neutral;
          return (
            <div key={i} style={{
              display: 'grid',
              gridTemplateColumns: '110px 110px 1fr 120px',
              gap: 12,
              padding: '10px 0',
              borderTop: i > 0 ? `1px dashed ${TOKENS.border}` : 'none',
              alignItems: 'center',
            }}>
              <Mono style={{ fontSize: 12, fontWeight: 600 }}>{m.us}</Mono>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 10, color: TOKENS.textDim }}>→</span>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{m.cn}</span>
              </div>
              <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>{m.stocks}</Mono>
              <Mono style={{ fontSize: 13, fontWeight: 600, color: c, textAlign: 'right' }}>{m.expect}</Mono>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// =========== TAB 2 ROOT ===========
function Tab2DailyBrief() {
  const tabs = ['持仓总览', '每日策略简报', '行业概览', '信号建议'];
  return (
    <div style={{
      width: 1280,
      background: TOKENS.bg,
      color: TOKENS.text,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      padding: 28,
      boxSizing: 'border-box',
    }}>
      {/* Page header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 18 }}>
        <div>
          <Mono style={{ fontSize: 11, color: TOKENS.textDim, letterSpacing: '0.16em' }}>MY-INVEST-GLOBAL · TAB 02</Mono>
          <div style={{ fontSize: 28, fontWeight: 600, marginTop: 4, letterSpacing: '-0.01em' }}>每日策略简报</div>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginTop: 4 }}>2026-05-17 周日 · 收盘后 · 下个交易日 2026-05-18 (周一)</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Mono style={{ fontSize: 11, color: TOKENS.textDim }}>下次刷新 05-18 08:30</Mono>
          <button style={{
            background: TOKENS.accent,
            color: '#fff',
            border: 'none',
            padding: '8px 14px',
            borderRadius: 6,
            fontFamily: 'inherit',
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
          }}>↻ 立即重生成</button>
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
              fontWeight: i === 1 ? 600 : 400,
              color: i === 1 ? TOKENS.text : TOKENS.textMuted,
              borderBottom: i === 1 ? `2px solid ${TOKENS.accent}` : '2px solid transparent',
              background: i === 1 ? 'rgba(79,142,247,0.06)' : 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{ color: i === 1 ? TOKENS.accent : TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>0{i + 1}</span>
              {t}
            </div>
          ))}
          <div style={{ flex: 1 }} />
          <div style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: TOKENS.bull }} />
              LLM · GPT-4 ready
            </span>
          </div>
        </div>
      </div>

      {/* 1. Macro banner */}
      <div style={{ marginBottom: 12 }}>
        <MacroBanner />
      </div>

      {/* 2. Strategy brief */}
      <div style={{ marginBottom: 12 }}>
        <StrategyBrief />
      </div>

      {/* 3. Score table */}
      <div style={{ marginBottom: 12 }}>
        <ScoreTable />
      </div>

      {/* 4. US leading + mapping */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 12 }}>
        <USLeadingChart />
        <MappingPanel />
      </div>

      {/* footer */}
      <div style={{ marginTop: 18, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
        <span>本简报为算法 + LLM 产出 · 仅供个人投资参考 · 不构成投资建议</span>
        <span>模型 GPT-4 · 因子模型 v2.3 · 缓存 2026-05-17 08:31:42</span>
      </div>
    </div>
  );
}

Object.assign(window, { Tab2DailyBrief, US_STOCKS, CAPEX_STATE });
