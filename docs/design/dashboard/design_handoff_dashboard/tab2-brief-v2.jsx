/* global React, TOKENS, Card, Mono, Tag, SignalBadge, GlobalActionBar, US_STOCKS, CAPEX_STATE */
const { useState: useT2V2 } = React;

// =========== MACRO BANNER (50/50 split) ===========
const MACRO_TRAFFIC = [
  { key: 'green',  label: '扩张', color: TOKENS.bull },
  { key: 'yellow', label: '观望', color: TOKENS.neutral },
  { key: 'red',    label: '收缩', color: TOKENS.bear },
];

function MacroBannerV2() {
  const activeKey = 'yellow';
  const active = MACRO_TRAFFIC.find(t => t.key === activeKey);

  return (
    <Card pad={16}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* LEFT 50%: traffic light + summary */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
            <Mono style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.08em', marginRight: 4 }}>美股 AI CAPEX 周期</Mono>
            {MACRO_TRAFFIC.map(t => {
              const isActive = t.key === activeKey;
              return (
                <span key={t.key} style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '4px 10px',
                  background: isActive ? `${t.color}26` : 'transparent',
                  border: `1px solid ${isActive ? t.color + '88' : TOKENS.border}`,
                  color: isActive ? t.color : TOKENS.textMuted,
                  borderRadius: 999,
                  fontSize: 11,
                  fontWeight: isActive ? 600 : 400,
                  boxShadow: isActive ? `0 0 12px ${t.color}33` : 'none',
                }}>
                  <span style={{
                    width: 6, height: 6,
                    borderRadius: '50%',
                    background: t.color,
                    boxShadow: isActive ? `0 0 5px ${t.color}` : 'none',
                  }} />
                  {t.label}
                </span>
              );
            })}
          </div>
          <div style={{ fontSize: 12, color: TOKENS.text, lineHeight: 1.55, marginBottom: 8 }}>
            四大云厂商 CapEx 同比 <Mono style={{ color: TOKENS.bull }}>+48%</Mono>，光通信链供需仍紧张；
            <Mono style={{ color: TOKENS.bear }}>MU -1.85%</Mono> 存储芯片短期承压，板块分化加剧。
          </div>
          <Mono style={{ fontSize: 10, color: TOKENS.textDim, letterSpacing: '0.04em' }}>
            阶段持续 47 天 · 弹性目标 33% · 单仓阈值 8%
          </Mono>
        </div>

        {/* RIGHT 50%: US chips */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
            <Mono style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.08em' }}>隔夜美股 · A 股映射先行指标</Mono>
            <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>更新于 05-20 05:00 ET</Mono>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
            {[
              { sym: 'NVDA', pct:  2.84 },
              { sym: 'AVGO', pct:  1.92 },
              { sym: 'VRT',  pct:  3.51 },
              { sym: 'ANET', pct: -0.74 },
              { sym: 'MU',   pct: -1.85 },
            ].map(s => {
              const pos = s.pct >= 0;
              const c = pos ? TOKENS.bull : TOKENS.bear;
              return (
                <div key={s.sym} style={{
                  padding: '8px 10px',
                  background: `${c}14`,
                  border: `1px solid ${c}40`,
                  borderRadius: 5,
                  textAlign: 'center',
                }}>
                  <Mono style={{ fontSize: 10, color: TOKENS.textMuted, display: 'block', marginBottom: 2 }}>{s.sym}</Mono>
                  <Mono style={{ fontSize: 14, fontWeight: 600, color: c, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
                    {pos ? '↑' : '↓'} {Math.abs(s.pct).toFixed(2)}%
                  </Mono>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Card>
  );
}

// =========== COLLAPSIBLE BRIEF ===========
const BRIEF_V2_SECTIONS = [
  {
    icon: '📊',
    title: '市场判断',
    sigBadge: { tone: 'bull', text: '偏多' },
    summary: '光通信链短期强势 · 半导体链分化',
    body: (
      <div style={{ fontSize: 13, lineHeight: 1.7, color: TOKENS.text }}>
        <p style={{ margin: '0 0 10px' }}>
          隔夜美股 AI 链整体偏强 (NVDA / AVGO / VRT 均涨)，光模块需求延续；
          A 股映射板块 <strong>预计高开 1.5–2.5%</strong>。
          上证 BBI 上穿确认日线偏多结构。
        </p>
        <p style={{ margin: 0, color: TOKENS.textMuted }}>
          策略：以"持有为主、弱者减仓"应对；光通信浮盈 &gt;+20% 可分批了结 1/3 仓位。
        </p>
      </div>
    ),
  },
  {
    icon: '📋',
    title: '个股操作',
    sigBadge: { tone: 'neutral', text: '6 项操作' },
    summary: '1 减仓 · 3 加仓 · 2 观望',
    body: (
      <div style={{ display: 'grid', gap: 0 }}>
        {[
          { sig: 'reduce',   s: '中际旭创', c: '300308', txt: '占比 11.07% 超阈值 +3%, 减至 8% 以内', t1: 'all_available' },
          { sig: 'hold_add', s: '中芯国际', c: '688981', txt: '回调至 60 日均线 · 加仓 1/3 至目标 6%', t1: 'partial' },
          { sig: 'hold_add', s: '景嘉微',   c: '300474', txt: '算力涨价预期持续 · 补足至 5%', t1: 'bought_today' },
          { sig: 'hold_add', s: '美的集团', c: '000333', txt: '家电出口超预期 · 加仓至目标 10%', t1: 'all_available' },
          { sig: 'hold',     s: '中航光电', c: '002179', txt: '+12.4% 浮盈 · 持有观察 PB 估值', t1: 'all_available' },
          { sig: 'hold',     s: '海康威视', c: '002415', txt: '占比偏高 (23%) · 等待目标价 ¥35', t1: 'all_available' },
        ].map((r, i) => (
          <div key={i} style={{
            display: 'grid',
            gridTemplateColumns: '94px 130px 1fr 100px',
            gap: 12,
            alignItems: 'center',
            padding: '10px 0',
            borderTop: i > 0 ? `1px dashed ${TOKENS.border}` : 'none',
          }}>
            <SignalBadge type={r.sig} size="sm" />
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ fontWeight: 500, fontSize: 13 }}>{r.s}</span>
              <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{r.c}</Mono>
            </div>
            <div style={{ color: TOKENS.textMuted, fontSize: 12 }}>{r.txt}</div>
            <div style={{ textAlign: 'right' }}>
              {r.t1 === 'bought_today' && <T1Inline tone="neutral" label="T+1 锁仓" />}
              {r.t1 === 'partial'      && <T1Inline tone="bull"    label="部分可用" />}
              {r.t1 === 'all_available' && <T1Inline tone="bull"   label="可执行" />}
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    icon: '⚠',
    title: '风险提示',
    sigBadge: { tone: 'bear', text: '2 项止损 / 1 止盈' },
    summary: '存储芯片承压 · 1 个止损监控',
    body: (
      <div style={{ display: 'grid', gap: 10 }}>
        <AlertBoxV2 type="danger" stock="中芯国际 (688981)" body="当前盈亏 -3.5%。若下一交易日跌破 ¥58.40 (持仓成本 -8%)，触发止损单强制清仓。" />
        <AlertBoxV2 type="warn"   stock="中际旭创 (300308)" body="盈亏 +18.59%，接近第一目标位 +20%。建议设置移动止盈：跌破日内 5 日 EMA 减仓 1/3。" />
        <AlertBoxV2 type="info"   stock="行业观察 · 存储芯片" body="MU 隔夜 -1.85%，HBM 周指数 -0.4%。明日开盘 30 分钟量价需观察。" />
      </div>
    ),
  },
];

function T1Inline({ tone, label }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'neutral' ? TOKENS.neutral : TOKENS.bear;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: '2px 7px',
      background: c + '1A',
      border: `1px solid ${c}44`,
      color: c,
      borderRadius: 3,
      fontSize: 10,
      fontWeight: 600,
    }}>
      <span style={{ width: 4, height: 4, borderRadius: '50%', background: c }} /> {label}
    </span>
  );
}

function AlertBoxV2({ type, stock, body }) {
  const cfg = {
    danger: { c: TOKENS.bear,    bg: 'rgba(232,64,64,0.08)',   bd: 'rgba(232,64,64,0.4)',   ic: '🔴' },
    warn:   { c: TOKENS.neutral, bg: 'rgba(245,166,35,0.08)',  bd: 'rgba(245,166,35,0.4)',  ic: '🟡' },
    info:   { c: TOKENS.accent,  bg: 'rgba(79,142,247,0.06)',  bd: 'rgba(79,142,247,0.3)',  ic: '🔵' },
  }[type];
  return (
    <div style={{
      background: cfg.bg,
      border: `1px solid ${cfg.bd}`,
      borderLeft: `3px solid ${cfg.c}`,
      borderRadius: 6,
      padding: '10px 14px',
      display: 'grid',
      gridTemplateColumns: '20px 1fr',
      gap: 10,
      alignItems: 'flex-start',
    }}>
      <div style={{ fontSize: 12, lineHeight: 1.4 }}>{cfg.ic}</div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: cfg.c, marginBottom: 4 }}>{stock}</div>
        <div style={{ fontSize: 12, color: TOKENS.text, lineHeight: 1.55 }}>{body}</div>
      </div>
    </div>
  );
}

function BriefV2() {
  const [open, setOpen] = useT2V2([true, true, true]);
  return (
    <Card pad={0}>
      <div style={{ padding: '12px 16px', borderBottom: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>LLM 策略简报</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>每日 08:30 自动生成 · 基于 GPT-4 + 内部因子模型</div>
        </div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>分析于 2026-05-20 08:31:42</Mono>
      </div>
      {BRIEF_V2_SECTIONS.map((s, i) => (
        <div key={s.title} style={{ borderTop: i > 0 ? `1px solid ${TOKENS.border}` : 'none' }}>
          <button
            onClick={() => setOpen(o => o.map((v, j) => j === i ? !v : v))}
            style={{
              width: '100%',
              display: 'grid',
              gridTemplateColumns: '28px 1fr auto 26px',
              gap: 10,
              alignItems: 'center',
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              color: TOKENS.text,
              fontFamily: 'inherit',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <span style={{ fontSize: 16 }}>{s.icon}</span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{s.title}</div>
              <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>{s.summary}</div>
            </div>
            <Tag tone={s.sigBadge.tone}>{s.sigBadge.text}</Tag>
            <span style={{
              fontSize: 12,
              color: TOKENS.textMuted,
              transform: open[i] ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 160ms',
            }}>▾</span>
          </button>
          {open[i] && (
            <div style={{ padding: '0 16px 16px 54px' }}>{s.body}</div>
          )}
        </div>
      ))}
    </Card>
  );
}

// =========== SIGNAL SCORE TABLE V2 (with 操作 column) ===========
const SCORE_V2_ROWS = [
  { stock: '中际旭创', code: '300308', cat: '弹性·光通信',  A: 78, B: 82, C: 88, sig: 'reduce' },
  { stock: '中航光电', code: '002179', cat: '弹性·光通信',  A: 71, B: 76, C: 70, sig: 'hold' },
  { stock: '中芯国际', code: '688981', cat: '弹性·半导体',  A: 58, B: 84, C: 65, sig: 'hold_add' },
  { stock: '景嘉微',   code: '300474', cat: '弹性·算力',    A: 62, B: 70, C: 75, sig: 'hold_add' },
  { stock: '美的集团', code: '000333', cat: '白马·家电',    A: 72, B: 78, C: 68, sig: 'hold_add' },
  { stock: '海康威视', code: '002415', cat: '白马·安防',    A: 65, B: 80, C: 60, sig: 'hold' },
  { stock: 'TCL中环',  code: '002129', cat: '弹性·半导体',  A: 38, B: 35, C: 28, sig: 'stop_loss' },
];

function scoreColorV2(v) {
  if (v >= 75) return TOKENS.bull;
  if (v >= 60) return TOKENS.accent;
  if (v >= 45) return '#9AA0AC';
  if (v >= 30) return TOKENS.neutral;
  return TOKENS.bear;
}

function ScoreBarV2({ value, color }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '32px 1fr', gap: 8, alignItems: 'center' }}>
      <Mono style={{ fontSize: 12, fontWeight: 600, textAlign: 'right' }}>{value}</Mono>
      <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2 }}>
        <div style={{ width: `${value}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
    </div>
  );
}

function ScoreTableV2() {
  return (
    <Card pad={0}>
      <div style={{
        padding: '12px 16px',
        borderBottom: `1px solid ${TOKENS.border}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>个股信号评分</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>
            综合 = 技术 30% + 基本面 40% + 情绪 30% · ≥75 强加 · 60–75 加 · 45–60 持 · 30–45 减 · &lt;30 止损
          </div>
        </div>
        <Mono style={{
          fontSize: 11,
          color: TOKENS.accent,
          textDecoration: 'underline',
          textDecorationStyle: 'dotted',
          cursor: 'pointer',
        }}>查看全部 →</Mono>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: TOKENS.surfaceAlt }}>
            <Tth>股票</Tth>
            <Tth>技术 A</Tth>
            <Tth>基本面 B</Tth>
            <Tth>情绪 C</Tth>
            <Tth align="right">综合</Tth>
            <Tth>建议</Tth>
            <Tth align="right">操作</Tth>
          </tr>
        </thead>
        <tbody>
          {SCORE_V2_ROWS.map(r => {
            const composite = r.A * 0.3 + r.B * 0.4 + r.C * 0.3;
            const isStop = r.sig === 'stop_loss';
            return (
              <tr key={r.code} style={{
                background: isStop ? 'rgba(232,64,64,0.12)' : 'transparent',
                borderTop: `1px solid ${TOKENS.border}`,
              }}>
                <Ttd>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span style={{ fontWeight: 500, color: isStop ? TOKENS.bear : TOKENS.text }}>{r.stock}</span>
                    <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{r.code}</Mono>
                  </div>
                  <div style={{ fontSize: 10, color: TOKENS.textMuted, marginTop: 1 }}>{r.cat}</div>
                </Ttd>
                <Ttd><ScoreBarV2 value={r.A} color={scoreColorV2(r.A)} /></Ttd>
                <Ttd><ScoreBarV2 value={r.B} color={scoreColorV2(r.B)} /></Ttd>
                <Ttd><ScoreBarV2 value={r.C} color={scoreColorV2(r.C)} /></Ttd>
                <Ttd align="right">
                  <Mono style={{ fontSize: 18, fontWeight: 600, color: scoreColorV2(composite) }}>{composite.toFixed(1)}</Mono>
                </Ttd>
                <Ttd><SignalBadge type={r.sig} size="sm" /></Ttd>
                <Ttd align="right">
                  <span style={{
                    fontSize: 11,
                    color: TOKENS.accent,
                    cursor: 'pointer',
                    fontWeight: 500,
                  }}>进入分析 →</span>
                </Ttd>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function Tth({ children, align = 'left' }) {
  return (
    <th style={{
      textAlign: align,
      padding: '9px 14px',
      fontWeight: 500,
      fontSize: 10,
      color: TOKENS.textMuted,
      letterSpacing: '0.06em',
      textTransform: 'uppercase',
      fontFamily: 'JetBrains Mono, monospace',
    }}>{children}</th>
  );
}
function Ttd({ children, align = 'left' }) {
  return (
    <td style={{
      textAlign: align,
      padding: '10px 14px',
      fontSize: 13,
      verticalAlign: 'middle',
    }}>{children}</td>
  );
}

// =========== T+1 REBALANCE SUMMARY BAR ===========
function T1RebalanceBar({ onJump }) {
  const cells = [
    { label: '今日可操作', value: '5 只', tone: 'text', icon: '✓' },
    { label: '建议减仓',   value: '1 只', tone: 'bear', icon: '↓', sub: '300308' },
    { label: '建议加仓',   value: '3 只', tone: 'bull', icon: '↑', sub: '688981 · 300474 · 000333' },
    { label: 'T+1 锁仓',   value: '1 只', tone: 'neutral', icon: '🔒', sub: '300474 今日买入' },
  ];
  return (
    <Card pad={0}>
      <div style={{ display: 'flex', alignItems: 'stretch' }}>
        {cells.map((cell, i) => {
          const c = cell.tone === 'bull' ? TOKENS.bull
                  : cell.tone === 'bear' ? TOKENS.bear
                  : cell.tone === 'neutral' ? TOKENS.neutral
                  : TOKENS.text;
          return (
            <div key={i} style={{
              flex: 1,
              padding: '14px 18px',
              borderRight: i < cells.length - 1 ? `1px solid ${TOKENS.border}` : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}>
              <div style={{
                width: 32, height: 32,
                background: c + '18',
                border: `1px solid ${c}44`,
                borderRadius: 6,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 14,
                color: c,
                flexShrink: 0,
              }}>{cell.icon}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.06em', marginBottom: 2 }}>{cell.label}</div>
                <Mono style={{ fontSize: 16, fontWeight: 600, color: c, display: 'block', lineHeight: 1.1 }}>{cell.value}</Mono>
                {cell.sub && <Mono style={{ fontSize: 9, color: TOKENS.textDim, marginTop: 2, display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{cell.sub}</Mono>}
              </div>
            </div>
          );
        })}
        {/* CTA */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          padding: '14px 18px',
          background: TOKENS.accent + '14',
          borderLeft: `1px solid ${TOKENS.accent}33`,
        }}>
          <button
            onClick={onJump}
            style={{
              background: TOKENS.accent,
              border: 'none',
              color: '#fff',
              padding: '10px 18px',
              borderRadius: 6,
              fontFamily: 'inherit',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            进入调仓分析 →
          </button>
        </div>
      </div>
    </Card>
  );
}

// =========== TAB 2 V2 ROOT ===========
function Tab2BriefV2() {
  return (
    <div style={{
      width: 1280,
      background: TOKENS.bg,
      color: TOKENS.text,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <GlobalActionBar activeTab={1} marketStatus="live" />

      <div style={{ padding: 24, boxSizing: 'border-box', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* ROW 1 — Page header (slim) */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          paddingBottom: 12,
          borderBottom: `1px solid ${TOKENS.border}`,
        }}>
          <div>
            <Mono style={{ fontSize: 10, color: TOKENS.textDim, letterSpacing: '0.16em' }}>TAB 02</Mono>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 2 }}>
              <div style={{ fontSize: 22, fontWeight: 600 }}>每日简报</div>
              <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>
                2026-05-20 · 下一交易日 05-21 · 7 个信号 · 2 项止损警报
              </Mono>
            </div>
          </div>
          {/* Tab-specific control: 分析自选 */}
          <button style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '7px 12px',
            background: 'transparent',
            border: `1px solid ${TOKENS.accent}66`,
            borderRadius: 5,
            color: TOKENS.accent,
            fontFamily: 'inherit',
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
          }}>
            ▶ 分析自选
          </button>
        </div>

        {/* ROW 2 — Macro banner */}
        <MacroBannerV2 />

        {/* ROW 3 — Brief sections */}
        <BriefV2 />

        {/* ROW 4 — Signal score table */}
        <ScoreTableV2 />

        {/* ROW 5 — T+1 rebalance summary */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
            <Mono style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.08em' }}>今日可执行调仓 · T+1 已计入</Mono>
            <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>基于当前信号 + T+1 状态计算</Mono>
          </div>
          <T1RebalanceBar />
        </div>

        {/* Footer */}
        <div style={{
          marginTop: 4, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`,
          display: 'flex', justifyContent: 'space-between',
          fontSize: 10, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace',
        }}>
          <span>本简报由算法 + LLM 产出 · 不构成投资建议</span>
          <span>GPT-4 · 因子模型 v2.3 · 缓存 08:31:42</span>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Tab2BriefV2, T1RebalanceBar });
