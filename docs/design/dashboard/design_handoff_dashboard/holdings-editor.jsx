/* global React, TOKENS, SIGNAL, Card, Mono, SignalBadge, Tag, HOLDINGS, HoldingsHeatmap */
const { useState: useStateE } = React;

// =========== EDITOR DATA ===========
const EDITOR_HOLDINGS = [
  { code: '300308', name: '中际旭创', cat: '弹性股', cost: 850.00, price: 1008.00, qty: 100, dirty: ['price'] },
  { code: '002415', name: '海康威视', cat: '白马股', cost: 28.50,  price: 30.00,   qty: 700, dirty: [] },
  { code: '688981', name: '中芯国际', cat: '弹性股', cost: 62.00,  price: 59.83,   qty: 800, dirty: ['qty'] },
];

const SOURCE_STATES = {
  manual: { label: '手动编辑', color: TOKENS.accent },
  csv:    { label: 'CSV 导入', color: TOKENS.bull },
  ocr:    { label: 'OCR 待校正', color: TOKENS.neutral },
};

// =========== COLLAPSED RAIL (32px) ===========
function SidebarCollapsed({ onExpand }) {
  return (
    <div style={{
      width: 32,
      background: TOKENS.surfaceAlt,
      borderRight: `1px solid ${TOKENS.border}`,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      paddingTop: 12,
      gap: 14,
      flexShrink: 0,
    }}>
      <button
        onClick={onExpand}
        title="展开持仓编辑器"
        style={{
          width: 24, height: 24,
          background: TOKENS.accent + '22',
          border: `1px solid ${TOKENS.accent}55`,
          borderRadius: 4,
          color: TOKENS.accent,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 13,
          padding: 0,
        }}
      >⟩</button>
      <div style={{
        writingMode: 'vertical-rl',
        textOrientation: 'mixed',
        fontSize: 12,
        fontWeight: 600,
        color: TOKENS.text,
        letterSpacing: '0.2em',
        marginTop: 4,
        userSelect: 'none',
      }}>持仓编辑</div>
      <div style={{ flex: 1 }} />
      {/* count badge */}
      <div style={{
        marginBottom: 14,
        writingMode: 'vertical-rl',
        textOrientation: 'mixed',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 10,
        color: TOKENS.textDim,
        letterSpacing: '0.1em',
      }}>3 持仓 · 已修改</div>
      <div style={{
        width: 6, height: 6,
        borderRadius: '50%',
        background: TOKENS.neutral,
        marginBottom: 14,
      }} title="有未保存修改" />
    </div>
  );
}

