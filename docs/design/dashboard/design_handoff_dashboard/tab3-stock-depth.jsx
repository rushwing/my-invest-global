/* global React, TOKENS, SIGNAL, Card, Mono, SignalBadge, Tag */
const { useState: useStateT3 } = React;

// =========== SYNTHETIC OHLC (300308 中际旭创) ===========
// Generate 100 trading days ending 2026-05-15. Realistic uptrend with pullbacks.
function genOHLC() {
  const out = [];
  let price = 145;
  const start = new Date('2025-12-15');
  let d = new Date(start);
  for (let i = 0; i < 100; i++) {
    // skip weekends
    while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
    const drift = 0.0040;
    const vol = 0.027;
    const r = (Math.sin(i * 0.38) * 0.6 + Math.sin(i * 0.13) * 0.9 + (Math.random() - 0.5) * 1.2);
    const change = drift + r * vol;
    const open = price;
    const close = +(open * (1 + change)).toFixed(2);
    const high = +(Math.max(open, close) * (1 + Math.random() * 0.015)).toFixed(2);
    const low = +(Math.min(open, close) * (1 - Math.random() * 0.015)).toFixed(2);
    const volBars = +(2000000 + Math.abs(change) * 60000000 + Math.random() * 1500000).toFixed(0);
    out.push({ d: d.toISOString().slice(5, 10), o: open, h: high, l: low, c: close, v: volBars });
    price = close;
    d.setDate(d.getDate() + 1);
  }
  return out;
}
function sma(arr, n) {
  return arr.map((_, i) => {
    if (i < n - 1) return null;
    let s = 0;
    for (let k = i - n + 1; k <= i; k++) s += arr[k];
    return s / n;
  });
}
function stddev(arr, n) {
  return arr.map((_, i) => {
    if (i < n - 1) return null;
    let s = 0;
    for (let k = i - n + 1; k <= i; k++) s += arr[k];
    const mean = s / n;
    let v = 0;
    for (let k = i - n + 1; k <= i; k++) v += (arr[k] - mean) ** 2;
    return Math.sqrt(v / n);
  });
}
function ema(arr, n) {
  const k = 2 / (n + 1);
  const out = [];
  arr.forEach((v, i) => {
    if (i === 0) out.push(v);
    else out.push(v * k + out[i - 1] * (1 - k));
  });
  return out;
}
function rsi(arr, n = 14) {
  const out = [];
  let gain = 0, loss = 0;
  for (let i = 0; i < arr.length; i++) {
    if (i === 0) { out.push(null); continue; }
    const ch = arr[i] - arr[i - 1];
    const g = Math.max(ch, 0);
    const l = Math.max(-ch, 0);
    if (i <= n) { gain += g; loss += l; out.push(null); continue; }
    if (i === n + 1) {
      gain = gain / n; loss = loss / n;
    } else {
      gain = (gain * (n - 1) + g) / n;
      loss = (loss * (n - 1) + l) / n;
    }
    const rs = loss === 0 ? 100 : gain / loss;
    out.push(100 - 100 / (1 + rs));
  }
  return out;
}

const RAW = genOHLC();
const CLOSES = RAW.map(x => x.c);
const BB_MID = sma(CLOSES, 20);
const BB_SD  = stddev(CLOSES, 20);
const BB_UP  = BB_MID.map((m, i) => m == null ? null : m + 2 * BB_SD[i]);
const BB_LO  = BB_MID.map((m, i) => m == null ? null : m - 2 * BB_SD[i]);
const MA13W = sma(CLOSES, 65); // 13 weeks ≈ 65 trading days
const EMA12 = ema(CLOSES, 12);
const EMA26 = ema(CLOSES, 26);
const MACD = EMA12.map((v, i) => v - EMA26[i]);
const MACD_SIGNAL = ema(MACD, 9);
const MACD_HIST = MACD.map((m, i) => m - MACD_SIGNAL[i]);
const RSI = rsi(CLOSES, 14);

// Find golden cross (MACD crosses above signal)
const GOLDEN_CROSS = [];
for (let i = 1; i < MACD.length; i++) {
  if (MACD[i - 1] <= MACD_SIGNAL[i - 1] && MACD[i] > MACD_SIGNAL[i]) GOLDEN_CROSS.push(i);
  if (MACD[i - 1] >= MACD_SIGNAL[i - 1] && MACD[i] < MACD_SIGNAL[i]) GOLDEN_CROSS.push({ i, death: true });
}

