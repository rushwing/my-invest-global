/* global React, TOKENS, Card, Mono, Tag, SignalBadge, GlobalActionBar */
const { useState: useT1V2 } = React;

// =========== T+1 AVAILABILITY BADGE (reusable) ===========
function T1Badge({ status, availableQty, totalQty, tomorrow }) {
  // status: 'bought_today' | 'partial' | 'all_available'
  if (status === 'bought_today') {
    return (
      <span
        title={`今日买入 · ${tomorrow || '明日'}可操作`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '2px 7px',
          background: TOKENS.neutral + '22',
          border: `1px solid ${TOKENS.neutral}66`,
          color: TOKENS.neutral,
          borderRadius: 4,
          fontSize: 10,
          fontWeight: 600,
          fontFamily: '"Noto Sans SC", sans-serif',
        }}
      >
        <svg width="9" height="9" viewBox="0 0 12 12" fill="none">
          <rect x="2.5" y="5" width="7" height="5" rx="0.8" fill={TOKENS.neutral} />
          <path d="M4 5 V3.5 a2 2 0 0 1 4 0 V5" stroke={TOKENS.neutral} strokeWidth="1.2" fill="none" />
        </svg>
        今日买入
      </span>
    );
  }
  if (status === 'partial') {
    const pct = (availableQty / totalQty) * 100;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'flex-end' }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '2px 7px',
          background: TOKENS.bull + '1A',
          border: `1px solid ${TOKENS.bull}55`,
          color: TOKENS.bull,
          borderRadius: 4,
          fontSize: 10,
          fontWeight: 600,
          fontFamily: '"Noto Sans SC", sans-serif',
        }}>
          {availableQty}/{totalQty} 手可用
        </span>
        <div style={{ width: 60, height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 1.5 }}>
          <div style={{ width: `${pct}%`, height: '100%', background: TOKENS.bull, borderRadius: 1.5 }} />
        </div>
      </div>
    );
  }
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 3,
      padding: '2px 7px',
      background: TOKENS.bull + '14',
      border: `1px solid ${TOKENS.bull}44`,
      color: TOKENS.bull,
      borderRadius: 4,
      fontSize: 10,
      fontWeight: 500,
      fontFamily: '"Noto Sans SC", sans-serif',
    }}>
      <span style={{ width: 4, height: 4, borderRadius: '50%', background: TOKENS.bull }} />
      全部可用
    </span>
  );
}

// =========== SAMPLE DATA (8 holdings with varied states) ===========
const T1_HOLDINGS = [
  // Selected row + dirty
  { code: '300308', name: '中际旭创', cat: '弹性股', cost: 850.00, price: 1008.00, qty: 100, t1: 'all_available', selected: true, dirty: ['price'] },
  // Normal positive
  { code: '002415', name: '海康威视', cat: '白马股', cost: 28.50,  price: 30.00,   qty: 700, t1: 'all_available' },
  // STOP LOSS row + partial T+1
  { code: '688981', name: '中芯国际', cat: '弹性股', cost: 65.00,  price: 52.40,   qty: 800, t1: 'partial', t1Avail: 500, t1Total: 800, stopLoss: true },
  // Bought today (T+1 locked)
  { code: '300474', name: '景嘉微',   cat: '弹性股', cost: 35.20,  price: 35.40,   qty: 200, t1: 'bought_today', dirty: ['qty'] },
  // Watchlist row (自选, not yet held — qty 0)
  { code: '000333', name: '美的集团', cat: '自选',   cost: 0,      price: 76.40,   qty: 0,   t1: null, watchlist: true },
  // Normal positive elastic
  { code: '002179', name: '中航光电', cat: '弹性股', cost: 55.20,  price: 62.05,   qty: 1000, t1: 'all_available' },
  // Neutral baima
  { code: '600036', name: '招商银行', cat: '白马股', cost: 38.20,  price: 37.74,   qty: 2000, t1: 'all_available' },
  // Negative baima
  { code: '600519', name: '贵州茅台', cat: '白马股', cost: 1820.00, price: 1857.00, qty: 100, t1: 'all_available' },
];

