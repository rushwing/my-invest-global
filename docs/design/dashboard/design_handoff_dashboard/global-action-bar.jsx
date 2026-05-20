/* global React, TOKENS, Mono */
const { useState: useGab } = React;

// =========== ICONS ===========
function IcRefresh({ size = 14, spin, color = 'currentColor' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" style={{ animation: spin ? 'gab-spin 0.9s linear infinite' : 'none' }}>
      <path d="M2 8a6 6 0 0 1 10.5-3.9L14 3M14 8a6 6 0 0 1-10.5 3.9L2 13" stroke={color} strokeWidth="1.4" fill="none" strokeLinecap="round" />
      <path d="M14 1.5 V4 H11.5 M2 14.5 V12 H4.5" stroke={color} strokeWidth="1.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IcPlay({ size = 14, color = 'currentColor' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M4 3 L13 8 L4 13 Z" fill={color} />
    </svg>
  );
}
function IcSpinner({ size = 14, color = 'currentColor' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" style={{ animation: 'gab-spin 0.85s linear infinite' }}>
      <circle cx="8" cy="8" r="6" stroke={color + '33'} strokeWidth="1.6" fill="none" />
      <path d="M14 8 A6 6 0 0 0 8 2" stroke={color} strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}
function IcLock({ size = 13, color = 'currentColor' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <rect x="3.5" y="7" width="9" height="7" rx="1" fill={color} />
      <path d="M5 7 V5 a3 3 0 0 1 6 0 V7" stroke={color} strokeWidth="1.4" fill="none" />
    </svg>
  );
}
function IcChart({ size = 14, color = '#fff' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M2 12 L5 8 L8 10 L11 5 L14 7" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <circle cx="14" cy="7" r="1.2" fill={color} />
    </svg>
  );
}

// =========== TABS CONFIG ===========
const GAB_TABS = ['持仓总览', '每日简报', '个股分析', '信号仪表盘', '调仓分析'];

// =========== LOGO ===========
function GabLogo() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: 24, height: 24,
        background: '#1C3A3A',
        borderRadius: 4,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: `1px solid rgba(0,196,122,0.3)`,
      }}>
        <IcChart size={14} color={TOKENS.bull} />
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, fontFamily: 'JetBrains Mono, monospace' }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: TOKENS.accent, letterSpacing: '0.06em' }}>MY INVEST</span>
        <span style={{ fontSize: 11, color: TOKENS.textMuted, letterSpacing: '0.06em' }}>GLOBAL</span>
      </div>
    </div>
  );
}

function GabSeparator() {
  return <div style={{ width: 1, height: 20, background: TOKENS.border, flexShrink: 0 }} />;
}

// =========== TAB PILLS ===========
function GabTabPill({ idx, label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 11px',
        background: active ? `${TOKENS.accent}26` : 'transparent',
        border: `1px solid ${active ? TOKENS.accent + '88' : 'transparent'}`,
        borderRadius: 5,
        color: active ? TOKENS.text : TOKENS.textMuted,
        fontSize: 12,
        fontWeight: active ? 600 : 400,
        fontFamily: 'inherit',
        cursor: 'pointer',
        letterSpacing: '0.02em',
        transition: 'background 120ms',
      }}
    >
      <Mono style={{
        fontSize: 10,
        color: active ? TOKENS.accent : TOKENS.textDim,
        fontWeight: 500,
      }}>0{idx + 1}</Mono>
      {label}
    </button>
  );
}

// =========== STATUS / COUNTDOWN ===========
function SystemStatus({ status }) {
  const cfg = {
    live:   { c: TOKENS.bull,    label: 'LIVE · A股盘中', pulse: true },
    closed: { c: TOKENS.textDim, label: '盘后',           pulse: false },
    error:  { c: TOKENS.bear,    label: '数据异常',       pulse: false },
  }[status];
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span style={{
        width: 6, height: 6,
        borderRadius: '50%',
        background: cfg.c,
        boxShadow: cfg.pulse ? `0 0 6px ${cfg.c}` : 'none',
        animation: cfg.pulse ? 'gab-pulse 1.4s ease-in-out infinite' : 'none',
      }} />
      <Mono style={{ fontSize: 10, color: cfg.c, letterSpacing: '0.04em' }}>{cfg.label}</Mono>
    </span>
  );
}