// =========== CHART ===========
const CHART_W = 1224;
const PRICE_H = 320;
const VOL_H = 70;
const MACD_H = 90;
const RSI_H = 90;
const GAP = 6;
const LEFT_AX = 56;
const RIGHT_AX = 12;
const TOP_PAD = 8;
const BOT_PAD = 22;
const PLOT_W = CHART_W - LEFT_AX - RIGHT_AX;
const N = RAW.length;
const COL_W = PLOT_W / N;
const CANDLE_W = Math.max(2, COL_W * 0.62);

function scale(v, min, max, h) {
  if (v == null) return null;
  return TOP_PAD + (1 - (v - min) / (max - min)) * (h - TOP_PAD - BOT_PAD);
}

function TripleChart() {
  // price pane scale
  const allP = [...CLOSES, ...RAW.map(r => r.h), ...RAW.map(r => r.l), ...BB_UP.filter(x => x != null), ...BB_LO.filter(x => x != null)];
  const pmin = Math.min(...allP) * 0.99;
  const pmax = Math.max(...allP) * 1.01;
  const volMax = Math.max(...RAW.map(r => r.v)) * 1.1;
  const macdAbs = Math.max(...MACD.map(Math.abs), ...MACD_SIGNAL.map(v => Math.abs(v || 0)));
  const macdMin = -macdAbs, macdMax = macdAbs;

  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>价格 / 技术指标</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>日 K · 100 个交易日 · 布林带 (20, 2σ) · 13 周均线 · MACD(12,26,9) · RSI(14)</div>
        </div>
        <div style={{ display: 'flex', gap: 14, fontSize: 11, alignItems: 'center' }}>
          <LegItem c="#fff" t="OHLC" />
          <LegItem c={TOKENS.accent} t="MA13W" />
          <LegItem c="rgba(245,166,35,0.7)" t="BB(20,2σ)" dashed />
          <LegItem c={TOKENS.bull} t="MACD" />
          <LegItem c="rgba(232,64,64,0.8)" t="Signal" dashed />
        </div>
      </div>

      <svg width={CHART_W} height={PRICE_H + VOL_H + MACD_H + RSI_H + GAP * 3 + 6} style={{ display: 'block' }}>
        {/* ===== PRICE PANE ===== */}
        <g transform={`translate(0,0)`}>
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={PRICE_H} fill={TOKENS.surfaceAlt} />
          {/* grid */}
          {[0.2, 0.4, 0.6, 0.8].map(t => (
            <line key={t} x1={LEFT_AX} x2={CHART_W - RIGHT_AX} y1={TOP_PAD + t * (PRICE_H - TOP_PAD - BOT_PAD)} y2={TOP_PAD + t * (PRICE_H - TOP_PAD - BOT_PAD)} stroke="rgba(255,255,255,0.04)" />
          ))}
          {/* price ticks */}
          {[0, 0.25, 0.5, 0.75, 1].map((t, i) => {
            const v = pmax - t * (pmax - pmin);
            const y = TOP_PAD + t * (PRICE_H - TOP_PAD - BOT_PAD);
            return <text key={i} x={LEFT_AX - 6} y={y + 3} fontSize="9" fill={TOKENS.textDim} textAnchor="end" fontFamily="JetBrains Mono">{v.toFixed(0)}</text>;
          })}
          {/* BB bands */}
          <path d={bandPath(BB_UP, BB_LO, pmin, pmax, PRICE_H)} fill="rgba(245,166,35,0.06)" stroke="none" />
          <path d={linePath(BB_UP, pmin, pmax, PRICE_H)} stroke="rgba(245,166,35,0.55)" strokeWidth="1" fill="none" strokeDasharray="2 3" />
          <path d={linePath(BB_LO, pmin, pmax, PRICE_H)} stroke="rgba(245,166,35,0.55)" strokeWidth="1" fill="none" strokeDasharray="2 3" />
          <path d={linePath(BB_MID, pmin, pmax, PRICE_H)} stroke="rgba(245,166,35,0.4)" strokeWidth="1" fill="none" />
          {/* MA13W */}
          <path d={linePath(MA13W, pmin, pmax, PRICE_H)} stroke={TOKENS.accent} strokeWidth="1.6" fill="none" />
          {/* Candles */}
          {RAW.map((r, i) => {
            const x = LEFT_AX + i * COL_W + (COL_W - CANDLE_W) / 2;
            const xMid = LEFT_AX + i * COL_W + COL_W / 2;
            const isUp = r.c >= r.o;
            const color = isUp ? TOKENS.bull : TOKENS.bear;
            const yH = scale(r.h, pmin, pmax, PRICE_H);
            const yL = scale(r.l, pmin, pmax, PRICE_H);
            const yO = scale(r.o, pmin, pmax, PRICE_H);
            const yC = scale(r.c, pmin, pmax, PRICE_H);
            const top = Math.min(yO, yC);
            const bh = Math.max(1, Math.abs(yC - yO));
            return (
              <g key={i}>
                <line x1={xMid} y1={yH} x2={xMid} y2={yL} stroke={color} strokeWidth="1" />
                <rect x={x} y={top} width={CANDLE_W} height={bh} fill={isUp ? 'transparent' : color} stroke={color} strokeWidth="1" />
              </g>
            );
          })}
          {/* Border */}
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={PRICE_H} fill="none" stroke={TOKENS.border} />
          <text x={LEFT_AX + 8} y={14} fontSize="10" fill={TOKENS.textMuted} fontFamily="Noto Sans SC">价格 (¥)</text>
        </g>

        {/* ===== VOLUME (bottom of price pane, separate strip) ===== */}
        <g transform={`translate(0, ${PRICE_H + GAP})`}>
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={VOL_H} fill={TOKENS.surfaceAlt} />
          {RAW.map((r, i) => {
            const x = LEFT_AX + i * COL_W + (COL_W - CANDLE_W) / 2;
            const isUp = r.c >= r.o;
            const color = isUp ? `${TOKENS.bull}aa` : `${TOKENS.bear}aa`;
            const h = (r.v / volMax) * (VOL_H - 12);
            return <rect key={i} x={x} y={VOL_H - h - 2} width={CANDLE_W} height={h} fill={color} />;
          })}
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={VOL_H} fill="none" stroke={TOKENS.border} />
          <text x={LEFT_AX + 8} y={12} fontSize="10" fill={TOKENS.textMuted} fontFamily="Noto Sans SC">成交量</text>
        </g>

        {/* ===== MACD PANE ===== */}
        <g transform={`translate(0, ${PRICE_H + VOL_H + GAP * 2})`}>
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={MACD_H} fill={TOKENS.surfaceAlt} />
          {/* zero line */}
          <line x1={LEFT_AX} x2={CHART_W - RIGHT_AX} y1={scale(0, macdMin, macdMax, MACD_H)} y2={scale(0, macdMin, macdMax, MACD_H)} stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
          {/* histogram */}
          {MACD_HIST.map((v, i) => {
            if (v == null) return null;
            const x = LEFT_AX + i * COL_W + (COL_W - CANDLE_W) / 2;
            const y0 = scale(0, macdMin, macdMax, MACD_H);
            const y1 = scale(v, macdMin, macdMax, MACD_H);
            const top = Math.min(y0, y1);
            const h = Math.max(1, Math.abs(y1 - y0));
            const isPos = v >= 0;
            return <rect key={i} x={x} y={top} width={CANDLE_W} height={h} fill={isPos ? `${TOKENS.bull}88` : `${TOKENS.bear}88`} />;
          })}
          {/* lines */}
          <path d={linePath(MACD, macdMin, macdMax, MACD_H)} stroke={TOKENS.bull} strokeWidth="1.4" fill="none" />
          <path d={linePath(MACD_SIGNAL, macdMin, macdMax, MACD_H)} stroke={TOKENS.bear} strokeWidth="1.4" fill="none" strokeDasharray="3 2" />
          {/* golden / death cross markers */}
          {GOLDEN_CROSS.filter(g => typeof g === 'number').map((idx, k) => (
            <g key={`gc${k}`}>
              <circle cx={LEFT_AX + idx * COL_W + COL_W / 2} cy={scale(MACD[idx], macdMin, macdMax, MACD_H)} r="4" fill={TOKENS.bull} stroke="#fff" strokeWidth="1" />
            </g>
          ))}
          {GOLDEN_CROSS.filter(g => typeof g === 'object').map((g, k) => (
            <g key={`dc${k}`}>
              <circle cx={LEFT_AX + g.i * COL_W + COL_W / 2} cy={scale(MACD[g.i], macdMin, macdMax, MACD_H)} r="4" fill={TOKENS.bear} stroke="#fff" strokeWidth="1" />
            </g>
          ))}
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={MACD_H} fill="none" stroke={TOKENS.border} />
          <text x={LEFT_AX + 8} y={12} fontSize="10" fill={TOKENS.textMuted} fontFamily="Noto Sans SC">MACD (12,26,9)</text>
        </g>

        {/* ===== RSI PANE ===== */}
        <g transform={`translate(0, ${PRICE_H + VOL_H + MACD_H + GAP * 3})`}>
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={RSI_H} fill={TOKENS.surfaceAlt} />
          {/* shaded oversold/overbought zones */}
          {(() => {
            const y30 = scale(30, 0, 100, RSI_H);
            const y70 = scale(70, 0, 100, RSI_H);
            const yBot = RSI_H - BOT_PAD;
            return (
              <>
                <rect x={LEFT_AX} y={TOP_PAD} width={PLOT_W} height={y70 - TOP_PAD} fill="rgba(232,64,64,0.06)" />
                <rect x={LEFT_AX} y={y30} width={PLOT_W} height={yBot - y30} fill="rgba(0,196,122,0.06)" />
                <line x1={LEFT_AX} x2={CHART_W - RIGHT_AX} y1={y70} y2={y70} stroke="rgba(232,64,64,0.5)" strokeDasharray="3 3" />
                <line x1={LEFT_AX} x2={CHART_W - RIGHT_AX} y1={y30} y2={y30} stroke="rgba(0,196,122,0.5)" strokeDasharray="3 3" />
                <line x1={LEFT_AX} x2={CHART_W - RIGHT_AX} y1={scale(50, 0, 100, RSI_H)} y2={scale(50, 0, 100, RSI_H)} stroke="rgba(255,255,255,0.1)" />
                <text x={CHART_W - RIGHT_AX - 4} y={y70 - 3} fontSize="9" fill={TOKENS.bear} textAnchor="end" fontFamily="JetBrains Mono">70 超买</text>
                <text x={CHART_W - RIGHT_AX - 4} y={y30 + 10} fontSize="9" fill={TOKENS.bull} textAnchor="end" fontFamily="JetBrains Mono">30 超卖</text>
              </>
            );
          })()}
          <path d={linePath(RSI, 0, 100, RSI_H)} stroke="#C792EA" strokeWidth="1.5" fill="none" />
          <rect x={LEFT_AX} y={0} width={PLOT_W} height={RSI_H} fill="none" stroke={TOKENS.border} />
          <text x={LEFT_AX + 8} y={12} fontSize="10" fill={TOKENS.textMuted} fontFamily="Noto Sans SC">RSI(14)</text>
          {/* x-axis labels */}
          {[0, 25, 50, 75, 99].map(i => (
            <text key={i} x={LEFT_AX + i * COL_W + COL_W / 2} y={RSI_H - 6} fontSize="9" fill={TOKENS.textDim} fontFamily="JetBrains Mono" textAnchor="middle">{RAW[i].d}</text>
          ))}
        </g>
      </svg>

      {/* Indicator readout strip */}
      <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 0, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, borderTop: `1px solid ${TOKENS.border}`, paddingTop: 10 }}>
        <IndStat label="收盘" value={`¥${CLOSES[N-1].toFixed(2)}`} tone="text" />
        <IndStat label="MA20" value={BB_MID[N-1].toFixed(2)} />
        <IndStat label="MA13W" value={MA13W[N-1].toFixed(2)} />
        <IndStat label="MACD" value={MACD[N-1].toFixed(3)} tone={MACD[N-1] > MACD_SIGNAL[N-1] ? 'bull' : 'bear'} />
        <IndStat label="RSI(14)" value={RSI[N-1].toFixed(1)} tone={RSI[N-1] > 70 ? 'bear' : RSI[N-1] < 30 ? 'bull' : 'text'} />
        <IndStat label="信号" value="趋势向上" tone="bull" />
      </div>
    </Card>
  );
}