const FILTER_PILLS = ['全部', '白马股', '弹性股', '自选'];

const fmtMoney = (n) => '¥' + n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
const fmtPrice = (n) => '¥' + n.toFixed(2);

function pnlPct(cost, price) {
  if (!cost) return 0;
  return (price - cost) / cost * 100;
}

// =========== KPI ROW ===========
function KpiRow({ totalMV, baimaPct, elasticPct, baimaMV, elasticMV, dirtyCount, pnlPct: totalPnl, profitAmt }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
      <KpiCard
        label="组合总市值"
        big={fmtMoney(totalMV)}
        sub={`累计盈亏 ¥+${profitAmt.toLocaleString('zh-CN', { maximumFractionDigits: 0 })} · ${totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}%`}
        tone="bull"
      />
      <KpiBar
        label="弹性仓位"
        pct={elasticPct}
        target={33}
        sub={`目标 33% · 偏差 ${(elasticPct - 33) >= 0 ? '+' : ''}${(elasticPct - 33).toFixed(1)}%`}
        amount={fmtMoney(elasticMV)}
      />
      <KpiBar
        label="白马仓位"
        pct={baimaPct}
        target={67}
        sub={`目标 67% · 偏差 ${(baimaPct - 67) >= 0 ? '+' : ''}${(baimaPct - 67).toFixed(1)}%`}
        amount={fmtMoney(baimaMV)}
      />
    </div>
  );
}

function KpiCard({ label, big, sub, tone }) {
  const c = tone === 'bull' ? TOKENS.bull : TOKENS.text;
  return (
    <div style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 8, padding: 12 }}>
      <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 6 }}>{label}</div>
      <Mono style={{ fontSize: 22, fontWeight: 600, color: c, display: 'block', lineHeight: 1.1, marginBottom: 4 }}>{big}</Mono>
      <Mono style={{ fontSize: 10, color: TOKENS.textDim, display: 'block' }}>{sub}</Mono>
    </div>
  );
}