function CacheCountdown({ text }) {
  return (
    <Mono style={{
      fontSize: 10,
      color: TOKENS.textDim,
      padding: '3px 7px',
      background: TOKENS.surfaceAlt,
      borderRadius: 3,
      letterSpacing: '0.03em',
    }}>↻ {text}</Mono>
  );
}

// =========== ICON BUTTONS ===========
function GabIconButton({ icon, primary, loading, disabled, errored, tooltip, onClick }) {
  const baseBg = primary ? TOKENS.accent : 'transparent';
  const baseBorder = primary ? TOKENS.accent : TOKENS.border;
  const c = errored ? TOKENS.bear : (primary ? '#fff' : TOKENS.textMuted);
  return (
    <button
      onClick={onClick}
      title={tooltip}
      disabled={disabled || loading}
      style={{
        width: 28, height: 28,
        background: errored ? TOKENS.bear + '1A' : baseBg,
        border: `1px solid ${errored ? TOKENS.bear + '66' : baseBorder}`,
        borderRadius: 5,
        color: c,
        cursor: disabled || loading ? 'default' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 0,
        fontFamily: 'inherit',
      }}
    >
      {loading ? <IcSpinner size={14} color={c} /> : icon}
    </button>
  );
}

// =========== AUTH INDICATOR ===========
function AuthIndicator({ locked, onLock }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
        <span style={{
          width: 6, height: 6,
          borderRadius: '50%',
          background: locked ? TOKENS.bear : TOKENS.bull,
          boxShadow: locked ? `0 0 4px ${TOKENS.bear}88` : `0 0 4px ${TOKENS.bull}88`,
        }} />
        <Mono style={{ fontSize: 10, color: locked ? TOKENS.bear : TOKENS.bull, letterSpacing: '0.04em' }}>
          {locked ? '已锁定' : '已解锁'}
        </Mono>
      </span>
      {!locked && (
        <button
          onClick={onLock}
          title="立即锁定 · 清除 session"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 3,
            padding: '3px 7px',
            background: 'transparent',
            border: `1px solid ${TOKENS.border}`,
            borderRadius: 4,
            color: TOKENS.textMuted,
            fontFamily: 'inherit',
            fontSize: 10,
            cursor: 'pointer',
          }}
        >
          <IcLock size={10} color={TOKENS.textMuted} /> 锁定
        </button>
      )}
    </div>
  );
}