function LegItem({ c, t, dashed }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: TOKENS.textMuted }}>
      <span style={{
        width: 14, height: 0,
        borderTop: `2px ${dashed ? 'dashed' : 'solid'} ${c}`,
      }} />
      {t}
    </span>
  );
}
function IndStat({ label, value, tone }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : TOKENS.text;
  return (
    <div>
      <div style={{ fontSize: 10, color: TOKENS.textDim }}>{label}</div>
      <div style={{ fontSize: 13, color: c, fontWeight: 600, marginTop: 1 }}>{value}</div>
    </div>
  );
}

function linePath(arr, min, max, h) {
  let d = '';
  let started = false;
  arr.forEach((v, i) => {
    if (v == null) return;
    const x = LEFT_AX + i * COL_W + COL_W / 2;
    const y = scale(v, min, max, h);
    if (!started) { d += `M ${x} ${y}`; started = true; }
    else d += ` L ${x} ${y}`;
  });
  return d;
}
function bandPath(upper, lower, min, max, h) {
  let d = '';
  let started = false;
  upper.forEach((v, i) => {
    if (v == null) return;
    const x = LEFT_AX + i * COL_W + COL_W / 2;
    const y = scale(v, min, max, h);
    if (!started) { d += `M ${x} ${y}`; started = true; }
    else d += ` L ${x} ${y}`;
  });
  for (let i = lower.length - 1; i >= 0; i--) {
    if (lower[i] == null) continue;
    const x = LEFT_AX + i * COL_W + COL_W / 2;
    const y = scale(lower[i], min, max, h);
    d += ` L ${x} ${y}`;
  }
  d += ' Z';
  return d;
}