function KpiBar({ label, pct, target, sub, amount }) {
  const dev = Math.abs(pct - target);
  const c = dev > 10 ? TOKENS.bear : dev > 5 ? TOKENS.neutral : TOKENS.accent;
  return (
    <div style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 8, padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <div style={{ fontSize: 11, color: TOKENS.textMuted }}>{label}</div>
        <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{amount}</Mono>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <Mono style={{ fontSize: 22, fontWeight: 600, color: c, lineHeight: 1.1 }}>{pct.toFixed(1)}%</Mono>
      </div>
      <div style={{ position: 'relative', height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, marginTop: 8, marginBottom: 6 }}>
        <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${pct}%`, background: c, borderRadius: 2 }} />
        <div style={{ position: 'absolute', left: `${target}%`, top: -2, width: 1.5, height: 8, background: '#fff' }} />
      </div>
      <Mono style={{ fontSize: 10, color: TOKENS.textDim, display: 'block' }}>{sub}</Mono>
    </div>
  );
}

// =========== DONUT (compact) ===========
function DonutMini({ baimaPct, elasticPct, totalMV }) {
  const R = 70;
  const STROKE = 18;
  const C = 2 * Math.PI * R;
  const baimaArc = (baimaPct / 100) * C;
  const dev = Math.abs(baimaPct - 67);
  const baimaColor = dev > 10 ? TOKENS.bear : dev > 5 ? TOKENS.neutral : TOKENS.accent;
  return (
    <Card pad={14}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>资产配置</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>白马 vs 弹性 · 当前 / 目标</div>
        </div>
        <Tag tone={dev > 10 ? 'bear' : dev > 5 ? 'neutral' : 'bull'}>偏差 {dev.toFixed(1)}%</Tag>
      </div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <svg width={180} height={180} viewBox="0 0 200 200">
          <circle cx="100" cy="100" r={R + 14} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="3 4" />
          <circle cx="100" cy="100" r={R} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={STROKE} />
          <circle cx="100" cy="100" r={R} fill="none" stroke="#5C616E" strokeWidth={STROKE} strokeDasharray={`${C - baimaArc} ${C}`} strokeDashoffset={-baimaArc} transform="rotate(-90 100 100)" />
          <circle cx="100" cy="100" r={R} fill="none" stroke={baimaColor} strokeWidth={STROKE} strokeDasharray={`${baimaArc} ${C}`} transform="rotate(-90 100 100)" />
          {(() => {
            const angle = (67 / 100) * 2 * Math.PI - Math.PI / 2;
            const x1 = 100 + (R - STROKE / 2 - 4) * Math.cos(angle);
            const y1 = 100 + (R - STROKE / 2 - 4) * Math.sin(angle);
            const x2 = 100 + (R + STROKE / 2 + 4) * Math.cos(angle);
            const y2 = 100 + (R + STROKE / 2 + 4) * Math.sin(angle);
            return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#fff" strokeWidth="1.5" />;
          })()}
          <text x="100" y="92" textAnchor="middle" fill={TOKENS.textMuted} fontSize="10" fontFamily="Noto Sans SC">总市值</text>
          <text x="100" y="115" textAnchor="middle" fill="#fff" fontSize="18" fontFamily="JetBrains Mono" fontWeight="600">¥{(totalMV / 10000).toFixed(1)}</text>
          <text x="100" y="130" textAnchor="middle" fill={TOKENS.textDim} fontSize="9" fontFamily="JetBrains Mono">万元</text>
        </svg>
        <div style={{ flex: 1, display: 'grid', gap: 12, fontSize: 12 }}>
          <LegRow color={baimaColor} label="白马股" pct={baimaPct} target={67} />
          <LegRow color="#5C616E" label="弹性股" pct={elasticPct} target={33} />
          <div style={{ borderTop: `1px solid ${TOKENS.border}`, paddingTop: 8, fontSize: 11, color: TOKENS.textMuted, lineHeight: 1.6 }}>
            {dev > 10 ? <span style={{ color: TOKENS.bear }}>⚠ 严重偏离 · 建议再平衡</span> :
             dev > 5  ? <span style={{ color: TOKENS.neutral }}>· 轻度偏离 · 可观察</span> :
                        <span style={{ color: TOKENS.bull }}>✓ 配置健康</span>}
          </div>
        </div>
      </div>
    </Card>
  );
}

function LegRow({ color, label, pct, target }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
        <div style={{ width: 10, height: 10, background: color, borderRadius: 2 }} />
        <span style={{ fontSize: 12, fontWeight: 500 }}>{label}</span>
        <div style={{ flex: 1 }} />
        <Mono style={{ fontSize: 13, fontWeight: 600 }}>{pct.toFixed(1)}%</Mono>
      </div>
      <Mono style={{ fontSize: 10, color: TOKENS.textDim, paddingLeft: 18 }}>目标 {target}%</Mono>
    </div>
  );
}

// =========== HEATMAP (compact, top 6) ===========
function HeatmapMini({ holdings, onSelect }) {
  const items = holdings.filter(h => h.qty > 0).slice(0, 6).map(h => ({ ...h, mv: h.price * h.qty, pnl: pnlPct(h.cost, h.price) }));
  const total = items.reduce((s, h) => s + h.mv, 0);
  return (
    <Card pad={14}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>持仓热力图</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>面积 = 市值 · 颜色 = 盈亏%</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 9, color: TOKENS.textMuted, fontFamily: 'JetBrains Mono, monospace' }}>
          <span>-20%</span>
          <div style={{ width: 80, height: 6, borderRadius: 1, background: `linear-gradient(90deg, ${TOKENS.bear}, #2a2a3a, ${TOKENS.bull})` }} />
          <span>+20%</span>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '2.2fr 1.2fr 1fr', gridTemplateRows: '1fr 1fr', gap: 4, height: 232 }}>
        {items.map((h, i) => (
          <HoldHeatCell key={h.code} h={h} mvShare={h.mv / total} onClick={() => onSelect && onSelect(h.code)} compact={i >= 2} />
        ))}
      </div>
    </Card>
  );
}