// =========== MAIN ===========
function GlobalActionBar({
  activeTab = 0,
  onTabChange = () => {},
  onRefresh = () => {},
  onRunAnalysis = () => {},
  onLock = () => {},
  isRefreshing = false,
  isAnalyzing = false,
  marketStatus = 'live',
  lastUpdated = '14:32',
  isUnlocked = true,
  errored = false,
  countdown = '03:24',
}) {
  return (
    <div style={{
      height: 44,
      background: TOKENS.surface,
      borderBottom: `1px solid ${TOKENS.border}`,
      display: 'flex',
      alignItems: 'center',
      padding: '0 16px 0 20px',
      gap: 10,
      flexShrink: 0,
      position: 'relative',
    }}>
      {/* LEFT */}
      <GabLogo />
      <GabSeparator />

      {/* CENTER */}
      <div style={{ display: 'flex', gap: 4 }}>
        {GAB_TABS.map((t, i) => (
          <GabTabPill key={t} idx={i} label={t} active={i === activeTab} onClick={() => onTabChange(i)} />
        ))}
      </div>

      <div style={{ flex: 1 }} />

      {/* RIGHT */}
      <SystemStatus status={marketStatus} />
      <CacheCountdown text={isRefreshing ? '刷新中…' : `${countdown} 前`} />
      <GabIconButton
        icon={<IcRefresh size={14} color={errored ? TOKENS.bear : TOKENS.textMuted} />}
        loading={isRefreshing}
        errored={errored}
        tooltip="刷新行情数据"
        onClick={onRefresh}
      />
      <GabIconButton
        icon={<IcPlay size={13} color="#fff" />}
        primary
        loading={isAnalyzing}
        errored={errored}
        tooltip={isAnalyzing ? 'AI 分析中，约 30 秒' : '运行 AI 分析'}
        onClick={onRunAnalysis}
      />
      <GabSeparator />
      <AuthIndicator locked={!isUnlocked} onLock={onLock} />

      {/* analyzing progress strip */}
      {isAnalyzing && (
        <div style={{
          position: 'absolute',
          left: 0, right: 0, bottom: -1,
          height: 2,
          background: TOKENS.accent + '22',
          overflow: 'hidden',
        }}>
          <div style={{
            width: '34%',
            height: '100%',
            background: `linear-gradient(90deg, transparent, ${TOKENS.accent}, transparent)`,
            animation: 'gab-progress 1.5s ease-in-out infinite',
          }} />
        </div>
      )}
    </div>
  );
}

// =========== INTERACTIVE WRAPPER (one bar wired to local state) ===========
function GabInteractive() {
  const [activeTab, setActiveTab] = useGab(0);
  const [refreshing, setRefreshing] = useGab(false);
  const [analyzing, setAnalyzing] = useGab(false);
  const [unlocked, setUnlocked] = useGab(true);

  const doRefresh = () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1400);
  };
  const doAnalyze = () => {
    setAnalyzing(true);
    setTimeout(() => setAnalyzing(false), 2200);
  };

  return (
    <GlobalActionBar
      activeTab={activeTab}
      onTabChange={setActiveTab}
      isRefreshing={refreshing}
      isAnalyzing={analyzing}
      onRefresh={doRefresh}
      onRunAnalysis={doAnalyze}
      onLock={() => setUnlocked(false)}
      isUnlocked={unlocked}
    />
  );
}