// =========== FUNDAMENTAL CARD ===========
const FUND = {
  ticker: '300308',
  name: '中际旭创',
  tier: 1,
  tierLabel: 'Tier-1 极高',
  tierDesc: '全球光模块龙头 / 良率壁垒极高',
  targetPrice: 235.0,
  currentPrice: CLOSES[N-1],
  upside: ((235.0 - CLOSES[N-1]) / CLOSES[N-1]) * 100,
  sectorRank: '光通信模块 #1 / 12',
  q1Rev:  192.4,
  q1Net:  256.1,
  ratings: { buy: 21, hold: 3, sell: 0 },
  marketCap: '2,184 亿',
  pe: 28.4,
  pettm: 31.2,
  peg: 0.42,
  roe: 24.8,
  staleness: 'high', // DataConfidence
};

const TIER_COLORS = {
  1: { c: '#FF7A1A', bg: 'rgba(255,122,26,0.14)', label: 'Tier-1 · 极高' },
  2: { c: '#F5A623', bg: 'rgba(245,166,35,0.14)', label: 'Tier-2 · 高'   },
  3: { c: '#9AA0AC', bg: 'rgba(154,160,172,0.14)', label: 'Tier-3 · 中'   },
  4: { c: '#4F8EF7', bg: 'rgba(79,142,247,0.14)', label: 'Tier-4 · 低'   },
};