function HoldHeatCell({ h, mvShare, onClick, compact }) {
  const isPos = h.pnl >= 0;
  const t = Math.max(-1, Math.min(1, h.pnl / 20));
  const bg = isPos
    ? `rgba(0,196,122,${0.15 + Math.abs(t) * 0.55})`
    : `rgba(232,64,64,${0.15 + Math.abs(t) * 0.55})`;
  return (
    <div
      onClick={onClick}
      style={{
        background: bg,
        border: `1px solid ${isPos ? '#00C47A55' : '#E8404055'}`,
        borderRadius: 4,
        padding: compact ? '8px 10px' : '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        cursor: 'pointer',
        overflow: 'hidden',
      }}
    >
      <div>
        <div style={{ fontSize: compact ? 12 : 14, fontWeight: 600, color: '#fff' }}>{h.name}</div>
        <Mono style={{ fontSize: 9, color: 'rgba(255,255,255,0.6)' }}>{h.code}</Mono>
      </div>
      <Mono style={{ fontSize: compact ? 14 : 20, fontWeight: 600, color: '#fff', lineHeight: 1 }}>
        {isPos ? '+' : ''}{h.pnl.toFixed(2)}%
      </Mono>
    </div>
  );
}

// =========== HOLDINGS TABLE ===========
function HoldingsTableV2({ holdings, filter, onFilter, onSelect, selectedCode }) {
  const filtered = filter === '全部' ? holdings : holdings.filter(h => h.cat === filter);
  const dirtyCount = holdings.filter(h => h.dirty && h.dirty.length).length;

  return (
    <Card pad={0}>
      {/* Section header with controls */}
      <div style={{
        padding: '12px 14px',
        borderBottom: `1px solid ${TOKENS.border}`,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>自选 / 持仓</span>
          <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>{filtered.length} 行</Mono>
          {dirtyCount > 0 && (
            <span style={{
              fontSize: 10, padding: '1px 6px',
              background: TOKENS.neutral + '22',
              color: TOKENS.neutral,
              border: `1px solid ${TOKENS.neutral}55`,
              borderRadius: 3,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
            }}>已修改 {dirtyCount} 行</span>
          )}
        </div>
        <div style={{ flex: 1 }} />
        {/* Filter pills */}
        <div style={{ display: 'flex', gap: 4, marginRight: 12 }}>
          {FILTER_PILLS.map(p => (
            <button key={p}
              onClick={() => onFilter(p)}
              style={{
                padding: '4px 10px',
                fontSize: 11,
                background: filter === p ? TOKENS.accent + '22' : 'transparent',
                color: filter === p ? TOKENS.accent : TOKENS.textMuted,
                border: `1px solid ${filter === p ? TOKENS.accent + '55' : TOKENS.border}`,
                borderRadius: 4,
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}>{p}</button>
          ))}
        </div>
        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 6 }}>
          <SmallBtn icon="+">添加</SmallBtn>
          <SmallBtn icon="↑">导入 CSV</SmallBtn>
          <SmallBtn primary disabled={dirtyCount === 0} badge={dirtyCount > 0 ? String(dirtyCount) : null}>保存快照</SmallBtn>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, minWidth: 1140 }}>
          <colgroup>
            <col style={{ width: 80 }} />
            <col style={{ width: 110 }} />
            <col style={{ width: 100 }} />
            <col style={{ width: 84 }} />
            <col style={{ width: 84 }} />
            <col style={{ width: 70 }} />
            <col style={{ width: 100 }} />
            <col style={{ width: 84 }} />
            <col style={{ width: 116 }} />
            <col style={{ width: 80 }} />
          </colgroup>
          <thead>
            <tr style={{ background: TOKENS.surfaceAlt }}>
              <Th>代码</Th>
              <Th>名称</Th>
              <Th>类别</Th>
              <Th align="right">成本价</Th>
              <Th align="right">现价</Th>
              <Th align="right">数量</Th>
              <Th align="right">市值</Th>
              <Th align="right">浮盈%</Th>
              <Th align="right">T+1 可用</Th>
              <Th align="center">操作</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(h => (
              <HoldingRow key={h.code} h={h} selected={h.code === selectedCode} onClick={() => onSelect && onSelect(h.code)} />
            ))}
            <AddRow />
          </tbody>
        </table>
      </div>

      {/* Footer hint */}
      <div style={{
        padding: '8px 14px',
        borderTop: `1px solid ${TOKENS.border}`,
        fontSize: 10,
        color: TOKENS.textDim,
        fontFamily: 'JetBrains Mono, monospace',
        display: 'flex',
        justifyContent: 'space-between',
      }}>
        <span>点击单元格编辑 · 失焦提交 · Tab 跳到下一格 · 黄色 = 未保存</span>
        <span>将写入 data/agent_input/holdings_20260520.csv</span>
      </div>
    </Card>
  );
}