// =========== STATES ARTBOARD ===========
function GabStatesArtboard() {
  const STATES = [
    { code: 'S1', label: 'Normal',      sub: '盘中常态 · 所有控件就绪',            props: {} },
    { code: 'S2', label: 'Refreshing',  sub: '行情拉取中 · 倒计时显示"刷新中…"',  props: { isRefreshing: true } },
    { code: 'S3', label: 'Analyzing',   sub: 'AI 分析中 · 底部进度条 · ▶ 旋转',   props: { isAnalyzing: true } },
    { code: 'S4', label: 'Both active', sub: '刷新 + 分析并行 · 两个按钮都加载',   props: { isRefreshing: true, isAnalyzing: true } },
    { code: 'S5', label: 'Error',       sub: '上次操作失败 · 按钮变红 · "数据异常"', props: { marketStatus: 'error', errored: true } },
    { code: 'S6', label: 'Locked',      sub: '认证失效 · 红点 + 隐藏锁定按钮',     props: { isUnlocked: false } },
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
      <style>{`
        @keyframes gab-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes gab-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes gab-progress { 0% { transform: translateX(-100%); } 100% { transform: translateX(400%); } }
      `}</style>

      <div style={{ marginBottom: 22 }}>
        <Mono style={{ fontSize: 11, color: TOKENS.textDim, letterSpacing: '0.16em' }}>GLOBAL HEADER · 跨 TAB 复用组件</Mono>
        <div style={{ fontSize: 24, fontWeight: 600, marginTop: 4 }}>GlobalActionBar · 6 状态</div>
        <div style={{ fontSize: 12, color: TOKENS.textMuted, marginTop: 4 }}>
          44px sticky 顶栏 · logo / 5 tab pills / 系统状态 / 倒计时 / 刷新+分析 / 认证锁 · 替代各 tab 重复的 header strip
        </div>
      </div>

      {/* Live interactive (one extra at top) */}
      <div style={{ marginBottom: 22 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 }}>
          <Mono style={{ fontSize: 10, color: TOKENS.accent, letterSpacing: '0.06em' }}>LIVE</Mono>
          <span style={{ fontSize: 13, fontWeight: 600 }}>可交互演示</span>
          <span style={{ fontSize: 11, color: TOKENS.textMuted }}>· 点击 tab 切换 / 点 ↻ 模拟刷新 / 点 ▶ 模拟 AI 分析 / 点"锁定"切到 locked 态</span>
        </div>
        <div style={{ border: `1px solid ${TOKENS.borderStrong}`, borderRadius: 6, overflow: 'hidden' }}>
          <GabInteractive />
        </div>
      </div>

      {/* All 6 states */}
      <div style={{ display: 'grid', gap: 18 }}>
        {STATES.map((s, i) => (
          <div key={s.code}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 }}>
              <Mono style={{
                fontSize: 10,
                fontWeight: 600,
                color: TOKENS.accent,
                background: TOKENS.accent + '1A',
                border: `1px solid ${TOKENS.accent}44`,
                padding: '2px 7px',
                borderRadius: 3,
                letterSpacing: '0.06em',
              }}>{s.code}</Mono>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{s.label}</span>
              <span style={{ fontSize: 11, color: TOKENS.textMuted }}>· {s.sub}</span>
            </div>
            <div style={{
              border: `1px solid ${TOKENS.border}`,
              borderRadius: 6,
              overflow: 'hidden',
              position: 'relative',
              filter: s.props.isUnlocked === false ? 'none' : 'none',
            }}>
              <GlobalActionBar activeTab={i % 5} {...s.props} />
              {/* For S6 locked, show a small main-content preview that's blurred */}
              {s.props.isUnlocked === false && (
                <div style={{
                  position: 'relative',
                  height: 64,
                  background: TOKENS.bg,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    filter: 'blur(4px)',
                    opacity: 0.35,
                    pointerEvents: 'none',
                    padding: 14,
                    display: 'flex',
                    gap: 8,
                  }}>
                    <div style={{ width: 110, height: 36, background: TOKENS.surface, borderRadius: 6 }} />
                    <div style={{ width: 110, height: 36, background: TOKENS.surface, borderRadius: 6 }} />
                    <div style={{ width: 110, height: 36, background: TOKENS.surface, borderRadius: 6 }} />
                  </div>
                  <div style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    fontSize: 11,
                    color: TOKENS.textMuted,
                  }}>
                    <IcLock size={12} color={TOKENS.textMuted} /> 主内容已锁定 · 点击左侧或顶栏头像解锁
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Specs notes */}
      <div style={{ marginTop: 28, padding: 16, background: TOKENS.surfaceAlt, borderRadius: 8, fontSize: 11, color: TOKENS.textMuted, lineHeight: 1.7 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: TOKENS.text, marginBottom: 8 }}>组件接口</div>
        <Mono style={{ fontSize: 11, color: TOKENS.text, display: 'block', lineHeight: 1.6 }}>
{`interface GlobalActionBarProps {
  activeTab: 0 | 1 | 2 | 3 | 4;
  onTabChange: (tab: number) => void;
  onRefresh: () => Promise<void>;
  onRunAnalysis: () => Promise<void>;
  onLock: () => void;
  isRefreshing: boolean;
  isAnalyzing: boolean;
  marketStatus: "live" | "closed" | "error";
  lastUpdated: Date | null;
  isUnlocked: boolean;
}`}
        </Mono>
      </div>
    </div>
  );
}

Object.assign(window, {
  GlobalActionBar, GabStatesArtboard, GabInteractive,
  IcRefresh, IcPlay, IcSpinner, IcLock, IcChart, GAB_TABS,
});