function FundamentalCard() {
  const tc = TIER_COLORS[FUND.tier];
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>基本面摘要</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>稀缺度 / 估值 / 业绩增速 / 机构覆盖</div>
        </div>
        <span style={{
          padding: '4px 10px',
          background: tc.bg,
          color: tc.c,
          border: `1px solid ${tc.c}55`,
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 600,
        }}>{tc.label}</span>
      </div>

      <div style={{ background: TOKENS.surfaceAlt, borderRadius: 6, padding: 12, marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: TOKENS.textMuted }}>稀缺逻辑</div>
        <div style={{ fontSize: 12, color: TOKENS.text, marginTop: 4, lineHeight: 1.5 }}>
          {FUND.tierDesc} · 800G / 1.6T 光模块全球 &lt;5 家有量产能力, 单季度营收 +192% YoY
        </div>
      </div>

      {/* price block */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0, marginBottom: 14 }}>
        <PriceCell label="当前价" value={`¥${FUND.currentPrice.toFixed(2)}`} />
        <PriceCell label="目标价" value={`¥${FUND.targetPrice.toFixed(2)}`} sub="券商一致" />
        <PriceCell label="上行空间" value={`+${FUND.upside.toFixed(1)}%`} tone="bull" big />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
        <FundRow label="行业排名" value={FUND.sectorRank} />
        <FundRow label="总市值" value={FUND.marketCap} />
        <FundRow label="Q1 营收 YoY" value={`+${FUND.q1Rev}%`} tone="bull" />
        <FundRow label="Q1 净利 YoY" value={`+${FUND.q1Net}%`} tone="bull" />
        <FundRow label="PE (TTM)" value={FUND.pettm.toFixed(1)} />
        <FundRow label="PEG" value={FUND.peg.toFixed(2)} tone="bull" sub="< 1 低估" />
        <FundRow label="ROE" value={`${FUND.roe}%`} tone="bull" />
        <FundRow label="数据时效" value="HIGH" sub="2026-05-17 fetched" />
      </div>

      {/* Ratings stacked bar */}
      <div>
        <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 6 }}>机构评级 · 共 {FUND.ratings.buy + FUND.ratings.hold + FUND.ratings.sell} 家</div>
        <div style={{ display: 'flex', height: 8, borderRadius: 2, overflow: 'hidden', background: TOKENS.surfaceAlt }}>
          <div style={{ flex: FUND.ratings.buy, background: TOKENS.bull }} />
          <div style={{ flex: FUND.ratings.hold, background: TOKENS.neutral }} />
          <div style={{ flex: FUND.ratings.sell, background: TOKENS.bear }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
          <span style={{ color: TOKENS.bull }}>买入 {FUND.ratings.buy}</span>
          <span style={{ color: TOKENS.neutral }}>持有 {FUND.ratings.hold}</span>
          <span style={{ color: TOKENS.bear }}>卖出 {FUND.ratings.sell}</span>
        </div>
      </div>
    </Card>
  );
}