function Th({ children, align = 'left' }) {
  return (
    <th style={{
      textAlign: align,
      padding: '9px 10px',
      fontWeight: 500,
      fontSize: 10,
      color: TOKENS.textMuted,
      letterSpacing: '0.06em',
      textTransform: 'uppercase',
      fontFamily: 'JetBrains Mono, monospace',
    }}>{children}</th>
  );
}

function HoldingRow({ h, selected, onClick }) {
  const mv = h.price * h.qty;
  const pnl = pnlPct(h.cost, h.price);
  const pnlPos = pnl >= 0;
  const isDirty = (k) => h.dirty && h.dirty.includes(k);

  let rowBg = 'transparent';
  let borderLeft = '2px solid transparent';
  if (h.stopLoss) rowBg = 'rgba(232,64,64,0.07)';
  else if (selected) { rowBg = 'rgba(79,142,247,0.08)'; borderLeft = `2px solid ${TOKENS.accent}`; }
  else if (h.dirty && h.dirty.length) { rowBg = 'rgba(245,166,35,0.07)'; borderLeft = `2px solid ${TOKENS.neutral}`; }

  return (
    <tr
      onClick={onClick}
      style={{
        background: rowBg,
        borderTop: `1px solid ${TOKENS.border}`,
        cursor: 'pointer',
        position: 'relative',
      }}
    >
      <Td>
        <div style={{ borderLeft, paddingLeft: 8, margin: '-7px 0', padding: '7px 0 7px 8px' }}>
          <Mono style={{
            fontSize: 11,
            fontWeight: 500,
            color: TOKENS.accent,
            textDecoration: 'underline',
            textDecorationStyle: 'dotted',
            textUnderlineOffset: 2,
          }}>{h.code}</Mono>
        </div>
      </Td>
      <Td>
        <span style={{ fontWeight: 500, color: h.stopLoss ? TOKENS.bear : TOKENS.text }}>{h.name}</span>
        {h.watchlist && <Mono style={{ fontSize: 9, color: TOKENS.textDim, marginLeft: 4 }}>(自选)</Mono>}
      </Td>
      <Td>
        <CategoryPill cat={h.cat} dirty={isDirty('cat')} />
      </Td>
      <Td align="right" dirty={isDirty('cost')}>
        {h.cost ? <Mono>{fmtPrice(h.cost)}</Mono> : <span style={{ color: TOKENS.textDim }}>—</span>}
      </Td>
      <Td align="right" dirty={isDirty('price')}>
        <Mono style={{ color: h.cost && h.price >= h.cost ? TOKENS.bull : (h.cost ? TOKENS.bear : TOKENS.text) }}>{fmtPrice(h.price)}</Mono>
      </Td>
      <Td align="right" dirty={isDirty('qty')}>
        {h.qty > 0 ? <Mono>{h.qty}</Mono> : <span style={{ color: TOKENS.textDim }}>—</span>}
      </Td>
      <Td align="right">
        {mv > 0 ? <Mono style={{ color: TOKENS.textMuted }}>{fmtMoney(mv)}</Mono> : <span style={{ color: TOKENS.textDim }}>—</span>}
      </Td>
      <Td align="right">
        {h.cost ? (
          <Mono style={{ color: pnlPos ? TOKENS.bull : TOKENS.bear, fontWeight: 600 }}>{pnlPos ? '+' : ''}{pnl.toFixed(2)}%</Mono>
        ) : <span style={{ color: TOKENS.textDim }}>—</span>}
      </Td>
      <Td align="right">
        {h.t1 ? <T1Badge status={h.t1} availableQty={h.t1Avail} totalQty={h.t1Total} tomorrow="2026-05-21" /> :
                <span style={{ color: TOKENS.textDim, fontSize: 10 }}>—</span>}
      </Td>
      <Td align="center">
        <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
          <RowIcon title="编辑">✎</RowIcon>
          <RowIcon title="删除" tone="bear">×</RowIcon>
        </div>
      </Td>
    </tr>
  );
}