// =========== EXPANDED PANEL (420px) ===========
function SidebarExpanded({ onCollapse, importOpen, setImportOpen }) {
  const totalMV = EDITOR_HOLDINGS.reduce((s, h) => s + h.price * h.qty, 0);
  const baimaMV = EDITOR_HOLDINGS.filter(h => h.cat === '白马股').reduce((s, h) => s + h.price * h.qty, 0);
  const elasticMV = EDITOR_HOLDINGS.filter(h => h.cat === '弹性股').reduce((s, h) => s + h.price * h.qty, 0);

  return (
    <div style={{
      width: 420,
      background: TOKENS.surfaceAlt,
      borderRight: `1px solid ${TOKENS.border}`,
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      height: '100%',
    }}>
      {/* ===== 1. Sticky status bar ===== */}
      <div style={{
        padding: '12px 14px',
        borderBottom: `1px solid ${TOKENS.border}`,
        background: TOKENS.surface,
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={onCollapse}
              title="收起"
              style={{
                width: 22, height: 22,
                background: 'rgba(255,255,255,0.06)',
                border: `1px solid ${TOKENS.border}`,
                borderRadius: 4,
                color: TOKENS.textMuted,
                cursor: 'pointer',
                fontSize: 12,
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>⟨</button>
            <div style={{ fontSize: 13, fontWeight: 600 }}>持仓编辑器</div>
          </div>
          <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>v1.2 · unsaved</Mono>
        </div>

        {/* snapshot date + source */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div>
            <div style={{ fontSize: 10, color: TOKENS.textMuted, marginBottom: 2 }}>快照日期</div>
            <button style={{
              background: 'transparent',
              border: `1px dashed ${TOKENS.border}`,
              borderRadius: 4,
              padding: '4px 8px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 13,
              color: TOKENS.text,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              2026-05-17
              <span style={{ fontSize: 10, color: TOKENS.textDim }}>✎</span>
            </button>
          </div>
          <div>
            <div style={{ fontSize: 10, color: TOKENS.textMuted, marginBottom: 2, textAlign: 'right' }}>数据来源</div>
            <span style={{
              padding: '4px 8px',
              background: SOURCE_STATES.manual.color + '1A',
              color: SOURCE_STATES.manual.color,
              border: `1px solid ${SOURCE_STATES.manual.color}55`,
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
            }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: SOURCE_STATES.manual.color }} />
              手动编辑
            </span>
          </div>
        </div>

        {/* source-state preview row */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
          {Object.entries(SOURCE_STATES).map(([k, v]) => (
            <div key={k} style={{
              flex: 1,
              padding: '4px 6px',
              borderRadius: 3,
              border: `1px solid ${k === 'manual' ? v.color + '55' : TOKENS.border}`,
              background: k === 'manual' ? v.color + '12' : 'transparent',
              textAlign: 'center',
              fontSize: 9,
              color: k === 'manual' ? v.color : TOKENS.textDim,
              cursor: 'pointer',
              fontFamily: 'JetBrains Mono, monospace',
              letterSpacing: '0.04em',
            }}>{v.label}</div>
          ))}
        </div>

        {/* action buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={{
            flex: 1,
            background: TOKENS.accent,
            border: 'none',
            color: '#fff',
            padding: '8px 12px',
            borderRadius: 5,
            fontSize: 12,
            fontWeight: 600,
            fontFamily: 'inherit',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}>
            <span>💾</span> 保存快照
          </button>
          <button style={{
            background: 'transparent',
            border: `1px solid ${TOKENS.border}`,
            color: TOKENS.textMuted,
            padding: '8px 12px',
            borderRadius: 5,
            fontSize: 12,
            fontFamily: 'inherit',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}>↺ 撤销</button>
        </div>
        <div style={{ fontSize: 10, color: TOKENS.textDim, marginTop: 6, fontFamily: 'JetBrains Mono, monospace' }}>
          将写入 data/agent_input/holdings_20260517.csv
        </div>
      </div>

      {/* ===== Scrollable middle ===== */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>

        {/* 2. Import (collapsible) */}
        <div style={{ marginBottom: 14 }}>
          <button
            onClick={() => setImportOpen(!importOpen)}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'transparent',
              border: 'none',
              padding: '6px 0',
              color: TOKENS.text,
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: TOKENS.textMuted, fontSize: 11 }}>{importOpen ? '▾' : '▸'}</span>
              导入
              <Mono style={{ fontSize: 10, color: TOKENS.textDim, fontWeight: 400 }}>CSV · Excel</Mono>
            </span>
          </button>
          {importOpen && (
            <div style={{ marginTop: 8 }}>
              <div style={{
                border: `1.5px dashed ${TOKENS.border}`,
                borderRadius: 6,
                padding: 18,
                textAlign: 'center',
                background: 'rgba(79,142,247,0.03)',
                cursor: 'pointer',
                transition: 'background 120ms, border-color 120ms',
              }}>
                <div style={{ fontSize: 22, marginBottom: 6, color: TOKENS.textMuted }}>⬆</div>
                <div style={{ fontSize: 12, color: TOKENS.text, fontWeight: 500, marginBottom: 4 }}>拖放 CSV 文件到此处</div>
                <div style={{ fontSize: 10, color: TOKENS.textMuted }}>或 <span style={{ color: TOKENS.accent, textDecoration: 'underline' }}>点击选择文件</span></div>
                <div style={{ fontSize: 10, color: TOKENS.textDim, marginTop: 8, lineHeight: 1.5, fontFamily: 'JetBrains Mono, monospace' }}>
                  接受 holdings_&#123;YYYYMMDD&#125;.csv 格式<br />或从券商后台导出 Excel 另存为 CSV
                </div>
              </div>
              {/* simulated parse result (would show after upload) */}
              <div style={{
                marginTop: 8,
                padding: '8px 10px',
                background: TOKENS.bull + '14',
                border: `1px solid ${TOKENS.bull}44`,
                borderRadius: 4,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: 11,
              }}>
                <span style={{ color: TOKENS.bull, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>✓</span> 已解析 11 行 · 与现有数据 3 行重叠
                </span>
                <button style={{
                  background: TOKENS.bull,
                  border: 'none',
                  color: '#fff',
                  padding: '3px 10px',
                  borderRadius: 3,
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}>应用</button>
              </div>
            </div>
          )}
        </div>

        {/* 3. Editable table */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 600 }}>持仓列表 <Mono style={{ fontSize: 10, color: TOKENS.textDim, fontWeight: 400 }}>{EDITOR_HOLDINGS.length} 行 · 2 项未保存</Mono></div>
            <div style={{ display: 'flex', gap: 4 }}>
              <Tag muted>排序</Tag>
              <Tag muted>过滤</Tag>
            </div>
          </div>

          <div style={{
            background: TOKENS.surface,
            border: `1px solid ${TOKENS.border}`,
            borderRadius: 6,
            overflow: 'hidden',
          }}>
            {/* header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '60px 1fr 70px 64px 64px 56px 70px 22px',
              gap: 4,
              padding: '7px 10px',
              background: TOKENS.surfaceAlt,
              fontSize: 9,
              color: TOKENS.textMuted,
              fontFamily: 'JetBrains Mono, monospace',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}>
              <span>代码</span>
              <span>名称</span>
              <span>类别</span>
              <span style={{ textAlign: 'right' }}>成本价</span>
              <span style={{ textAlign: 'right' }}>现价</span>
              <span style={{ textAlign: 'right' }}>数量</span>
              <span style={{ textAlign: 'right' }}>市值</span>
              <span></span>
            </div>

            {/* rows */}
            {EDITOR_HOLDINGS.map((r, i) => {
              const mv = r.price * r.qty;
              return (
                <EditableRow key={r.code} row={r} mv={mv} last={i === EDITOR_HOLDINGS.length - 1} />
              );
            })}

            {/* add row */}
            <div style={{
              padding: '8px 10px',
              borderTop: `1px dashed ${TOKENS.border}`,
              fontSize: 11,
              color: TOKENS.accent,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'transparent',
              fontWeight: 500,
            }}>
              <span style={{
                width: 16, height: 16,
                borderRadius: 3,
                border: `1px dashed ${TOKENS.accent}66`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11,
                color: TOKENS.accent,
              }}>+</span>
              添加持仓
            </div>
          </div>

          {/* keyboard hint */}
          <div style={{ marginTop: 8, fontSize: 10, color: TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.6 }}>
            <div>点击单元格编辑 · 失焦提交 · Tab 跳到下一格</div>
            <div>市值列只读 · 现价 × 数量 实时计算 · 黄色 = 未保存</div>
          </div>
        </div>
      </div>

      {/* ===== 4. Sticky summary bar ===== */}
      <div style={{
        flexShrink: 0,
        background: TOKENS.surface,
        borderTop: `1px solid ${TOKENS.border}`,
        padding: '12px 14px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
          <div style={{ fontSize: 10, color: TOKENS.textMuted }}>组合总市值</div>
          <Mono style={{ fontSize: 17, fontWeight: 600, color: TOKENS.text }}>¥{totalMV.toLocaleString('zh-CN')}</Mono>
        </div>
        <SummaryRow label="白马股" mv={baimaMV} total={totalMV} color={TOKENS.accent} target={67} />
        <SummaryRow label="弹性股" mv={elasticMV} total={totalMV} color="#5C616E" target={33} highlightOver={8} holdings={EDITOR_HOLDINGS.filter(h => h.cat === '弹性股')} />
      </div>
    </div>
  );
}

function SummaryRow({ label, mv, total, color, target, highlightOver, holdings }) {
  const pct = (mv / total) * 100;
  // Check single-stock over-threshold (8%)
  let warnSingle = false;
  if (highlightOver && holdings) {
    holdings.forEach(h => {
      const single = (h.price * h.qty / total) * 100;
      if (single > highlightOver) warnSingle = true;
    });
  }
  const dev = pct - target;
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '52px 1fr 70px',
      gap: 8,
      alignItems: 'center',
      padding: '5px 6px',
      borderRadius: 4,
      border: warnSingle ? `1px solid ${TOKENS.bear}66` : '1px solid transparent',
      background: warnSingle ? `${TOKENS.bear}0F` : 'transparent',
      marginBottom: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <span style={{ width: 8, height: 8, background: color, borderRadius: 2 }} />
        <span style={{ fontSize: 11 }}>{label}</span>
      </div>
      <div>
        <div style={{ position: 'relative', height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2 }}>
          <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${pct}%`, background: color, borderRadius: 2 }} />
          <div style={{ position: 'absolute', left: `${target}%`, top: -2, width: 1.5, height: 8, background: '#fff' }} />
        </div>
        <div style={{ fontSize: 9, color: TOKENS.textDim, marginTop: 3, fontFamily: 'JetBrains Mono, monospace', display: 'flex', justifyContent: 'space-between' }}>
          <span>目标 {target}%</span>
          <span style={{ color: warnSingle ? TOKENS.bear : (Math.abs(dev) > 5 ? TOKENS.neutral : TOKENS.textDim) }}>
            {warnSingle && '⚠ 单仓超阈值 · '}偏差 {dev >= 0 ? '+' : ''}{dev.toFixed(1)}%
          </span>
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <Mono style={{ fontSize: 11, color: TOKENS.text }}>¥{mv.toLocaleString('zh-CN')}</Mono>
        <Mono style={{ fontSize: 10, color: TOKENS.textMuted, display: 'block' }}>{pct.toFixed(1)}%</Mono>
      </div>
    </div>
  );
}

function EditableRow({ row, mv, last }) {
  const dirty = (k) => row.dirty.includes(k);
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '60px 1fr 70px 64px 64px 56px 70px 22px',
      gap: 4,
      padding: '6px 10px',
      borderTop: `1px solid ${TOKENS.border}`,
      alignItems: 'center',
      fontSize: 12,
      fontFamily: 'JetBrains Mono, monospace',
      position: 'relative',
    }}>
      <Cell dirty={dirty('code')}>
        <Mono style={{ fontSize: 11, fontWeight: 500 }}>{row.code}</Mono>
      </Cell>
      <Cell dirty={dirty('name')} nonMono>
        <span style={{ fontFamily: '"Noto Sans SC", sans-serif', fontSize: 12, color: TOKENS.text }}>{row.name}</span>
      </Cell>
      <Cell dirty={dirty('cat')} nonMono>
        <span style={{
          padding: '1px 6px',
          background: 'rgba(79,142,247,0.16)',
          color: TOKENS.accent,
          borderRadius: 3,
          fontSize: 10,
          fontWeight: 500,
          fontFamily: '"Noto Sans SC", sans-serif',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 3,
        }}>{row.cat}<span style={{ fontSize: 8, opacity: 0.6 }}>▾</span></span>
      </Cell>
      <Cell dirty={dirty('cost')} align="right">¥{row.cost.toFixed(2)}</Cell>
      <Cell dirty={dirty('price')} align="right">¥{row.price.toFixed(2)}</Cell>
      <Cell dirty={dirty('qty')} align="right">{row.qty}</Cell>
      <div style={{ textAlign: 'right', color: TOKENS.textMuted, fontSize: 11, paddingRight: 2 }}>
        ¥{mv.toLocaleString('zh-CN')}
      </div>
      <div title="删除" style={{
        width: 18, height: 18,
        borderRadius: 3,
        color: TOKENS.textDim,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 12,
        background: 'rgba(255,255,255,0.04)',
      }}>×</div>
    </div>
  );
}

function Cell({ children, dirty, align, nonMono }) {
  return (
    <div style={{
      textAlign: align || 'left',
      padding: '2px 4px',
      borderRadius: 2,
      background: dirty ? 'rgba(245,166,35,0.18)' : 'transparent',
      border: dirty ? `1px solid ${TOKENS.neutral}55` : '1px solid transparent',
      color: TOKENS.text,
      fontSize: nonMono ? undefined : 11,
      lineHeight: 1.4,
      position: 'relative',
    }}>
      {children}
      {dirty && (
        <div title="未保存" style={{
          position: 'absolute',
          top: 2, right: 2,
          width: 4, height: 4,
          borderRadius: '50%',
          background: TOKENS.neutral,
        }} />
      )}
    </div>
  );
}

// =========== COMPACT MAIN CONTENT (Tab 1) — narrower variant for expanded sidebar ===========
function MiniDashboard({ width = 1248 }) {
  // mini Tab 1 — header + tabs + donut/KPIs + heatmap teaser
  const ph = (h) => ({
    background: TOKENS.surface,
    border: `1px solid ${TOKENS.border}`,
    borderRadius: 8,
    padding: 12,
    height: h,
    color: TOKENS.text,
  });

  const tabs = ['持仓总览', '每日策略简报', '个股深度分析', '信号仪表盘'];

  return (
    <div style={{
      flex: 1,
      background: TOKENS.bg,
      color: TOKENS.text,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      padding: '18px 20px',
      overflow: 'hidden',
      boxSizing: 'border-box',
    }}>
      {/* header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 12 }}>
        <div>
          <Mono style={{ fontSize: 10, color: TOKENS.textDim, letterSpacing: '0.14em' }}>MY-INVEST-GLOBAL · TAB 01</Mono>
          <div style={{ fontSize: 22, fontWeight: 600, marginTop: 2 }}>持仓总览</div>
          <div style={{ fontSize: 11, color: TOKENS.textMuted, marginTop: 2 }}>2026-05-17 · 3 持仓 · 弹性股 1 项超阈值</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <MiniStat label="总市值" value="¥169,664" />
          <MiniStat label="盈亏" value="+5.18%" tone="bull" />
        </div>
      </div>

      {/* tab bar */}
      <div style={{
        display: 'flex',
        background: TOKENS.surface,
        border: `1px solid ${TOKENS.border}`,
        borderRadius: 8,
        overflow: 'hidden',
        marginBottom: 12,
      }}>
        {tabs.map((t, i) => (
          <div key={t} style={{
            padding: '10px 16px',
            fontSize: 12,
            fontWeight: i === 0 ? 600 : 400,
            color: i === 0 ? TOKENS.text : TOKENS.textMuted,
            borderBottom: i === 0 ? `2px solid ${TOKENS.accent}` : '2px solid transparent',
            background: i === 0 ? 'rgba(79,142,247,0.06)' : 'transparent',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <span style={{ color: i === 0 ? TOKENS.accent : TOKENS.textDim, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>0{i + 1}</span>
            {t}
          </div>
        ))}
        <div style={{ flex: 1 }} />
      </div>

      {/* Row 1: donut + KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 12, marginBottom: 12 }}>
        <Card pad={14}>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>资产配置</div>
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            <svg width={140} height={140} viewBox="0 0 200 200">
              <circle cx="100" cy="100" r="80" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="22" />
              <circle cx="100" cy="100" r="80" fill="none" stroke="#5C616E" strokeWidth="22" strokeDasharray="160 502" strokeDashoffset="-342" transform="rotate(-90 100 100)" />
              <circle cx="100" cy="100" r="80" fill="none" stroke={TOKENS.accent} strokeWidth="22" strokeDasharray="342 502" transform="rotate(-90 100 100)" />
              <text x="100" y="92" textAnchor="middle" fill={TOKENS.textMuted} fontSize="10" fontFamily="Noto Sans SC">总市值</text>
              <text x="100" y="116" textAnchor="middle" fill="#fff" fontSize="18" fontFamily="JetBrains Mono" fontWeight="600">¥16.97</text>
              <text x="100" y="130" textAnchor="middle" fill={TOKENS.textDim} fontSize="8" fontFamily="JetBrains Mono">万元</text>
            </svg>
            <div style={{ flex: 1, fontSize: 11 }}>
              <div style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span><span style={{ display: 'inline-block', width: 8, height: 8, background: TOKENS.accent, borderRadius: 2, marginRight: 5 }} />白马股</span>
                  <Mono style={{ fontWeight: 600 }}>12.4%</Mono>
                </div>
                <div style={{ fontSize: 9, color: TOKENS.textDim, marginTop: 1, paddingLeft: 13, fontFamily: 'JetBrains Mono, monospace' }}>目标 67% · 严重偏离</div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span><span style={{ display: 'inline-block', width: 8, height: 8, background: '#5C616E', borderRadius: 2, marginRight: 5 }} />弹性股</span>
                  <Mono style={{ fontWeight: 600 }}>87.6%</Mono>
                </div>
                <div style={{ fontSize: 9, color: TOKENS.textDim, marginTop: 1, paddingLeft: 13, fontFamily: 'JetBrains Mono, monospace' }}>目标 33% · 严重偏离</div>
              </div>
            </div>
          </div>
        </Card>
        <div style={{ display: 'grid', gridTemplateRows: 'repeat(3, 1fr)', gap: 8 }}>
          <MiniKPI label="白马股市值" value="¥21,000" pct="12.4%" sub="目标 67% · 严重偏离" tone="bear" />
          <MiniKPI label="弹性股市值" value="¥148,664" pct="87.6%" sub="目标 33% · 严重偏离" tone="bear" />
          <MiniKPI label="最大单只" value="59.4%" sub="300308 · 大幅超阈值" tone="bear" danger />
        </div>
      </div>

      {/* Mini heatmap teaser - 3 cells */}
      <Card pad={12}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600 }}>持仓热力图</div>
          <Mono style={{ fontSize: 10, color: TOKENS.textDim }}>3 持仓</Mono>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '3fr 1.5fr 1.5fr', gap: 4, height: 250 }}>
          <HeatBlock name="中际旭创" code="300308" mv="¥100,800" pnl={18.59} />
          <HeatBlock name="中芯国际" code="688981" mv="¥47,864" pnl={-3.5} />
          <HeatBlock name="海康威视" code="002415" mv="¥21,000" pnl={5.2} />
        </div>
      </Card>
    </div>
  );
}

function MiniKPI({ label, value, pct, sub, tone, danger }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : TOKENS.text;
  return (
    <div style={{
      background: TOKENS.surface,
      border: `1px solid ${danger ? TOKENS.bear + '55' : TOKENS.border}`,
      borderRadius: 6,
      padding: '8px 12px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      position: 'relative',
    }}>
      {danger && (
        <div style={{ position: 'absolute', top: 6, right: 8 }}>
          <Tag tone="bear">超阈值</Tag>
        </div>
      )}
      <div style={{ fontSize: 10, color: TOKENS.textMuted }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 2 }}>
        <Mono style={{ fontSize: 16, fontWeight: 600, color: c }}>{value}</Mono>
        {pct && <Mono style={{ fontSize: 11, color: TOKENS.textMuted }}>{pct}</Mono>}
      </div>
      <div style={{ fontSize: 10, color: TOKENS.textDim, marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>{sub}</div>
    </div>
  );
}

function MiniStat({ label, value, tone }) {
  const c = tone === 'bull' ? TOKENS.bull : tone === 'bear' ? TOKENS.bear : TOKENS.text;
  return (
    <div style={{
      background: TOKENS.surface,
      border: `1px solid ${TOKENS.border}`,
      borderRadius: 6,
      padding: '6px 12px',
      minWidth: 110,
    }}>
      <div style={{ fontSize: 9, color: TOKENS.textMuted, letterSpacing: '0.05em' }}>{label}</div>
      <Mono style={{ fontSize: 16, fontWeight: 600, color: c, display: 'block' }}>{value}</Mono>
    </div>
  );
}

function HeatBlock({ name, code, mv, pnl }) {
  const isPos = pnl >= 0;
  const t = Math.max(-1, Math.min(1, pnl / 20));
  const bg = isPos
    ? `rgba(0,196,122,${0.15 + Math.abs(t) * 0.55})`
    : `rgba(232,64,64,${0.15 + Math.abs(t) * 0.55})`;
  return (
    <div style={{
      background: bg,
      border: `1px solid ${isPos ? '#00C47A55' : '#E8404055'}`,
      borderRadius: 4,
      padding: '10px 12px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
    }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{name}</div>
        <Mono style={{ fontSize: 10, color: 'rgba(255,255,255,0.65)' }}>{code} · {mv}</Mono>
      </div>
      <Mono style={{ fontSize: 22, fontWeight: 600, color: '#fff' }}>{isPos ? '+' : ''}{pnl.toFixed(2)}%</Mono>
    </div>
  );
}

// =========== ARTBOARD COMPOSITIONS ===========
function DashboardWithSidebar({ expanded, interactive }) {
  // Interactive variant: clicking the chevron toggles state via setState
  const [open, setOpen] = useStateE(expanded);
  const [importOpen, setImportOpen] = useStateE(true);
  const isOpen = interactive ? open : expanded;

  return (
    <div style={{
      width: 1280,
      height: 900,
      display: 'flex',
      background: TOKENS.bg,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      overflow: 'hidden',
      borderRadius: 4,
    }}>
      {isOpen ? (
        <SidebarExpanded onCollapse={() => interactive && setOpen(false)} importOpen={importOpen} setImportOpen={setImportOpen} />
      ) : (
        <SidebarCollapsed onExpand={() => interactive && setOpen(true)} />
      )}
      <MiniDashboard />
    </div>
  );
}

function ArtboardSidebarCollapsed() {
  return <DashboardWithSidebar expanded={false} interactive={true} />;
}
function ArtboardSidebarExpanded() {
  return <DashboardWithSidebar expanded={true} interactive={true} />;
}

Object.assign(window, { ArtboardSidebarCollapsed, ArtboardSidebarExpanded, SidebarCollapsed, SidebarExpanded });
