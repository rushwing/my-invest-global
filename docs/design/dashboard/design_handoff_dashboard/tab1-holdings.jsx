/* global React, TOKENS, SIGNAL, Card, Mono, KPICard, SignalBadge, Tag, pnlColor */

// =========== HOLDINGS DATA ===========
const HOLDINGS = [
  // 白马股 — blue chip
  { code: '002415', name: '海康威视', cat: '白马股', sub: '安防', mv: 210000, pnl: 5.2,   target: 20, sig: 'hold' },
  { code: '600519', name: '贵州茅台', cat: '白马股', sub: '白酒', mv: 180000, pnl: 2.1,   target: 18, sig: 'hold' },
  { code: '000333', name: '美的集团', cat: '白马股', sub: '家电', mv:  95000, pnl: 3.8,   target: 10, sig: 'hold_add' },
  { code: '600036', name: '招商银行', cat: '白马股', sub: '银行', mv:  75000, pnl: -1.2,  target:  9, sig: 'hold' },
  { code: '601318', name: '中国平安', cat: '白马股', sub: '保险', mv:  55000, pnl: 0.8,   target: 10, sig: 'hold_add' },
  // 弹性股 — high-beta AI infra
  { code: '300308', name: '中际旭创', cat: '弹性股', sub: '光通信',   mv: 100800, pnl: 18.59, target: 6, sig: 'reduce' },
  { code: '002179', name: '中航光电', cat: '弹性股', sub: '光通信',   mv:  62000, pnl: 12.4,  target: 6, sig: 'hold' },
  { code: '688981', name: '中芯国际', cat: '弹性股', sub: '半导体',   mv:  48000, pnl: -3.5,  target: 6, sig: 'hold_add' },
  { code: '002129', name: 'TCL中环',  cat: '弹性股', sub: '半导体',   mv:  35000, pnl: 8.9,   target: 5, sig: 'hold' },
  { code: '300474', name: '景嘉微',   cat: '弹性股', sub: '算力',     mv:  28000, pnl: -8.2,  target: 5, sig: 'hold_add' },
  { code: '002384', name: '东山精密', cat: '弹性股', sub: '光通信',   mv:  22000, pnl: 6.7,   target: 5, sig: 'hold' },
];

const TOTAL_MV = HOLDINGS.reduce((s, h) => s + h.mv, 0);
const TOTAL_PROFIT = HOLDINGS.reduce((s, h) => s + h.mv * h.pnl / 100, 0);
const COST_BASIS = TOTAL_MV - TOTAL_PROFIT;
const TOTAL_PNL_PCT = (TOTAL_PROFIT / COST_BASIS) * 100;

const BAIMA_MV   = HOLDINGS.filter(h => h.cat === '白马股').reduce((s, h) => s + h.mv, 0);
const TANXING_MV = HOLDINGS.filter(h => h.cat === '弹性股').reduce((s, h) => s + h.mv, 0);
const BAIMA_PCT   = BAIMA_MV / TOTAL_MV * 100;   // ~67.5
const TANXING_PCT = TANXING_MV / TOTAL_MV * 100; // ~32.5
const MAX_TANXING = HOLDINGS.filter(h => h.cat === '弹性股').reduce((m, h) => Math.max(m, h.mv / TOTAL_MV * 100), 0);
const MAX_TANXING_HOLDING = HOLDINGS.filter(h => h.cat === '弹性股').sort((a,b) => b.mv - a.mv)[0];

const fmt = (n, digits = 0) => n.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits });

// =========== DONUT ===========
function AllocationDonut() {
  const R = 80;
  const STROKE = 22;
  const C = 2 * Math.PI * R;
  const baimaArc = (BAIMA_PCT / 100) * C;
  const targetBaima = 67;
  const dev = Math.abs(BAIMA_PCT - targetBaima);
  // deviation status
  let devTone = TOKENS.bull;
  if (dev > 10) devTone = TOKENS.bear;
  else if (dev > 5) devTone = TOKENS.neutral;

  const baimaColor = dev > 10 ? TOKENS.bear : dev > 5 ? TOKENS.neutral : TOKENS.accent;

  return (
    <Card pad={16} style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>资产配置</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>白马股 vs 弹性股 · 当前 / 目标</div>
        </div>
        <Tag tone={dev > 10 ? 'bear' : dev > 5 ? 'neutral' : 'bull'}>
          偏差 {dev.toFixed(1)}%
        </Tag>
      </div>
      <div style={{ display: 'flex', gap: 18, alignItems: 'center', marginTop: 8 }}>
        <svg width={200} height={200} viewBox="0 0 200 200">
          {/* target ring (background dashed) */}
          <circle cx="100" cy="100" r={R + 16} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="3 4" />
          {/* base ring */}
          <circle cx="100" cy="100" r={R} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={STROKE} />
          {/* tanxing (rest of circle) */}
          <circle cx="100" cy="100" r={R} fill="none" stroke="#5C616E" strokeWidth={STROKE} strokeDasharray={`${C - baimaArc} ${C}`} strokeDashoffset={-baimaArc} transform="rotate(-90 100 100)" strokeLinecap="butt" />
          {/* baima */}
          <circle cx="100" cy="100" r={R} fill="none" stroke={baimaColor} strokeWidth={STROKE} strokeDasharray={`${baimaArc} ${C}`} transform="rotate(-90 100 100)" strokeLinecap="butt" />
          {/* target marker — small tick at 67% */}
          {(() => {
            const angle = (targetBaima / 100) * 2 * Math.PI - Math.PI / 2;
            const x1 = 100 + (R - STROKE / 2 - 4) * Math.cos(angle);
            const y1 = 100 + (R - STROKE / 2 - 4) * Math.sin(angle);
            const x2 = 100 + (R + STROKE / 2 + 4) * Math.cos(angle);
            const y2 = 100 + (R + STROKE / 2 + 4) * Math.sin(angle);
            return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#fff" strokeWidth="1.5" />;
          })()}
          {/* center text */}
          <text x="100" y="92" textAnchor="middle" fill={TOKENS.textMuted} fontSize="10" fontFamily="Noto Sans SC">总市值</text>
          <text x="100" y="115" textAnchor="middle" fill="#fff" fontSize="20" fontFamily="JetBrains Mono" fontWeight="600">¥{(TOTAL_MV/10000).toFixed(1)}</text>
          <text x="100" y="130" textAnchor="middle" fill={TOKENS.textDim} fontSize="9" fontFamily="JetBrains Mono">万元</text>
        </svg>
        <div style={{ flex: 1, display: 'grid', gap: 10 }}>
          <LegendRow color={baimaColor} label="白马股" cur={BAIMA_PCT} target={67} mv={BAIMA_MV} />
          <LegendRow color="#5C616E" label="弹性股" cur={TANXING_PCT} target={33} mv={TANXING_MV} />
          <div style={{ borderTop: `1px solid ${TOKENS.border}`, paddingTop: 8, marginTop: 2 }}>
            <div style={{ fontSize: 10, color: TOKENS.textDim, marginBottom: 4 }}>状态</div>
            <div style={{ fontSize: 12, color: devTone, fontWeight: 500 }}>
              {dev > 10 ? '⚠ 严重偏离 · 建议再平衡' : dev > 5 ? '· 轻度偏离 · 可观察' : '✓ 配置健康 · 在目标区间'}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function LegendRow({ color, label, cur, target, mv }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <div style={{ width: 10, height: 10, background: color, borderRadius: 2 }} />
        <div style={{ fontSize: 12, fontWeight: 500 }}>{label}</div>
        <div style={{ flex: 1 }} />
        <Mono style={{ fontSize: 13, fontWeight: 600 }}>{cur.toFixed(1)}%</Mono>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', paddingLeft: 18 }}>
        <span>目标 {target}%</span>
        <span>¥{fmt(mv)}</span>
      </div>
    </div>
  );
}

// =========== TREEMAP ===========
// Squarified-ish layout for simple horizontal/vertical split
function squarify(items, w, h) {
  // items: {value, ...}
  // simple slice-and-dice with row packing
  const total = items.reduce((s, i) => s + i.value, 0);
  const result = [];
  let remaining = [...items];
  let x = 0, y = 0, availW = w, availH = h;

  while (remaining.length > 0) {
    const horizontal = availW >= availH;
    const sliceDim = horizontal ? availH : availW;
    // take items until row aspect ratio degrades
    let rowItems = [];
    let rowSum = 0;
    let bestRatio = Infinity;
    for (let i = 0; i < remaining.length; i++) {
      const trial = [...rowItems, remaining[i]];
      const trialSum = rowSum + remaining[i].value;
      const totalRem = remaining.reduce((s, it) => s + it.value, 0);
      const sliceLen = (trialSum / totalRem) * (horizontal ? availW : availH);
      const worst = Math.max(...trial.map(it => {
        const cellLen = (it.value / trialSum) * sliceDim;
        const cellOther = sliceLen;
        return Math.max(cellLen / cellOther, cellOther / cellLen);
      }));
      if (worst > bestRatio && rowItems.length > 0) break;
      bestRatio = worst;
      rowItems = trial;
      rowSum = trialSum;
    }
    const totalRem = remaining.reduce((s, it) => s + it.value, 0);
    const sliceLen = (rowSum / totalRem) * (horizontal ? availW : availH);
    let cursor = 0;
    rowItems.forEach(it => {
      const cellLen = (it.value / rowSum) * sliceDim;
      if (horizontal) {
        result.push({ ...it, x: x, y: y + cursor, w: sliceLen, h: cellLen });
      } else {
        result.push({ ...it, x: x + cursor, y: y, w: cellLen, h: sliceLen });
      }
      cursor += cellLen;
    });
    if (horizontal) { x += sliceLen; availW -= sliceLen; }
    else { y += sliceLen; availH -= sliceLen; }
    remaining = remaining.slice(rowItems.length);
  }
  return result;
}

function HoldingsHeatmap() {
  const W = 1224;
  const H = 380;
  const sorted = [...HOLDINGS].sort((a, b) => b.mv - a.mv);
  const items = sorted.map(h => ({ ...h, value: h.mv }));
  const cells = squarify(items, W, H);
  return (
    <Card pad={16} style={{ overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>持仓热力图</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>面积 = 市值 · 颜色 = 盈亏% (-20% 红 → 0 中性 → +20% 绿)</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, color: TOKENS.textMuted, fontFamily: 'JetBrains Mono, monospace' }}>
          <span>-20%</span>
          <div style={{ width: 140, height: 8, borderRadius: 2, background: `linear-gradient(90deg, ${TOKENS.bear}, #2a2a3a, ${TOKENS.bull})` }} />
          <span>+20%</span>
        </div>
      </div>
      <div style={{ position: 'relative', width: W, height: H, background: TOKENS.surfaceAlt, borderRadius: 4, overflow: 'hidden' }}>
        {cells.map(c => {
          const isPos = c.pnl >= 0;
          const isSmall = c.w < 110 || c.h < 70;
          const isTiny = c.w < 75 || c.h < 55;
          return (
            <div key={c.code} style={{
              position: 'absolute',
              left: c.x,
              top: c.y,
              width: c.w - 2,
              height: c.h - 2,
              background: pnlColor(c.pnl),
              border: `1px solid ${isPos ? '#00C47A66' : '#E8404066'}`,
              padding: isTiny ? '6px 8px' : '12px 14px',
              boxSizing: 'border-box',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              overflow: 'hidden',
            }}>
              <div>
                <div style={{
                  fontSize: isTiny ? 11 : isSmall ? 13 : 15,
                  fontWeight: 600,
                  color: '#fff',
                  lineHeight: 1.2,
                }}>{c.name}</div>
                {!isTiny && (
                  <div style={{ display: 'flex', gap: 6, alignItems: 'baseline', marginTop: 2 }}>
                    <Mono style={{ fontSize: 10, color: 'rgba(255,255,255,0.65)' }}>{c.code}</Mono>
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.55)' }}>· {c.sub}</span>
                  </div>
                )}
              </div>
              <div>
                <Mono style={{
                  fontSize: isTiny ? 13 : isSmall ? 16 : 22,
                  fontWeight: 600,
                  color: '#fff',
                  display: 'block',
                  lineHeight: 1,
                }}>{isPos ? '+' : ''}{c.pnl.toFixed(2)}%</Mono>
                {!isSmall && (
                  <Mono style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)', marginTop: 4, display: 'block' }}>
                    ¥{fmt(c.mv)}
                  </Mono>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// =========== DEVIATION TABLE ===========
function DeviationTable() {
  const rows = HOLDINGS.map(h => {
    const curPct = h.mv / TOTAL_MV * 100;
    const dev = curPct - h.target;
    return { ...h, curPct, dev };
  }).sort((a, b) => Math.abs(b.dev) - Math.abs(a.dev));

  return (
    <Card pad={0} style={{ overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>偏离明细 · 再平衡建议</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>按偏差绝对值排序 · 黄色 |偏差|&gt;5% · 红色 |偏差|&gt;10%</div>
        </div>
        <div style={{ display: 'flex', gap: 10, fontSize: 11, color: TOKENS.textMuted, fontFamily: 'JetBrains Mono, monospace' }}>
          <span>SORT: |dev| DESC</span>
        </div>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: TOKENS.surfaceAlt }}>
            <th style={thStyle()}>股票名</th>
            <th style={thStyle()}>类别</th>
            <th style={thStyle('right')}>当前占比</th>
            <th style={thStyle('right')}>目标占比</th>
            <th style={thStyle('right')}>偏差</th>
            <th style={thStyle('right')}>市值</th>
            <th style={thStyle('right')}>盈亏%</th>
            <th style={thStyle()}>操作建议</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const adev = Math.abs(r.dev);
            const isPos = r.dev > 0;
            const isPnlPos = r.pnl >= 0;
            let rowBg = 'transparent';
            if (adev > 10) rowBg = `${TOKENS.bear}1A`;
            else if (adev > 5) rowBg = `${TOKENS.neutral}14`;
            return (
              <tr key={r.code} style={{ background: rowBg, borderTop: `1px solid ${TOKENS.border}` }}>
                <td style={tdStyle()}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                    <span style={{ fontWeight: 500 }}>{r.name}</span>
                    <Mono style={{ fontSize: 11, color: TOKENS.textDim }}>{r.code}</Mono>
                  </div>
                </td>
                <td style={tdStyle()}>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <Tag>{r.cat}</Tag>
                    <span style={{ fontSize: 10, color: TOKENS.textDim }}>{r.sub}</span>
                  </div>
                </td>
                <td style={tdStyle('right')}><Mono>{r.curPct.toFixed(2)}%</Mono></td>
                <td style={tdStyle('right')}><Mono style={{ color: TOKENS.textMuted }}>{r.target.toFixed(2)}%</Mono></td>
                <td style={tdStyle('right')}>
                  <Mono style={{ color: isPos ? TOKENS.bull : TOKENS.bear, fontWeight: 600 }}>
                    {isPos ? '+' : ''}{r.dev.toFixed(2)}%
                  </Mono>
                </td>
                <td style={tdStyle('right')}><Mono>¥{fmt(r.mv)}</Mono></td>
                <td style={tdStyle('right')}>
                  <Mono style={{ color: isPnlPos ? TOKENS.bull : TOKENS.bear }}>{isPnlPos ? '+' : ''}{r.pnl.toFixed(2)}%</Mono>
                </td>
                <td style={tdStyle()}>
                  <SignalBadge type={r.sig} size="sm" />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function thStyle(align = 'left') {
  return {
    textAlign: align,
    padding: '10px 14px',
    fontWeight: 500,
    fontSize: 10,
    color: TOKENS.textMuted,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    fontFamily: 'JetBrains Mono, monospace',
  };
}
function tdStyle(align = 'left') {
  return {
    textAlign: align,
    padding: '11px 14px',
    fontSize: 13,
    color: TOKENS.text,
  };
}

// =========== TABS BAR ===========
function TabBar({ active = 0 }) {
  const tabs = ['持仓总览', '个股深度', '行业概览', '信号建议'];
  return (
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
          fontWeight: i === active ? 600 : 400,
          color: i === active ? TOKENS.text : TOKENS.textMuted,
          borderBottom: i === active ? `2px solid ${TOKENS.accent}` : '2px solid transparent',
          background: i === active ? 'rgba(79,142,247,0.06)' : 'transparent',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{ color: i === active ? TOKENS.accent : TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>0{i + 1}</span>
          {t}
        </div>
      ))}
      <div style={{ flex: 1, borderBottom: `2px solid transparent` }} />
      <div style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: TOKENS.bull }} />
          LIVE · A股盘中
        </span>
        <span>缓存 2026-05-17 14:32:08</span>
      </div>
    </div>
  );
}

// =========== TAB 1 ROOT ===========
function Tab1Holdings() {
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
          <Mono style={{ fontSize: 11, color: TOKENS.textDim, letterSpacing: '0.16em' }}>MY-INVEST-GLOBAL · A-SHARE · AI INFRA</Mono>
          <div style={{ fontSize: 28, fontWeight: 600, marginTop: 4, letterSpacing: '-0.01em' }}>持仓总览</div>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginTop: 4 }}>2026-05-17 周日 · 收盘后视图 · 11 只持仓 · 监控行业: 光通信 · 半导体 · 算力</div>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <SummaryStat label="组合总市值" value={`¥${fmt(TOTAL_MV)}`} sub={`成本基准 ¥${fmt(COST_BASIS, 0)}`} />
          <SummaryStat label="累计盈亏" value={`¥+${fmt(TOTAL_PROFIT, 0)}`} sub={`${TOTAL_PNL_PCT.toFixed(2)}% · 日内 +0.45%`} tone="bull" />
        </div>
      </div>

      {/* Tabs */}
      <div style={{ marginBottom: 16 }}>
        <TabBar active={0} />
      </div>

      {/* Row 1: donut + KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 1fr', gap: 12, marginBottom: 12 }}>
        <AllocationDonut />
        <div style={{ display: 'grid', gridTemplateRows: 'repeat(3, 1fr)', gap: 12 }}>
          <KPIRow
            label="白马股市值"
            value={`¥${fmt(BAIMA_MV)}`}
            pct={`${BAIMA_PCT.toFixed(2)}%`}
            sub={`目标 67% · 偏差 ${(BAIMA_PCT - 67) >= 0 ? '+' : ''}${(BAIMA_PCT - 67).toFixed(2)}%`}
            tone="bull"
            barPct={BAIMA_PCT}
            targetBar={67}
          />
          <KPIRow
            label="弹性股市值"
            value={`¥${fmt(TANXING_MV)}`}
            pct={`${TANXING_PCT.toFixed(2)}%`}
            sub={`目标 33% · 偏差 ${(TANXING_PCT - 33) >= 0 ? '+' : ''}${(TANXING_PCT - 33).toFixed(2)}%`}
            tone="neutral"
            barPct={TANXING_PCT}
            targetBar={33}
          />
          <KPIRow
            label="最大单只弹性股占比"
            value={`${MAX_TANXING.toFixed(2)}%`}
            pct={MAX_TANXING_HOLDING.name}
            code={MAX_TANXING_HOLDING.code}
            sub={`阈值 8% · 超出 +${(MAX_TANXING - 8).toFixed(2)}% · 建议减仓至阈值内`}
            tone="bear"
            danger
          />
        </div>
      </div>

      {/* Row 2: Heatmap */}
      <div style={{ marginBottom: 12 }}>
        <HoldingsHeatmap />
      </div>

      {/* Row 3: Deviation table */}
      <DeviationTable />

      {/* footer */}
      <div style={{ marginTop: 18, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
        <span>my-invest-global · personal advisor · 仅供个人投资参考</span>
        <span>数据源 Tushare · 缓存 2026-05-17 14:32:08 · Streamlit dark</span>
      </div>
    </div>
  );
}

function SummaryStat({ label, value, sub, tone }) {
  return (
    <div style={{
      background: TOKENS.surface,
      border: `1px solid ${TOKENS.border}`,
      borderRadius: 8,
      padding: '10px 16px',
      minWidth: 200,
    }}>
      <div style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.06em' }}>{label}</div>
      <Mono style={{ fontSize: 22, fontWeight: 600, color: tone === 'bull' ? TOKENS.bull : TOKENS.text, display: 'block', lineHeight: 1.15 }}>{value}</Mono>
      <div style={{ fontSize: 10, color: TOKENS.textDim, marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>{sub}</div>
    </div>
  );
}

function KPIRow({ label, value, pct, code, sub, tone, barPct, targetBar, danger }) {
  const toneColor = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : tone === 'neutral' ? TOKENS.accent : TOKENS.text;
  return (
    <div style={{
      background: TOKENS.surface,
      border: `1px solid ${danger ? TOKENS.bear + '55' : TOKENS.border}`,
      borderRadius: 8,
      padding: 12,
      position: 'relative',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
    }}>
      {danger && (
        <div style={{ position: 'absolute', top: 10, right: 12 }}>
          <Tag tone="bear">超阈值</Tag>
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div style={{ fontSize: 11, color: TOKENS.textMuted }}>{label}</div>
        {code && <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{code}</Mono>}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 4 }}>
        <Mono style={{ fontSize: 22, fontWeight: 600, color: toneColor, lineHeight: 1.1 }}>{value}</Mono>
        <Mono style={{ fontSize: 13, color: TOKENS.textMuted }}>{pct}</Mono>
      </div>
      {barPct !== undefined && (
        <div style={{ position: 'relative', height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, marginTop: 8, marginBottom: 6 }}>
          <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${barPct}%`, background: toneColor, borderRadius: 2 }} />
          {targetBar !== undefined && (
            <div style={{ position: 'absolute', left: `${targetBar}%`, top: -2, width: 1.5, height: 8, background: '#fff' }} />
          )}
        </div>
      )}
      <div style={{ fontSize: 11, color: TOKENS.textDim, marginTop: barPct !== undefined ? 0 : 6, fontFamily: 'JetBrains Mono, monospace' }}>{sub}</div>
    </div>
  );
}

Object.assign(window, { Tab1Holdings, HOLDINGS });