function Td({ children, align = 'left', dirty }) {
  return (
    <td style={{
      textAlign: align,
      padding: '7px 10px',
      fontSize: 12,
      verticalAlign: 'middle',
      position: 'relative',
      background: dirty ? 'rgba(245,166,35,0.15)' : 'transparent',
      borderTop: dirty ? `1px solid ${TOKENS.neutral}44` : undefined,
      borderBottom: dirty ? `1px solid ${TOKENS.neutral}44` : undefined,
    }}>
      {children}
      {dirty && (
        <span style={{
          position: 'absolute',
          top: 3, right: 3,
          width: 4, height: 4,
          borderRadius: '50%',
          background: TOKENS.neutral,
        }} />
      )}
    </td>
  );
}

function CategoryPill({ cat, dirty }) {
  const colors = {
    '白马股': { c: TOKENS.accent, label: '白马股' },
    '弹性股': { c: '#C792EA',    label: '弹性股' },
    '自选':   { c: TOKENS.textMuted, label: '自选' },
  };
  const cfg = colors[cat] || colors['白马股'];
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 3,
      padding: '2px 7px',
      background: cfg.c + '22',
      border: `1px solid ${cfg.c}55`,
      color: cfg.c,
      borderRadius: 3,
      fontSize: 10,
      fontWeight: 500,
      cursor: 'pointer',
    }}>
      {cfg.label}
      <span style={{ fontSize: 7, opacity: 0.7 }}>▾</span>
    </span>
  );
}

function RowIcon({ children, title, tone }) {
  const c = tone === 'bear' ? TOKENS.bear : TOKENS.textMuted;
  return (
    <span title={title} style={{
      width: 20, height: 20,
      borderRadius: 3,
      background: 'rgba(255,255,255,0.04)',
      color: c,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 12,
      cursor: 'pointer',
    }}>{children}</span>
  );
}

function AddRow() {
  return (
    <tr style={{ borderTop: `1px dashed ${TOKENS.border}` }}>
      <td colSpan={10} style={{ padding: '12px 14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            color: TOKENS.accent,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
          }}>
            <span style={{
              width: 18, height: 18,
              borderRadius: 3,
              border: `1px dashed ${TOKENS.accent}88`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12,
              color: TOKENS.accent,
            }}>+</span>
            添加持仓
          </span>
          <span style={{ fontSize: 10, color: TOKENS.textDim }}>输入 6 位代码 → 自动查找名称 → Tab 填入其余字段</span>
          <div style={{ flex: 1 }} />
          {/* Name lookup chip mock (shown while typing) */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 10px',
            background: TOKENS.surfaceAlt,
            border: `1px solid ${TOKENS.border}`,
            borderRadius: 4,
            fontSize: 11,
          }}>
            <Mono style={{ color: TOKENS.accent }}>300502</Mono>
            <span style={{ color: TOKENS.textMuted }}>→</span>
            <span style={{ color: TOKENS.text }}>新易盛</span>
            <Mono style={{ fontSize: 9, color: TOKENS.textDim }}>光通信 · Tier-1</Mono>
            <Mono style={{ fontSize: 9, color: TOKENS.bull, marginLeft: 4 }}>↵ 添加</Mono>
          </div>
        </div>
      </td>
    </tr>
  );
}

