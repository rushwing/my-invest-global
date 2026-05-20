/* global React, TOKENS, Card, Mono, Tag, SignalBadge, GlobalActionBar, T1Badge */
const { useState: useT5 } = React;

// =========== STOCK SELECTOR ===========
const HELD_POOL = [
  { code: '300308', name: '中际旭创', pnl:  18.59, t1: 'all_available', selected: true },
  { code: '002415', name: '海康威视', pnl:   5.20, t1: 'all_available', selected: false },
  { code: '688981', name: '中芯国际', pnl:  -3.50, t1: 'partial', avail: 5, total: 8, selected: true },
  { code: '300474', name: '景嘉微',   pnl:   0.57, t1: 'bought_today', selected: true },
  { code: '002179', name: '中航光电', pnl:  12.40, t1: 'all_available', selected: true },
  { code: '600036', name: '招商银行', pnl:  -1.20, t1: 'all_available', selected: false },
  { code: '600519', name: '贵州茅台', pnl:   2.10, t1: 'all_available', selected: false },
];

const WATCHLIST_POOL = [
  { code: '000333', name: '美的集团', sector: '家电', selected: true },
  { code: '300502', name: '新易盛',   sector: '光通信', selected: false },
  { code: '002837', name: '英维克',   sector: '液冷',   selected: false },
  { code: '688008', name: '澜起科技', sector: 'HBM',    selected: false },
  { code: '002916', name: '深南电路', sector: 'AI PCB', selected: false },
];

function ChipItem({ stock, watchlist, onClick }) {
  const c = stock.selected ? TOKENS.accent : TOKENS.border;
  const pnlPos = (stock.pnl || 0) >= 0;
  const t1Cfg = {
    all_available: { c: TOKENS.bull, label: '可用' },
    partial:       { c: TOKENS.bull, label: `${stock.avail}/${stock.total}` },
    bought_today:  { c: TOKENS.neutral, label: 'T+1' },
  }[stock.t1] || null;
  return (
    <div
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '7px 11px',
        background: stock.selected ? TOKENS.accent + '16' : TOKENS.surfaceAlt,
        border: `1px solid ${c}`,
        borderRadius: 5,
        cursor: 'pointer',
      }}
    >
      <span style={{
        width: 14, height: 14,
        borderRadius: 3,
        border: `1.5px solid ${stock.selected ? TOKENS.accent : TOKENS.borderStrong}`,
        background: stock.selected ? TOKENS.accent : 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontSize: 10,
        fontWeight: 700,
        flexShrink: 0,
      }}>{stock.selected && '✓'}</span>
      <Mono style={{ fontSize: 11, color: TOKENS.textDim }}>{stock.code}</Mono>
      <span style={{ fontSize: 12, fontWeight: 500 }}>{stock.name}</span>
      {!watchlist && (
        <Mono style={{ fontSize: 10, color: pnlPos ? TOKENS.bull : TOKENS.bear, fontWeight: 600 }}>
          {pnlPos ? '+' : ''}{stock.pnl.toFixed(2)}%
        </Mono>
      )}
      {watchlist && <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{stock.sector}</Mono>}
      {t1Cfg && (
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 3,
          padding: '1px 5px',
          background: t1Cfg.c + '14',
          border: `1px solid ${t1Cfg.c}44`,
          color: t1Cfg.c,
          borderRadius: 3,
          fontSize: 9,
          fontWeight: 600,
        }}>
          <span style={{ width: 3, height: 3, borderRadius: '50%', background: t1Cfg.c }} />
          {t1Cfg.label}
        </span>
      )}
    </div>
  );
}