function PriceCell({ label, value, sub, tone, big }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : TOKENS.text;
  return (
    <div style={{ borderRight: `1px solid ${TOKENS.border}`, padding: '0 14px' }}>
      <div style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.04em' }}>{label}</div>
      <Mono style={{ fontSize: big ? 20 : 18, fontWeight: 600, color: c, display: 'block', marginTop: 4, lineHeight: 1.15 }}>{value}</Mono>
      {sub && <div style={{ fontSize: 10, color: TOKENS.textDim, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}
function FundRow({ label, value, sub, tone }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : TOKENS.text;
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '6px 0', borderBottom: `1px dashed ${TOKENS.border}` }}>
      <div style={{ fontSize: 11, color: TOKENS.textMuted }}>{label}</div>
      <div style={{ textAlign: 'right' }}>
        <Mono style={{ fontSize: 13, color: c, fontWeight: 500 }}>{value}</Mono>
        {sub && <div style={{ fontSize: 9, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>{sub}</div>}
      </div>
    </div>
  );
}

// =========== NEWS TIMELINE ===========
const NEWS = [
  { d: '05-16', t: '中际旭创发布 2026 Q1 财报: 营收同比+192%, 净利+256%', s: 'positive', rel: 0.98, src: '公告' },
  { d: '05-14', t: 'Coherent 上修 2026 财年指引, 光模块需求"远超供给"', s: 'positive', rel: 0.91, src: 'Reuters' },
  { d: '05-12', t: '中信证券: 1.6T 光模块 2026 年出货预期上调 35%, 维持买入', s: 'positive', rel: 0.86, src: '中信证券' },
  { d: '05-09', t: '北美光模块供应商良率不及预期, 国产份额预计提升至 65%', s: 'positive', rel: 0.82, src: 'LightCounting' },
  { d: '05-07', t: '主力资金净流入 ¥4.2 亿, 北上资金加仓 0.8 个百分点', s: 'positive', rel: 0.65, src: '东方财富' },
  { d: '05-05', t: 'CPO 技术路线小批量量产, 短期对模块替代有限', s: 'neutral',  rel: 0.71, src: '行业研究' },
  { d: '04-30', t: '汇率波动: 人民币升值 0.6%, 美元收入折算压力短期上升', s: 'negative', rel: 0.48, src: 'Bloomberg' },
  { d: '04-28', t: '美国 BIS 拟扩大光模块出口管制, 国产替代或受关税干扰', s: 'negative', rel: 0.74, src: 'WSJ' },
];

function NewsTimeline() {
  const sentMeta = {
    positive: { c: TOKENS.bull,    icon: '↑', label: '正面' },
    neutral:  { c: TOKENS.neutral, icon: '·', label: '中性' },
    negative: { c: TOKENS.bear,    icon: '↓', label: '负面' },
  };
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>相关新闻时间线</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>近 20 日 · 按相关度排序 · {NEWS.length} 条</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Tag tone="bull">{NEWS.filter(n => n.s === 'positive').length} 正面</Tag>
          <Tag tone="neutral">{NEWS.filter(n => n.s === 'neutral').length} 中性</Tag>
          <Tag tone="bear">{NEWS.filter(n => n.s === 'negative').length} 负面</Tag>
        </div>
      </div>
      <div style={{ position: 'relative' }}>
        {/* timeline rail */}
        <div style={{ position: 'absolute', left: 36, top: 4, bottom: 4, width: 1, background: TOKENS.border }} />
        {NEWS.map((n, i) => {
          const m = sentMeta[n.s];
          return (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '48px 16px 1fr', gap: 8, alignItems: 'flex-start', padding: '10px 0', borderBottom: i < NEWS.length - 1 ? `1px dashed ${TOKENS.border}` : 'none' }}>
              <Mono style={{ fontSize: 11, color: TOKENS.textMuted, paddingTop: 2 }}>{n.d}</Mono>
              <div style={{ position: 'relative', height: 16 }}>
                <div style={{
                  position: 'absolute',
                  left: -4,
                  top: 4,
                  width: 10, height: 10,
                  borderRadius: '50%',
                  background: m.c,
                  border: `2px solid ${TOKENS.surface}`,
                  boxShadow: `0 0 0 1px ${m.c}55`,
                }} />
              </div>
              <div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
                  <span style={{
                    fontSize: 10,
                    color: m.c,
                    border: `1px solid ${m.c}55`,
                    background: `${m.c}1A`,
                    padding: '1px 5px',
                    borderRadius: 3,
                    fontWeight: 600,
                  }}>{m.icon} {m.label}</span>
                  <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{n.src}</Mono>
                </div>
                <div style={{ fontSize: 12, color: TOKENS.text, marginTop: 4, lineHeight: 1.45 }}>{n.t}</div>
                {/* relevance bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                  <div style={{ fontSize: 9, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>相关度</div>
                  <div style={{ flex: 1, height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 1.5 }}>
                    <div style={{ width: `${n.rel * 100}%`, height: '100%', background: m.c, borderRadius: 1.5 }} />
                  </div>
                  <Mono style={{ fontSize: 10, color: TOKENS.textMuted, width: 32, textAlign: 'right' }}>{(n.rel * 100).toFixed(0)}</Mono>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// =========== TAB 3 ROOT ===========
function Tab3StockDepth() {
  const tabs = ['持仓总览', '每日策略简报', '个股深度分析', '信号仪表盘'];
  const stocks = [
    { c: '300308', n: '中际旭创' }, { c: '688008', n: '澜起科技' },
    { c: '002916', n: '深南电路' }, { c: '002837', n: '英维克' },
    { c: '688981', n: '中芯国际' }, { c: '002371', n: '北方华创' },
  ];
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
          <Mono style={{ fontSize: 11, color: TOKENS.textDim, letterSpacing: '0.16em' }}>MY-INVEST-GLOBAL · TAB 03</Mono>
          <div style={{ fontSize: 28, fontWeight: 600, marginTop: 4, letterSpacing: '-0.01em' }}>个股深度分析</div>
          <div style={{ fontSize: 12, color: TOKENS.textMuted, marginTop: 4 }}>技术 / 基本面 / 新闻三视角联动 · 默认覆盖持仓 + 关注列表</div>
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
              fontWeight: i === 2 ? 600 : 400,
              color: i === 2 ? TOKENS.text : TOKENS.textMuted,
              borderBottom: i === 2 ? `2px solid ${TOKENS.accent}` : '2px solid transparent',
              background: i === 2 ? 'rgba(79,142,247,0.06)' : 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{ color: i === 2 ? TOKENS.accent : TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>0{i + 1}</span>
              {t}
            </div>
          ))}
          <div style={{ flex: 1 }} />
        </div>
      </div>

      {/* Stock selector toolbar */}
      <div style={{
        display: 'flex',
        gap: 12,
        marginBottom: 12,
        alignItems: 'stretch',
      }}>
        {/* Selected stock card */}
        <div style={{
          background: TOKENS.surface,
          border: `1px solid ${TOKENS.border}`,
          borderRadius: 8,
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          flex: 1,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Mono style={{ fontSize: 18, fontWeight: 600 }}>300308</Mono>
            <div style={{ fontSize: 18, fontWeight: 600 }}>中际旭创</div>
            <Tag>弹性股</Tag>
            <Tag muted>光通信</Tag>
            <span style={{
              padding: '3px 8px',
              background: TIER_COLORS[1].bg,
              color: TIER_COLORS[1].c,
              border: `1px solid ${TIER_COLORS[1].c}55`,
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
            }}>Tier-1</span>
          </div>
          <div style={{ height: 28, width: 1, background: TOKENS.border }} />
          <div style={{ display: 'flex', gap: 18 }}>
            <KV label="现价" value={`¥${CLOSES[N-1].toFixed(2)}`} />
            <KV label="日涨跌" value={`+${((CLOSES[N-1] - CLOSES[N-2]) / CLOSES[N-2] * 100).toFixed(2)}%`} tone="bull" />
            <KV label="100日累计" value={`+${((CLOSES[N-1] - CLOSES[0]) / CLOSES[0] * 100).toFixed(1)}%`} tone="bull" />
            <KV label="持仓" value="450 股" sub="¥100,800" />
            <KV label="持仓盈亏" value="+18.59%" tone="bull" />
          </div>
          <div style={{ flex: 1 }} />
          <SignalBadge type="reduce" />
        </div>
        {/* Quick switch */}
        <div style={{
          background: TOKENS.surface,
          border: `1px solid ${TOKENS.border}`,
          borderRadius: 8,
          padding: '10px 12px',
          display: 'flex',
          gap: 8,
          alignItems: 'center',
        }}>
          <div style={{ fontSize: 10, color: TOKENS.textMuted, marginRight: 4 }}>切换</div>
          {stocks.slice(0, 5).map((s, i) => (
            <div key={s.c} style={{
              padding: '4px 9px',
              borderRadius: 4,
              background: i === 0 ? TOKENS.accent + '22' : 'transparent',
              border: `1px solid ${i === 0 ? TOKENS.accent + '66' : TOKENS.border}`,
              fontSize: 11,
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              minWidth: 64,
            }}>
              <Mono style={{ fontSize: 10, color: i === 0 ? TOKENS.accent : TOKENS.textDim }}>{s.c}</Mono>
              <span style={{ fontSize: 11, marginTop: 1, color: i === 0 ? TOKENS.text : TOKENS.textMuted }}>{s.n}</span>
            </div>
          ))}
          <div style={{ width: 1, height: 28, background: TOKENS.border, margin: '0 4px' }} />
          {/* Date range */}
          <div style={{ display: 'flex', gap: 4 }}>
            {['1M', '3M', '6M', '1Y', '全部'].map((r, i) => (
              <div key={r} style={{
                padding: '4px 10px',
                fontSize: 11,
                borderRadius: 3,
                background: i === 2 ? TOKENS.accent + '22' : 'transparent',
                color: i === 2 ? TOKENS.accent : TOKENS.textMuted,
                border: `1px solid ${i === 2 ? TOKENS.accent + '55' : TOKENS.border}`,
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
              }}>{r}</div>
            ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ marginBottom: 12 }}>
        <TripleChart />
      </div>

      {/* Below: 2 columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <FundamentalCard />
        <NewsTimeline />
      </div>

      {/* footer */}
      <div style={{ marginTop: 18, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
        <span>数据源 Tushare · LightCounting · 东方财富 · 公司公告 · 数据时效 HIGH</span>
        <span>缓存 2026-05-17 14:32:08</span>
      </div>
    </div>
  );
}

function KV({ label, value, sub, tone }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : TOKENS.text;
  return (
    <div>
      <div style={{ fontSize: 10, color: TOKENS.textMuted }}>{label}</div>
      <Mono style={{ fontSize: 14, fontWeight: 600, color: c, display: 'block', lineHeight: 1.2 }}>{value}</Mono>
      {sub && <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{sub}</Mono>}
    </div>
  );
}

Object.assign(window, { Tab3StockDepth, TIER_COLORS });