function SmallBtn({ icon, children, primary, disabled, badge }) {
  return (
    <button
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '6px 11px',
        background: primary && !disabled ? TOKENS.accent : 'transparent',
        border: `1px solid ${primary && !disabled ? TOKENS.accent : TOKENS.border}`,
        borderRadius: 4,
        color: primary && !disabled ? '#fff' : (disabled ? TOKENS.textDim : TOKENS.textMuted),
        fontSize: 11,
        fontWeight: primary ? 600 : 400,
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontFamily: 'inherit',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {icon && <span>{icon}</span>}
      {children}
      {badge && <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        minWidth: 16,
        height: 14,
        padding: '0 4px',
        background: 'rgba(255,255,255,0.2)',
        borderRadius: 7,
        fontSize: 9,
        fontWeight: 600,
        marginLeft: 2,
      }}>{badge}</span>}
    </button>
  );
}

// =========== TAB 1 V2 ROOT (with GlobalActionBar) ===========
function Tab1HoldingsV2() {
  const [filter, setFilter] = useT1V2('全部');
  const [selected, setSelected] = useT1V2('300308');

  // Aggregates
  const heldHoldings = T1_HOLDINGS.filter(h => h.qty > 0 && h.cat !== '自选');
  const totalMV = heldHoldings.reduce((s, h) => s + h.price * h.qty, 0);
  const totalCost = heldHoldings.reduce((s, h) => s + h.cost * h.qty, 0);
  const profitAmt = totalMV - totalCost;
  const totalPnl = (profitAmt / totalCost) * 100;
  const baimaMV = heldHoldings.filter(h => h.cat === '白马股').reduce((s, h) => s + h.price * h.qty, 0);
  const elasticMV = heldHoldings.filter(h => h.cat === '弹性股').reduce((s, h) => s + h.price * h.qty, 0);
  const baimaPct = (baimaMV / totalMV) * 100;
  const elasticPct = (elasticMV / totalMV) * 100;

  return (
    <div style={{
      width: 1280,
      background: TOKENS.bg,
      color: TOKENS.text,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Global header */}
      <GlobalActionBar activeTab={0} marketStatus="live" />

      <div style={{ padding: 24, boxSizing: 'border-box', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* ROW 1 — Page header strip (slim, no refresh/run — those moved to global bar) */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          paddingBottom: 12,
          borderBottom: `1px solid ${TOKENS.border}`,
        }}>
          <div>
            <Mono style={{ fontSize: 10, color: TOKENS.textDim, letterSpacing: '0.16em' }}>TAB 01</Mono>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 2 }}>
              <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.01em' }}>持仓总览</div>
              <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>2026-05-20 · {heldHoldings.length} 持仓 · 监控 光通信 / 半导体 / 算力</Mono>
            </div>
          </div>
          <div style={{ fontSize: 10, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace' }}>
            数据时效 HIGH · 缓存 14:32
          </div>
        </div>

        {/* ROW 2 — KPI */}
        <KpiRow
          totalMV={totalMV}
          baimaPct={baimaPct}
          elasticPct={elasticPct}
          baimaMV={baimaMV}
          elasticMV={elasticMV}
          pnlPct={totalPnl}
          profitAmt={profitAmt}
        />

        {/* ROW 3 — Donut + Heatmap */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.22fr 1fr', gap: 12 }}>
          <DonutMini baimaPct={baimaPct} elasticPct={elasticPct} totalMV={totalMV} />
          <HeatmapMini holdings={T1_HOLDINGS} onSelect={setSelected} />
        </div>

        {/* ROW 4+5 — Holdings table */}
        <HoldingsTableV2
          holdings={T1_HOLDINGS}
          filter={filter}
          onFilter={setFilter}
          onSelect={setSelected}
          selectedCode={selected}
        />

        {/* Footer */}
        <div style={{
          marginTop: 4, paddingTop: 12, borderTop: `1px solid ${TOKENS.border}`,
          display: 'flex', justifyContent: 'space-between',
          fontSize: 10, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace',
        }}>
          <span>my-invest-global · personal · A-share AI infra portfolio</span>
          <span>holdings.csv → engine/portfolio.py → signals_*.json</span>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Tab1HoldingsV2, T1Badge, T1_HOLDINGS });