function StockSelectorPanel({ selectedCount, onAnalyze }) {
  return (
    <Card pad={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>选择分析标的</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>多选 · 持仓含 T+1 状态 · 自选不含持仓数据</div>
        </div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>持仓 {HELD_POOL.length} · 自选 {WATCHLIST_POOL.length}</Mono>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Held */}
        <div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
            marginBottom: 8, paddingBottom: 6, borderBottom: `1px solid ${TOKENS.border}`,
          }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: TOKENS.accent }}>当前持仓</span>
            <Mono style={{ fontSize: 9, color: TOKENS.textDim }}>{HELD_POOL.filter(s => s.selected).length} / {HELD_POOL.length} 选中</Mono>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {HELD_POOL.map(s => <ChipItem key={s.code} stock={s} />)}
          </div>
        </div>
        {/* Watchlist */}
        <div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
            marginBottom: 8, paddingBottom: 6, borderBottom: `1px solid ${TOKENS.border}`,
          }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#C792EA' }}>自选观察</span>
            <Mono style={{ fontSize: 9, color: TOKENS.textDim }}>{WATCHLIST_POOL.filter(s => s.selected).length} / {WATCHLIST_POOL.length} 选中</Mono>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {WATCHLIST_POOL.map(s => <ChipItem key={s.code} stock={s} watchlist />)}
            <span style={{
              padding: '7px 11px',
              fontSize: 11,
              color: TOKENS.textMuted,
              border: `1px dashed ${TOKENS.border}`,
              borderRadius: 5,
              cursor: 'pointer',
            }}>+ 添加自选</span>
          </div>
        </div>
      </div>
      <div style={{
        marginTop: 14, paddingTop: 12,
        borderTop: `1px solid ${TOKENS.border}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>
          已选 <span style={{ color: TOKENS.accent, fontWeight: 600, fontSize: 14 }}>{selectedCount}</span> 只 · 预计分析 ~15 秒
        </Mono>
        <button
          onClick={onAnalyze}
          disabled={selectedCount === 0}
          style={{
            background: selectedCount > 0 ? TOKENS.accent : TOKENS.surfaceAlt,
            border: 'none',
            color: '#fff',
            padding: '9px 18px',
            borderRadius: 6,
            fontFamily: 'inherit',
            fontSize: 13,
            fontWeight: 600,
            cursor: selectedCount > 0 ? 'pointer' : 'not-allowed',
            opacity: selectedCount > 0 ? 1 : 0.4,
          }}
        >开始分析 →</button>
      </div>
    </Card>
  );
}

// =========== ANALYSIS CARDS (horizontal scroll) ===========
const ANALYSIS_CARDS = [
  { code: '300308', name: '中际旭创', tier: 1, action: 'reduce',
    price: 1008.00, cost: 850.00, pnl: 18.59,
    t1: 'all_available',
    scores: { tech: 78, fund: 82, sent: 88, total: 82.6 },
    rec: '占比 11.07% 超阈值 +3%, 减至 8% 以内, 释放约 ¥28,000',
    actionLabel: '减仓 30 手', enabled: true },
  { code: '688981', name: '中芯国际', tier: 2, action: 'hold_add',
    price: 52.40, cost: 65.00, pnl: -3.50,
    t1: 'partial', avail: 5, total: 8,
    scores: { tech: 58, fund: 84, sent: 65, total: 69.2 },
    rec: '回调至 60 日均线 + 国产替代催化, 加仓 1/3 至目标 6%',
    actionLabel: '加仓 20 手', enabled: true },
  { code: '300474', name: '景嘉微', tier: 3, action: 'hold_add',
    price: 35.40, cost: 35.20, pnl: 0.57,
    t1: 'bought_today',
    scores: { tech: 62, fund: 70, sent: 75, total: 69.1 },
    rec: '算力涨价预期持续 · 当前占比低于目标',
    actionLabel: 'T+1 锁仓', enabled: false },
  { code: '002179', name: '中航光电', tier: 1, action: 'hold',
    price: 62.05, cost: 55.20, pnl: 12.40,
    t1: 'all_available',
    scores: { tech: 71, fund: 76, sent: 70, total: 72.8 },
    rec: '+12.4% 浮盈, 持有观察 PB 估值',
    actionLabel: '持仓观望', enabled: true },
  { code: '000333', name: '美的集团', tier: 2, action: 'hold_add',
    price: 76.40, cost: null, pnl: null,
    t1: null, isWatchlist: true,
    scores: { tech: 72, fund: 78, sent: 68, total: 73.2 },
    rec: '自选标的 · 出口超预期 · 建议建仓 5%',
    actionLabel: '建仓', enabled: true },
];

const ACTION_COLORS = {
  strong_add: TOKENS.bull,
  hold_add:   TOKENS.accent,
  hold:       '#888888',
  reduce:     TOKENS.bear,
  stop_loss:  '#FF0000',
};
const ACTION_LABELS_ZH = {
  strong_add: '强力加仓',
  hold_add:   '持有加仓',
  hold:       '持有观望',
  reduce:     '减仓',
  stop_loss:  '止损',
};

const TIER_COLORS_T5 = {
  1: '#FF7A1A',
  2: '#F5A623',
  3: '#9AA0AC',
  4: '#4F8EF7',
};

function AnalysisCard({ card, focused, onClick }) {
  const ac = ACTION_COLORS[card.action];
  const tc = TIER_COLORS_T5[card.tier];
  return (
    <div
      onClick={onClick}
      style={{
        flexShrink: 0,
        width: 240,
        background: focused ? TOKENS.surface : TOKENS.surfaceAlt,
        border: `1px solid ${focused ? TOKENS.accent + '88' : TOKENS.border}`,
        borderRadius: 8,
        padding: 12,
        boxShadow: focused ? `0 0 0 2px ${TOKENS.accent}22` : 'none',
        cursor: 'pointer',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <span style={{
          padding: '1px 5px',
          background: tc + '22',
          border: `1px solid ${tc}55`,
          color: tc,
          borderRadius: 3,
          fontSize: 9,
          fontWeight: 600,
        }}>T{card.tier}</span>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{card.name}</span>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{card.code}</Mono>
        <div style={{ flex: 1 }} />
        <span style={{
          padding: '2px 6px',
          background: ac + '22',
          border: `1px solid ${ac}55`,
          color: ac,
          borderRadius: 3,
          fontSize: 9,
          fontWeight: 600,
        }}>{ACTION_LABELS_ZH[card.action]}</span>
      </div>

      {/* Price block */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto auto', gap: 6, marginBottom: 8, alignItems: 'baseline' }}>
        <Mono style={{ fontSize: 18, fontWeight: 600 }}>¥{card.price.toFixed(2)}</Mono>
        {card.cost != null ? (
          <Mono style={{ fontSize: 11, color: TOKENS.textMuted, justifySelf: 'end' }}>
            成本 ¥{card.cost.toFixed(2)}
          </Mono>
        ) : (
          <Mono style={{ fontSize: 11, color: TOKENS.textDim, justifySelf: 'end' }}>自选 · 未持有</Mono>
        )}
        {card.pnl != null && (
          <Mono style={{
            fontSize: 12, fontWeight: 600,
            color: card.pnl >= 0 ? TOKENS.bull : TOKENS.bear,
            gridColumn: '1 / 3',
          }}>
            浮盈 {card.pnl >= 0 ? '+' : ''}{card.pnl.toFixed(2)}%
          </Mono>
        )}
      </div>

      {/* T+1 row */}
      <div style={{ marginBottom: 8, minHeight: 24 }}>
        {card.t1 && (
          <T1Badge
            status={card.t1}
            availableQty={card.avail}
            totalQty={card.total}
            tomorrow="2026-05-21"
          />
        )}
      </div>

      {/* Scores */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 4, padding: '8px 0',
        borderTop: `1px dashed ${TOKENS.border}`,
        borderBottom: `1px dashed ${TOKENS.border}`,
        marginBottom: 8,
      }}>
        <ScoreMini label="技术" value={card.scores.tech} />
        <ScoreMini label="基本面" value={card.scores.fund} />
        <ScoreMini label="情绪" value={card.scores.sent} />
        <ScoreMini label="综合" value={card.scores.total} big />
      </div>

      {/* Reasoning */}
      <div style={{ fontSize: 11, color: TOKENS.textMuted, lineHeight: 1.5, minHeight: 32, marginBottom: 10 }}>
        {card.rec}
      </div>

      {/* Action button */}
      <button
        disabled={!card.enabled}
        style={{
          width: '100%',
          padding: '8px 12px',
          background: card.enabled ? ac : TOKENS.surfaceAlt,
          border: card.enabled ? 'none' : `1px solid ${TOKENS.border}`,
          color: card.enabled ? '#fff' : TOKENS.textDim,
          borderRadius: 5,
          fontSize: 12,
          fontWeight: 600,
          fontFamily: 'inherit',
          cursor: card.enabled ? 'pointer' : 'not-allowed',
          opacity: card.enabled ? 1 : 0.6,
        }}
      >
        {card.enabled ? card.actionLabel : `🔒 ${card.actionLabel}`}
      </button>
    </div>
  );
}

function ScoreMini({ label, value, big }) {
  const c = value >= 75 ? TOKENS.bull : value >= 60 ? TOKENS.accent : value >= 45 ? '#9AA0AC' : value >= 30 ? TOKENS.neutral : TOKENS.bear;
  return (
    <div style={{ textAlign: 'center' }}>
      <Mono style={{ fontSize: 9, color: TOKENS.textDim, display: 'block', marginBottom: 1 }}>{label}</Mono>
      <Mono style={{ fontSize: big ? 14 : 11, fontWeight: big ? 700 : 600, color: c }}>{typeof value === 'number' ? value.toFixed(big ? 1 : 0) : value}</Mono>
    </div>
  );
}

// =========== K-LINE CHART (compact 60 days) ===========
function genT5OHLC() {
  const out = [];
  let p = 880;
  const start = new Date('2026-02-26');
  let d = new Date(start);
  for (let i = 0; i < 60; i++) {
    while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
    const r = Math.sin(i * 0.32) * 0.6 + Math.sin(i * 0.11) * 0.9 + (Math.random() - 0.5) * 1.0;
    const ch = 0.005 + r * 0.025;
    const o = p;
    const c = +(o * (1 + ch)).toFixed(2);
    const h = +(Math.max(o, c) * (1 + Math.random() * 0.014)).toFixed(2);
    const l = +(Math.min(o, c) * (1 - Math.random() * 0.014)).toFixed(2);
    out.push({ d: d.toISOString().slice(5, 10), o, h, l, c });
    p = c;
    d.setDate(d.getDate() + 1);
  }
  // Ensure the last close is around 1008 to match card data
  out[out.length - 1].c = 1008;
  out[out.length - 1].h = Math.max(out[out.length - 1].h, 1015);
  return out;
}

function sma60(arr, n) {
  return arr.map((_, i) => {
    if (i < n - 1) return null;
    let s = 0;
    for (let k = i - n + 1; k <= i; k++) s += arr[k];
    return s / n;
  });
}

function ema60(arr, n) {
  const k = 2 / (n + 1);
  const out = [];
  arr.forEach((v, i) => {
    if (i === 0) out.push(v); else out.push(v * k + out[i - 1] * (1 - k));
  });
  return out;
}

function KLineMini({ focusCode }) {
  const RAW = genT5OHLC();
  const closes = RAW.map(r => r.c);
  const ma13w = sma60(closes, 30); // shortened 13W → 30 days for the 60-day window
  const ema12 = ema60(closes, 12);
  const ema26 = ema60(closes, 26);
  const macd = ema12.map((v, i) => v - ema26[i]);
  const signal = ema60(macd, 9);
  const hist = macd.map((m, i) => m - signal[i]);

  const W = 720;
  const PRICE_H = 220;
  const MACD_H = 70;
  const LAX = 50;
  const RAX = 10;
  const TOP = 8;
  const BOT = 18;
  const PLOT_W = W - LAX - RAX;
  const COL = PLOT_W / RAW.length;
  const CANDLE_W = Math.max(2, COL * 0.6);

  const allP = [...closes, ...RAW.map(r => r.h), ...RAW.map(r => r.l)];
  const pmin = Math.min(...allP) * 0.985;
  const pmax = Math.max(...allP) * 1.015;
  const macdAbs = Math.max(...macd.map(Math.abs), ...signal.map(v => Math.abs(v || 0)));

  const scalePrice = v => TOP + (1 - (v - pmin) / (pmax - pmin)) * (PRICE_H - TOP - BOT);
  const scaleMacd  = v => TOP + (1 - (v + macdAbs) / (2 * macdAbs)) * (MACD_H - TOP - BOT);

  const linePath = (arr, scale) => {
    let d = '';
    let started = false;
    arr.forEach((v, i) => {
      if (v == null) return;
      const x = LAX + i * COL + COL / 2;
      const y = scale(v);
      if (!started) { d += `M ${x} ${y}`; started = true; } else d += ` L ${x} ${y}`;
    });
    return d;
  };

  const costLine = 850;
  const yCost = scalePrice(costLine);

  // Golden / death crosses
  const crosses = [];
  for (let i = 1; i < macd.length; i++) {
    if (macd[i - 1] <= signal[i - 1] && macd[i] > signal[i]) crosses.push({ i, golden: true });
    if (macd[i - 1] >= signal[i - 1] && macd[i] < signal[i]) crosses.push({ i, golden: false });
  }

  return (
    <Card pad={14}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>K线 · {focusCode || '300308'} 中际旭创</div>
          <div style={{ fontSize: 10, color: TOKENS.textMuted, marginTop: 2 }}>近 60 个交易日 · 日K + MA30 + MACD · 成本线虚线</div>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['1M', '3M', '6M'].map((r, i) => (
            <span key={r} style={{
              padding: '3px 9px',
              fontSize: 10,
              background: i === 1 ? TOKENS.accent + '22' : 'transparent',
              color: i === 1 ? TOKENS.accent : TOKENS.textMuted,
              border: `1px solid ${i === 1 ? TOKENS.accent + '55' : TOKENS.border}`,
              borderRadius: 3,
              fontFamily: 'JetBrains Mono, monospace',
              cursor: 'pointer',
            }}>{r}</span>
          ))}
        </div>
      </div>

      <svg width={W} height={PRICE_H + MACD_H + 6} style={{ display: 'block' }}>
        {/* Price pane */}
        <rect x={LAX} y={0} width={PLOT_W} height={PRICE_H} fill={TOKENS.surfaceAlt} />
        {/* grid + price labels */}
        {[0.25, 0.5, 0.75].map(t => (
          <line key={t} x1={LAX} x2={W - RAX} y1={TOP + t * (PRICE_H - TOP - BOT)} y2={TOP + t * (PRICE_H - TOP - BOT)} stroke="rgba(255,255,255,0.04)" />
        ))}
        {[0, 0.5, 1].map((t, i) => {
          const v = pmax - t * (pmax - pmin);
          const y = TOP + t * (PRICE_H - TOP - BOT);
          return <text key={i} x={LAX - 6} y={y + 3} fontSize="9" fill={TOKENS.textDim} textAnchor="end" fontFamily="JetBrains Mono">{v.toFixed(0)}</text>;
        })}
        {/* Cost basis dashed line */}
        <line x1={LAX} x2={W - RAX} y1={yCost} y2={yCost} stroke={TOKENS.textMuted} strokeWidth="1" strokeDasharray="4 4" />
        <rect x={W - RAX - 70} y={yCost - 8} width="62" height="14" rx="2" fill={TOKENS.surface} stroke={TOKENS.textMuted} />
        <text x={W - RAX - 39} y={yCost + 3} fontSize="9" fill={TOKENS.textMuted} textAnchor="middle" fontFamily="JetBrains Mono">成本 ¥{costLine}</text>

        {/* MA30 line */}
        <path d={linePath(ma13w, scalePrice)} stroke={TOKENS.neutral} strokeWidth="1.4" fill="none" />

        {/* Candles */}
        {RAW.map((r, i) => {
          const x = LAX + i * COL + (COL - CANDLE_W) / 2;
          const xMid = LAX + i * COL + COL / 2;
          const up = r.c >= r.o;
          const c = up ? TOKENS.bull : TOKENS.bear;
          const yH = scalePrice(r.h);
          const yL = scalePrice(r.l);
          const yO = scalePrice(r.o);
          const yC = scalePrice(r.c);
          const top = Math.min(yO, yC);
          const bh = Math.max(1, Math.abs(yC - yO));
          return (
            <g key={i}>
              <line x1={xMid} y1={yH} x2={xMid} y2={yL} stroke={c} strokeWidth="1" />
              <rect x={x} y={top} width={CANDLE_W} height={bh} fill={up ? 'transparent' : c} stroke={c} strokeWidth="1" />
            </g>
          );
        })}
        <rect x={LAX} y={0} width={PLOT_W} height={PRICE_H} fill="none" stroke={TOKENS.border} />
        <text x={LAX + 6} y={14} fontSize="10" fill={TOKENS.textMuted} fontFamily="Noto Sans SC">价格 (¥)</text>

        {/* MACD pane */}
        <g transform={`translate(0, ${PRICE_H + 6})`}>
          <rect x={LAX} y={0} width={PLOT_W} height={MACD_H} fill={TOKENS.surfaceAlt} />
          <line x1={LAX} x2={W - RAX} y1={scaleMacd(0)} y2={scaleMacd(0)} stroke="rgba(255,255,255,0.2)" />
          {/* histogram */}
          {hist.map((v, i) => {
            if (v == null) return null;
            const x = LAX + i * COL + (COL - CANDLE_W) / 2;
            const y0 = scaleMacd(0);
            const y1 = scaleMacd(v);
            const top = Math.min(y0, y1);
            const h = Math.max(1, Math.abs(y1 - y0));
            const pos = v >= 0;
            return <rect key={i} x={x} y={top} width={CANDLE_W} height={h} fill={pos ? `${TOKENS.bull}88` : `${TOKENS.bear}88`} />;
          })}
          <path d={linePath(macd, scaleMacd)} stroke={TOKENS.bull} strokeWidth="1.3" fill="none" />
          <path d={linePath(signal, scaleMacd)} stroke={TOKENS.bear} strokeWidth="1.3" fill="none" strokeDasharray="3 2" />
          {crosses.map((c, k) => (
            <circle key={k}
              cx={LAX + c.i * COL + COL / 2}
              cy={scaleMacd(macd[c.i])}
              r="3.5"
              fill={c.golden ? TOKENS.bull : TOKENS.bear}
              stroke="#fff" strokeWidth="1" />
          ))}
          <rect x={LAX} y={0} width={PLOT_W} height={MACD_H} fill="none" stroke={TOKENS.border} />
          <text x={LAX + 6} y={11} fontSize="9" fill={TOKENS.textMuted} fontFamily="Noto Sans SC">MACD (12,26,9)</text>
          {/* X labels */}
          {[0, 15, 30, 45, 59].map(i => (
            <text key={i} x={LAX + i * COL + COL / 2} y={MACD_H - 4} fontSize="8" fill={TOKENS.textDim} fontFamily="JetBrains Mono" textAnchor="middle">{RAW[i].d}</text>
          ))}
        </g>
      </svg>
    </Card>
  );
}

// =========== CHIP DISTRIBUTION (筹码分布) ===========
function ChipDistribution({ focusCode }) {
  // Bell-curve centered ~5% above current price (1058)
  const currentPrice = 1008;
  const costBasis = 850;
  const buckets = [];
  const center = 1058;
  const sigma = 70;
  const minP = 780, maxP = 1180;
  const step = 12; // ~33 buckets
  for (let p = minP; p <= maxP; p += step) {
    const pct = Math.exp(-Math.pow(p - center, 2) / (2 * sigma * sigma)) * 6.5; // peak ~6.5%
    buckets.push({ price: p, pct });
  }
  // Normalize so sum ~100%
  const sum = buckets.reduce((s, b) => s + b.pct, 0);
  buckets.forEach(b => b.pct = (b.pct / sum) * 100);

  const W = 380, H = 320;
  const TOP = 10, BOT = 26;
  const LAX = 50;
  const PLOT_W = W - LAX - 14;
  const maxPct = Math.max(...buckets.map(b => b.pct)) * 1.05;
  const yAt = p => TOP + (1 - (p - minP) / (maxP - minP)) * (H - TOP - BOT);
  const barH = Math.max(2, ((H - TOP - BOT) / buckets.length) - 1);

  // Compute zone percentages
  const aboveCurrent = buckets.filter(b => b.price > currentPrice).reduce((s, b) => s + b.pct, 0);
  const winning = buckets.filter(b => b.price > costBasis && b.price <= currentPrice).reduce((s, b) => s + b.pct, 0);
  const losing = buckets.filter(b => b.price <= costBasis).reduce((s, b) => s + b.pct, 0);
  // Concentration: peak / total
  const peak = Math.max(...buckets.map(b => b.pct));
  const concentration = peak * 4.5; // proxy

  const zoneColor = price => {
    if (price > currentPrice) return TOKENS.textDim;
    if (price > costBasis)    return TOKENS.bull;
    return TOKENS.bear;
  };
  const zoneAlpha = price => {
    if (price > currentPrice) return 0.28;
    if (price > costBasis)    return 0.55;
    return 0.55;
  };

  return (
    <Card pad={14}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>筹码分布</div>
          <div style={{ fontSize: 10, color: TOKENS.textMuted, marginTop: 2 }}>按价位累计成交量分布</div>
        </div>
        <Mono style={{ fontSize: 9, color: TOKENS.textDim }}>{focusCode || '300308'}</Mono>
      </div>

      <svg width={W} height={H} style={{ display: 'block' }}>
        {/* background plot area */}
        <rect x={LAX} y={0} width={PLOT_W} height={H - BOT} fill={TOKENS.surfaceAlt} />

        {/* Y-axis price labels */}
        {[minP, 850, 900, 1008, 1058, 1100, maxP].map((p, i) => {
          const y = yAt(p);
          const isKey = p === currentPrice || p === costBasis;
          return (
            <g key={i}>
              <line x1={LAX - 4} x2={LAX} y1={y} y2={y} stroke={TOKENS.textDim} />
              <text x={LAX - 6} y={y + 3} fontSize="9" fill={isKey ? TOKENS.text : TOKENS.textDim} textAnchor="end" fontFamily="JetBrains Mono">¥{p}</text>
            </g>
          );
        })}

        {/* X-axis ticks */}
        {[0, 2, 4, 6].map(v => {
          const x = LAX + (v / maxPct) * PLOT_W;
          return (
            <g key={v}>
              <line x1={x} x2={x} y1={H - BOT} y2={H - BOT + 3} stroke={TOKENS.textDim} />
              <text x={x} y={H - BOT + 13} fontSize="9" fill={TOKENS.textDim} textAnchor="middle" fontFamily="JetBrains Mono">{v}%</text>
            </g>
          );
        })}
        <text x={LAX + PLOT_W / 2} y={H - 4} fontSize="9" fill={TOKENS.textMuted} textAnchor="middle" fontFamily="Noto Sans SC">持仓占比</text>

        {/* Bars */}
        {buckets.map((b, i) => {
          const w = (b.pct / maxPct) * PLOT_W;
          const y = yAt(b.price) - barH / 2;
          const c = zoneColor(b.price);
          const a = zoneAlpha(b.price);
          return <rect key={i} x={LAX} y={y} width={w} height={barH} fill={c} fillOpacity={a} />;
        })}

        {/* Cost basis line */}
        <line x1={LAX} x2={LAX + PLOT_W} y1={yAt(costBasis)} y2={yAt(costBasis)} stroke={TOKENS.textMuted} strokeWidth="1" strokeDasharray="3 3" />
        <rect x={LAX + PLOT_W - 70} y={yAt(costBasis) - 8} width="64" height="14" rx="2" fill={TOKENS.surface} stroke={TOKENS.textMuted} />
        <text x={LAX + PLOT_W - 38} y={yAt(costBasis) + 3} fontSize="9" fill={TOKENS.textMuted} textAnchor="middle" fontFamily="JetBrains Mono">成本 ¥{costBasis}</text>

        {/* Current price line (red) */}
        <line x1={LAX} x2={LAX + PLOT_W} y1={yAt(currentPrice)} y2={yAt(currentPrice)} stroke={TOKENS.bear} strokeWidth="1.2" strokeDasharray="4 3" />
        <rect x={LAX + PLOT_W - 70} y={yAt(currentPrice) - 8} width="64" height="14" rx="2" fill={TOKENS.surface} stroke={TOKENS.bear} />
        <text x={LAX + PLOT_W - 38} y={yAt(currentPrice) + 3} fontSize="9" fill={TOKENS.bear} textAnchor="middle" fontFamily="JetBrains Mono" fontWeight="600">现价 ¥{currentPrice}</text>

        {/* Border */}
        <rect x={LAX} y={0} width={PLOT_W} height={H - BOT} fill="none" stroke={TOKENS.border} />
      </svg>

      {/* Metric chips */}
      <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, paddingTop: 10, borderTop: `1px solid ${TOKENS.border}` }}>
        <ChipMetric label="筹码集中度" value={`${concentration.toFixed(1)}%`} tone="text" />
        <ChipMetric label="获利盘" value={`${winning.toFixed(1)}%`} tone="bull" />
        <ChipMetric label="套牢/解套压力" value={`${aboveCurrent.toFixed(1)}%`} tone="neutral" />
      </div>

      {/* legend */}
      <div style={{ marginTop: 8, display: 'flex', gap: 10, fontSize: 10, color: TOKENS.textMuted }}>
        <LegSwatch c={TOKENS.bear}    a={0.55} label="亏损筹码" />
        <LegSwatch c={TOKENS.bull}    a={0.55} label="获利筹码" />
        <LegSwatch c={TOKENS.textDim} a={0.28} label="解套压力" />
      </div>
    </Card>
  );
}

function ChipMetric({ label, value, tone }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : tone === 'neutral' ? TOKENS.neutral : TOKENS.text;
  return (
    <div style={{ background: TOKENS.surfaceAlt, borderRadius: 4, padding: '6px 8px', textAlign: 'center' }}>
      <Mono style={{ fontSize: 9, color: TOKENS.textDim, display: 'block' }}>{label}</Mono>
      <Mono style={{ fontSize: 13, fontWeight: 600, color: c, display: 'block', marginTop: 1 }}>{value}</Mono>
    </div>
  );
}

function LegSwatch({ c, a, label }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <span style={{ width: 10, height: 6, background: c, opacity: a, borderRadius: 1 }} />
      {label}
    </span>
  );
}

// =========== OPERATION LIST ===========
const OPERATIONS = [
  { action: 'sell', actionLabel: '卖出', tone: 'bear', code: '300308', name: '中际旭创', qty: 30, price: 1008.00, reason: '占比 11.07% 超阈值, 减仓至 8%', status: 'executable' },
  { action: 'buy',  actionLabel: '买入', tone: 'bull', code: '688981', name: '中芯国际', qty: 20, price: 52.40,  reason: '占比 4.4% 低于目标 6%, 国产替代催化',     status: 'executable' },
  { action: 'buy',  actionLabel: '买入', tone: 'bull', code: '002179', name: '中航光电', qty: 10, price: 62.05,  reason: '弹性目标占用 · 浮盈良好可加仓',         status: 'executable' },
  { action: 'sell', actionLabel: '减仓', tone: 'bear', code: '300474', name: '景嘉微',   qty: 20, price: 35.40,  reason: '位低补足后短期回调',                   status: 't1_locked' },
];

function OperationList() {
  const executable = OPERATIONS.filter(o => o.status === 'executable');
  const projectedElastic = 27.4;
  const currentElastic = 32.5;

  return (
    <Card pad={0}>
      <div style={{
        padding: '12px 16px', borderBottom: `1px solid ${TOKENS.border}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>今日可执行操作清单</div>
          <Mono style={{ fontSize: 11, color: TOKENS.textDim, marginTop: 2, display: 'block' }}>T+1 锁仓股已标记 · 仅 {executable.length} 项可立即下单</Mono>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={{
            background: 'transparent',
            border: `1px solid ${TOKENS.border}`,
            color: TOKENS.textMuted,
            padding: '6px 12px',
            borderRadius: 4,
            fontSize: 11,
            fontFamily: 'inherit',
            cursor: 'pointer',
          }}>导出清单</button>
          <button style={{
            background: TOKENS.accent,
            border: 'none',
            color: '#fff',
            padding: '6px 14px',
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 600,
            fontFamily: 'inherit',
            cursor: 'pointer',
          }}>保存调仓记录</button>
        </div>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: TOKENS.surfaceAlt }}>
            <Otd head>操作</Otd>
            <Otd head>股票</Otd>
            <Otd head align="right">数量</Otd>
            <Otd head align="right">参考价</Otd>
            <Otd head align="right">预计金额</Otd>
            <Otd head>依据</Otd>
            <Otd head align="right">状态</Otd>
          </tr>
        </thead>
        <tbody>
          {OPERATIONS.map((op, i) => {
            const amt = op.qty * op.price * 100; // 1 手 = 100 股
            const locked = op.status === 't1_locked';
            const c = op.tone === 'bull' ? TOKENS.bull : TOKENS.bear;
            return (
              <tr key={i} style={{
                borderTop: `1px solid ${TOKENS.border}`,
                background: locked ? 'rgba(245,166,35,0.06)' : 'transparent',
                opacity: locked ? 0.7 : 1,
              }}>
                <Otd>
                  <span style={{
                    padding: '2px 8px',
                    background: c + '22',
                    border: `1px solid ${c}55`,
                    color: c,
                    borderRadius: 3,
                    fontSize: 11,
                    fontWeight: 600,
                  }}>{op.actionLabel}</span>
                </Otd>
                <Otd>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span style={{ fontWeight: 500 }}>{op.name}</span>
                    <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{op.code}</Mono>
                  </div>
                </Otd>
                <Otd align="right"><Mono>{op.qty} 手</Mono></Otd>
                <Otd align="right"><Mono>¥{op.price.toFixed(2)}</Mono></Otd>
                <Otd align="right"><Mono style={{ fontWeight: 600 }}>¥{amt.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}</Mono></Otd>
                <Otd><span style={{ fontSize: 11, color: TOKENS.textMuted }}>{op.reason}</span></Otd>
                <Otd align="right">
                  {locked ? (
                    <span style={{
                      padding: '2px 7px',
                      background: TOKENS.neutral + '1A',
                      border: `1px solid ${TOKENS.neutral}44`,
                      color: TOKENS.neutral,
                      borderRadius: 3,
                      fontSize: 10,
                      fontWeight: 600,
                    }}>T+1 锁定</span>
                  ) : (
                    <span style={{
                      padding: '2px 7px',
                      background: TOKENS.bull + '1A',
                      border: `1px solid ${TOKENS.bull}44`,
                      color: TOKENS.bull,
                      borderRadius: 3,
                      fontSize: 10,
                      fontWeight: 600,
                    }}>可执行</span>
                  )}
                </Otd>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div style={{
        padding: '12px 16px',
        borderTop: `1px solid ${TOKENS.border}`,
        background: TOKENS.surfaceAlt,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>
          预计调仓后弹性仓位:
          <Mono style={{ color: TOKENS.text, fontWeight: 600, marginLeft: 6 }}>{currentElastic}%</Mono>
          <span style={{ color: TOKENS.textDim, margin: '0 6px' }}>→</span>
          <Mono style={{ color: TOKENS.bull, fontWeight: 600 }}>{projectedElastic}%</Mono>
        </Mono>
        <Tag tone="bull">回归目标区间 (33% ±5%)</Tag>
        <div style={{ flex: 1 }} />
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>总成交额 ¥{(executable.reduce((s, o) => s + o.qty * o.price * 100, 0)).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}</Mono>
      </div>
    </Card>
  );
}

function Otd({ children, align = 'left', head }) {
  if (head) {
    return <th style={{
      textAlign: align,
      padding: '9px 14px',
      fontWeight: 500,
      fontSize: 10,
      color: TOKENS.textMuted,
      letterSpacing: '0.06em',
      textTransform: 'uppercase',
      fontFamily: 'JetBrains Mono, monospace',
    }}>{children}</th>;
  }
  return <td style={{ textAlign: align, padding: '9px 14px', fontSize: 13, verticalAlign: 'middle' }}>{children}</td>;
}

// =========== HISTORY (collapsible) ===========
const T5_HISTORY = [
  { d: '2026-05-14', op: '加仓', stock: '澜起科技', qty: '+20 手', outcome: '+1.4% 浮盈' },
  { d: '2026-05-09', op: '止损', stock: 'TCL中环',   qty: '清仓',   outcome: '-12.3% 实现亏损' },
  { d: '2026-05-02', op: '加仓', stock: '中芯国际', qty: '+15 手', outcome: '盈亏中性' },
  { d: '2026-04-29', op: '加仓', stock: '中芯国际', qty: '+20 手', outcome: '+2.1%' },
  { d: '2026-04-23', op: '减仓', stock: '亨通光电', qty: '-30 手', outcome: '+0.8% 出仓' },
];

function HistoryT5() {
  const [open, setOpen] = useT5(false);
  return (
    <Card pad={0}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%',
          padding: '12px 16px',
          background: 'transparent',
          border: 'none',
          color: TOKENS.text,
          fontFamily: 'inherit',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <span style={{
          color: TOKENS.textMuted,
          fontSize: 12,
          transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
          transition: 'transform 160ms',
          display: 'inline-block',
        }}>▸</span>
        <span style={{ fontSize: 13, fontWeight: 600 }}>历史调仓记录</span>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>近 30 日 · {T5_HISTORY.length} 起</Mono>
        <div style={{ flex: 1 }} />
        <Mono style={{ fontSize: 10, color: TOKENS.textMuted }}>{open ? '收起' : '展开'} ↗</Mono>
      </button>
      {open && (
        <div style={{ padding: '0 16px 14px 16px' }}>
          <div style={{ borderTop: `1px solid ${TOKENS.border}`, paddingTop: 10 }}>
            {T5_HISTORY.map((e, i) => (
              <div key={i} style={{
                display: 'grid',
                gridTemplateColumns: '90px 70px 1fr 100px 1fr',
                gap: 10, alignItems: 'center',
                padding: '8px 0',
                borderBottom: i < T5_HISTORY.length - 1 ? `1px dashed ${TOKENS.border}` : 'none',
                fontSize: 12,
              }}>
                <Mono style={{ color: TOKENS.textMuted }}>{e.d}</Mono>
                <Tag>{e.op}</Tag>
                <span>{e.stock}</span>
                <Mono style={{ textAlign: 'right' }}>{e.qty}</Mono>
                <Mono style={{ color: TOKENS.textMuted, fontSize: 11 }}>{e.outcome}</Mono>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

// =========== TAB 5 ROOT ===========
function Tab5Rebalance() {
  const [focused, setFocused] = useT5('300308');
  const selectedCount = HELD_POOL.filter(s => s.selected).length + WATCHLIST_POOL.filter(s => s.selected).length;

  return (
    <div style={{
      width: 1280,
      background: TOKENS.bg,
      color: TOKENS.text,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <GlobalActionBar activeTab={4} marketStatus="live" />

      <div style={{ padding: 24, boxSizing: 'border-box', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* ROW 1 — header */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          paddingBottom: 12,
          borderBottom: `1px solid ${TOKENS.border}`,
        }}>
          <div>
            <Mono style={{ fontSize: 10, color: TOKENS.textDim, letterSpacing: '0.16em' }}>TAB 05</Mono>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 2 }}>
              <div style={{ fontSize: 22, fontWeight: 600 }}>调仓分析</div>
              <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>
                T+1 settlement · 多股对比 · 今日可执行清单
              </Mono>
            </div>
          </div>
          <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>分析于 2026-05-20 14:32 · 收盘前 45 分钟</Mono>
        </div>

        {/* ROW 2 — Stock selector */}
        <StockSelectorPanel selectedCount={selectedCount} />

        {/* ROW 3 SECTION A — Analysis cards */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
            <Mono style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.08em' }}>A · 调仓建议摘要 · {ANALYSIS_CARDS.length} 个标的</Mono>
            <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>横向滚动 · 点击聚焦 K线 / 筹码</Mono>
          </div>
          <div style={{
            display: 'flex',
            gap: 12,
            overflowX: 'auto',
            paddingBottom: 4,
          }}>
            {ANALYSIS_CARDS.map(c => (
              <AnalysisCard
                key={c.code}
                card={c}
                focused={c.code === focused}
                onClick={() => setFocused(c.code)}
              />
            ))}
          </div>
        </div>

        {/* SECTION B — K-line + chip distribution */}
        <div>
          <Mono style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.08em', display: 'block', marginBottom: 8 }}>
            B · 聚焦标的 · 技术面 + 筹码分布 · {focused}
          </Mono>
          <div style={{ display: 'grid', gridTemplateColumns: '1.85fr 1fr', gap: 12 }}>
            <KLineMini focusCode={focused} />
            <ChipDistribution focusCode={focused} />
          </div>
        </div>

        {/* SECTION C — Operation list */}
        <div>
          <Mono style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.08em', display: 'block', marginBottom: 8 }}>
            C · 今日可操作建议 · T+1 锁仓已计入
          </Mono>
          <OperationList />
        </div>

        {/* SECTION D — History (collapsed) */}
        <HistoryT5 />

        {/* Footer */}
        <div style={{
          marginTop: 4, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`,
          display: 'flex', justifyContent: 'space-between',
          fontSize: 10, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace',
        }}>
          <span>仅供模拟分析 · 真实下单请通过券商客户端</span>
          <span>engine/portfolio.py · T+1 lot tracking · chip_dist_v1</span>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Tab5Rebalance, ChipDistribution, KLineMini, AnalysisCard });
