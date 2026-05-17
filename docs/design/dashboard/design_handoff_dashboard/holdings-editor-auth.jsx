/* global React, TOKENS, Card, Mono, Tag, SignalBadge, SidebarExpanded, MiniDashboard */
const { useState: useStateA } = React;

// =========== AVATAR ===========
function Avatar({ locked, size = 36, onClick }) {
  const initial = 'W';
  const dotSize = 11;
  return (
    <div
      onClick={onClick}
      style={{
        position: 'relative',
        width: size,
        height: size,
        flexShrink: 0,
        cursor: onClick ? 'pointer' : 'default',
      }}
      title={locked ? '已锁定 · 点击展开登录' : '已解锁'}
    >
      <div style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: locked ? '#3A4258' : TOKENS.accent,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: '"Noto Sans SC", sans-serif',
        fontWeight: 500,
        fontSize: size * 0.45,
        letterSpacing: '0.02em',
        boxShadow: locked ? 'none' : `0 0 0 2px rgba(79,142,247,0.18)`,
        filter: locked ? 'grayscale(0.6)' : 'none',
      }}>{initial}</div>
      {/* status indicator */}
      <div style={{
        position: 'absolute',
        right: -2,
        bottom: -2,
        width: dotSize,
        height: dotSize,
        borderRadius: '50%',
        background: locked ? '#2A2E3A' : TOKENS.bull,
        border: `2px solid ${TOKENS.surfaceAlt}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: locked ? TOKENS.textMuted : '#fff',
      }}>
        {locked && (
          <svg width="7" height="7" viewBox="0 0 12 12" fill="none">
            <rect x="3" y="5.5" width="6" height="5" rx="0.8" fill={TOKENS.textMuted} />
            <path d="M4 5.5 V4 a2 2 0 0 1 4 0 V5.5" stroke={TOKENS.textMuted} strokeWidth="1.2" fill="none" />
          </svg>
        )}
      </div>
    </div>
  );
}

// =========== ICONS ===========
function LockIcon({ size = 14, color = TOKENS.textMuted }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <rect x="3.5" y="7" width="9" height="7" rx="1" fill={color} />
      <path d="M5 7 V5 a3 3 0 0 1 6 0 V7" stroke={color} strokeWidth="1.5" fill="none" />
    </svg>
  );
}
function UnlockIcon({ size = 14, color = TOKENS.bull }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <rect x="3.5" y="7" width="9" height="7" rx="1" fill={color} />
      <path d="M5 7 V5 a3 3 0 0 1 6 0" stroke={color} strokeWidth="1.5" fill="none" />
    </svg>
  );
}

// =========== COLLAPSED 56px (with avatar) ===========
function SidebarCollapsedAuth({ locked, onExpand }) {
  return (
    <div style={{
      width: 56,
      background: TOKENS.surfaceAlt,
      borderRight: `1px solid ${TOKENS.border}`,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      paddingTop: 14,
      paddingBottom: 14,
      flexShrink: 0,
    }}>
      <Avatar locked={locked} size={36} onClick={onExpand} />

      <div style={{
        writingMode: 'vertical-rl',
        textOrientation: 'mixed',
        fontSize: 10,
        fontWeight: 500,
        color: locked ? TOKENS.textDim : TOKENS.textMuted,
        letterSpacing: '0.1em',
        marginTop: 12,
      }}>持仓</div>

      {!locked && (
        <Mono style={{
          marginTop: 10,
          writingMode: 'vertical-rl',
          fontSize: 9,
          color: TOKENS.textDim,
          letterSpacing: '0.08em',
        }}>3 持仓 · 已修改</Mono>
      )}
      {locked && (
        <Mono style={{
          marginTop: 10,
          writingMode: 'vertical-rl',
          fontSize: 9,
          color: TOKENS.bear + 'cc',
          letterSpacing: '0.08em',
        }}>LOCKED</Mono>
      )}

      <div style={{ flex: 1 }} />

      <button
        onClick={onExpand}
        title="展开"
        style={{
          width: 26,
          height: 26,
          background: TOKENS.accent + '22',
          border: `1px solid ${TOKENS.accent}55`,
          borderRadius: 4,
          color: TOKENS.accent,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 14,
          padding: 0,
        }}
      >⟩</button>
    </div>
  );
}

// =========== LOGIN FORM (expanded, locked) ===========
function SidebarLoginForm({ error, onUnlock, onCollapse }) {
  const [val, setVal] = useStateA('');
  const [showError, setShowError] = useStateA(error);

  const submit = () => {
    if (val === 'unlock') {
      setShowError(false);
      onUnlock && onUnlock();
    } else {
      setShowError(true);
    }
  };

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
      {/* collapse handle */}
      <div style={{ padding: '12px 14px 0 14px', display: 'flex', justifyContent: 'flex-end' }}>
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
      </div>

      {/* ===== TOP: app identity ===== */}
      <div style={{ padding: '24px 28px 0 28px', textAlign: 'left' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div style={{
            width: 36, height: 36,
            borderRadius: 8,
            background: TOKENS.accent + '1F',
            border: `1px solid ${TOKENS.accent}44`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <LockIcon size={18} color={TOKENS.accent} />
          </div>
          <div>
            <Mono style={{ fontSize: 15, fontWeight: 600, color: TOKENS.text, letterSpacing: '-0.01em', display: 'block' }}>my-invest-global</Mono>
            <Mono style={{ fontSize: 10, color: TOKENS.textDim, letterSpacing: '0.06em' }}>v0.1 · personal advisor</Mono>
          </div>
        </div>
        <div style={{ fontSize: 12, color: TOKENS.textMuted, lineHeight: 1.55 }}>
          持仓数据受本地密语保护
        </div>
      </div>

      <div style={{ flex: 1, padding: '32px 28px 8px 28px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        {/* ===== MIDDLE: form ===== */}
        <div style={{ fontSize: 11, color: TOKENS.textMuted, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6, letterSpacing: '0.04em' }}>
          <LockIcon size={11} color={TOKENS.textMuted} />
          访问密语
        </div>

        <input
          type="password"
          placeholder="输入你的本地密语…"
          value={val}
          onChange={e => { setVal(e.target.value); if (showError) setShowError(false); }}
          onKeyDown={e => { if (e.key === 'Enter') submit(); }}
          style={{
            width: '100%',
            background: TOKENS.bg,
            color: TOKENS.text,
            border: `1.5px solid ${showError ? TOKENS.bear : TOKENS.border}`,
            borderRadius: 6,
            padding: '12px 14px',
            fontSize: 14,
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            letterSpacing: '0.1em',
            outline: 'none',
            boxSizing: 'border-box',
            transition: 'border-color 120ms',
          }}
        />

        {showError && (
          <div style={{
            marginTop: 8,
            fontSize: 11,
            color: TOKENS.bear,
            display: 'flex',
            alignItems: 'center',
            gap: 5,
          }}>
            <span>⨯</span> 密语错误，请重试
          </div>
        )}

        <button
          onClick={submit}
          style={{
            marginTop: 14,
            width: '100%',
            background: TOKENS.accent,
            border: 'none',
            color: '#fff',
            padding: '12px 16px',
            borderRadius: 6,
            fontSize: 13,
            fontWeight: 600,
            fontFamily: 'inherit',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            letterSpacing: '0.02em',
          }}
        >
          <UnlockIcon size={13} color="#fff" /> 解锁
        </button>

        <div style={{ textAlign: 'center', marginTop: 12 }}>
          <Mono style={{
            fontSize: 10,
            color: TOKENS.textDim,
            textDecoration: 'underline',
            textDecorationStyle: 'dotted',
            textUnderlineOffset: 3,
            cursor: 'pointer',
            letterSpacing: '0.02em',
          }}>忘记密语？查看 .env 文件</Mono>
        </div>
      </div>

      {/* ===== BOTTOM: security notes ===== */}
      <div style={{
        padding: '14px 28px 18px 28px',
        borderTop: `1px solid ${TOKENS.border}`,
        background: TOKENS.surface,
      }}>
        <Mono style={{ fontSize: 10, color: TOKENS.textMuted, letterSpacing: '0.06em', display: 'block', marginBottom: 8 }}>本地安全</Mono>
        {[
          '数据仅存储在本机 data/ 目录',
          '无网络同步，无云备份',
          'session 关闭后自动锁定',
        ].map((t, i) => (
          <div key={i} style={{ fontSize: 11, color: TOKENS.textDim, lineHeight: 1.7, display: 'flex', gap: 6 }}>
            <span style={{ color: TOKENS.textDim }}>·</span> {t}
          </div>
        ))}
      </div>
    </div>
  );
}

// =========== HEADER UNLOCK BADGE ===========
function HeaderUnlockBadge({ onLock }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <span style={{
          width: 6, height: 6,
          borderRadius: '50%',
          background: TOKENS.bull,
          boxShadow: `0 0 6px ${TOKENS.bull}88`,
        }} />
        <Mono style={{ fontSize: 11, color: TOKENS.bull, letterSpacing: '0.04em' }}>已解锁</Mono>
      </div>
      <button
        onClick={onLock}
        title="立即锁定"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 5,
          background: 'transparent',
          border: `1px solid ${TOKENS.border}`,
          borderRadius: 5,
          padding: '5px 9px',
          color: TOKENS.textMuted,
          fontFamily: 'inherit',
          fontSize: 11,
          cursor: 'pointer',
        }}
      >
        <LockIcon size={11} color={TOKENS.textMuted} /> 锁定
      </button>
    </div>
  );
}

// =========== LOCKED MAIN-CONTENT MASK ===========
function LockedMask({ collapsed }) {
  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      background: 'rgba(14, 17, 23, 0.78)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 5,
    }}>
      <div style={{
        background: TOKENS.surface,
        border: `1px solid ${TOKENS.border}`,
        borderRadius: 12,
        padding: '28px 36px',
        textAlign: 'center',
        boxShadow: '0 12px 40px rgba(0,0,0,0.4)',
        maxWidth: 360,
      }}>
        <div style={{
          width: 56, height: 56,
          borderRadius: '50%',
          background: TOKENS.surfaceAlt,
          border: `1px solid ${TOKENS.border}`,
          margin: '0 auto 14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <LockIcon size={24} color={TOKENS.textMuted} />
        </div>
        <div style={{ fontSize: 14, fontWeight: 600, color: TOKENS.text, marginBottom: 6 }}>
          持仓数据已锁定
        </div>
        <Mono style={{ fontSize: 11, color: TOKENS.textMuted, lineHeight: 1.6, display: 'block' }}>
          {collapsed ? '点击左侧 ⟩ 或头像解锁' : '在左侧输入密语解锁'}
        </Mono>
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${TOKENS.border}`, fontSize: 10, color: TOKENS.textDim, letterSpacing: '0.04em' }}>
          MY-INVEST-GLOBAL · LOCAL ONLY
        </div>
      </div>
    </div>
  );
}

// =========== MASKED MINI DASHBOARD ===========
// Renders a blurred decoy of MiniDashboard with zero real numbers
function MaskedDashboard({ collapsed }) {
  // We render a stripped placeholder version of the dashboard structure
  // — no numbers, no stock names — overlaid by the lock mask.
  return (
    <div style={{
      flex: 1,
      position: 'relative',
      background: TOKENS.bg,
      color: TOKENS.text,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      padding: '18px 20px',
      overflow: 'hidden',
      boxSizing: 'border-box',
    }}>
      {/* skeleton header */}
      <div style={{ filter: 'blur(2px)', opacity: 0.35, pointerEvents: 'none' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 14 }}>
          <div>
            <div style={{ width: 220, height: 9, background: TOKENS.surfaceAlt, borderRadius: 2, marginBottom: 8 }} />
            <div style={{ width: 180, height: 24, background: TOKENS.surfaceAlt, borderRadius: 4 }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ width: 130, height: 40, background: TOKENS.surface, borderRadius: 6 }} />
            <div style={{ width: 130, height: 40, background: TOKENS.surface, borderRadius: 6 }} />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 0, background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 8, padding: '10px 16px', marginBottom: 14 }}>
          {['持仓总览', '每日策略简报', '个股深度分析', '信号仪表盘'].map((t, i) => (
            <div key={t} style={{ padding: '0 16px', fontSize: 13, color: TOKENS.textMuted }}>{t}</div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 8, height: 200 }} />
          <div style={{ display: 'grid', gridTemplateRows: 'repeat(3, 1fr)', gap: 8 }}>
            {[1, 2, 3].map(i => <div key={i} style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 6 }} />)}
          </div>
        </div>
        <div style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 8, height: 280 }} />
      </div>
      <LockedMask collapsed={collapsed} />
    </div>
  );
}

// =========== UNLOCKED MINI DASHBOARD with header badge ===========
function UnlockedDashboard({ onLock }) {
  // Wrap MiniDashboard, but override header to include lock badge.
  // Easiest path: render the existing MiniDashboard and overlay the lock control absolutely.
  return (
    <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
      <MiniDashboard />
      <div style={{ position: 'absolute', top: 18, right: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
        <HeaderUnlockBadge onLock={onLock} />
      </div>
    </div>
  );
}

// =========== ARTBOARD COMPOSITIONS ===========

// A: collapsed + locked  (56px rail + masked main)
function ArtboardA_CollapsedLocked() {
  const [collapsed, setCollapsed] = useStateA(true);
  const [locked, setLocked] = useStateA(true);
  return (
    <div style={{
      width: 1280, height: 900,
      display: 'flex',
      background: TOKENS.bg,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      overflow: 'hidden',
      borderRadius: 4,
    }}>
      {collapsed
        ? <SidebarCollapsedAuth locked={locked} onExpand={() => setCollapsed(false)} />
        : (locked
            ? <SidebarLoginForm onUnlock={() => setLocked(false)} onCollapse={() => setCollapsed(true)} />
            : <SidebarExpanded onCollapse={() => setCollapsed(true)} importOpen={true} setImportOpen={() => {}} />)
      }
      {locked
        ? <MaskedDashboard collapsed={collapsed} />
        : <UnlockedDashboard onLock={() => setLocked(true)} />
      }
    </div>
  );
}

// B: expanded + locked + login form (default)
function ArtboardB_LoginDefault() {
  const [collapsed, setCollapsed] = useStateA(false);
  const [locked, setLocked] = useStateA(true);
  return (
    <div style={{
      width: 1280, height: 900,
      display: 'flex',
      background: TOKENS.bg,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      overflow: 'hidden',
      borderRadius: 4,
    }}>
      {collapsed
        ? <SidebarCollapsedAuth locked={locked} onExpand={() => setCollapsed(false)} />
        : (locked
            ? <SidebarLoginForm onUnlock={() => setLocked(false)} onCollapse={() => setCollapsed(true)} />
            : <SidebarExpanded onCollapse={() => setCollapsed(true)} importOpen={true} setImportOpen={() => {}} />)
      }
      {locked
        ? <MaskedDashboard collapsed={collapsed} />
        : <UnlockedDashboard onLock={() => setLocked(true)} />
      }
    </div>
  );
}

// C: expanded + locked + login form ERROR
function ArtboardC_LoginError() {
  const [collapsed, setCollapsed] = useStateA(false);
  const [locked, setLocked] = useStateA(true);
  return (
    <div style={{
      width: 1280, height: 900,
      display: 'flex',
      background: TOKENS.bg,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      overflow: 'hidden',
      borderRadius: 4,
    }}>
      {collapsed
        ? <SidebarCollapsedAuth locked={locked} onExpand={() => setCollapsed(false)} />
        : (locked
            ? <SidebarLoginForm error={true} onUnlock={() => setLocked(false)} onCollapse={() => setCollapsed(true)} />
            : <SidebarExpanded onCollapse={() => setCollapsed(true)} importOpen={true} setImportOpen={() => {}} />)
      }
      {locked
        ? <MaskedDashboard collapsed={collapsed} />
        : <UnlockedDashboard onLock={() => setLocked(true)} />
      }
    </div>
  );
}

// D: expanded + unlocked (editor)
function ArtboardD_Unlocked() {
  const [collapsed, setCollapsed] = useStateA(false);
  const [locked, setLocked] = useStateA(false);
  const [importOpen, setImportOpen] = useStateA(true);
  return (
    <div style={{
      width: 1280, height: 900,
      display: 'flex',
      background: TOKENS.bg,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      overflow: 'hidden',
      borderRadius: 4,
    }}>
      {collapsed
        ? <SidebarCollapsedAuth locked={locked} onExpand={() => setCollapsed(false)} />
        : (locked
            ? <SidebarLoginForm onUnlock={() => setLocked(false)} onCollapse={() => setCollapsed(true)} />
            : <SidebarExpanded onCollapse={() => setCollapsed(true)} importOpen={importOpen} setImportOpen={setImportOpen} />)
      }
      {locked
        ? <MaskedDashboard collapsed={collapsed} />
        : <UnlockedDashboard onLock={() => setLocked(true)} />
      }
    </div>
  );
}

// E: collapsed + unlocked (avatar with green dot, normal dashboard)
function ArtboardE_CollapsedUnlocked() {
  const [collapsed, setCollapsed] = useStateA(true);
  const [locked, setLocked] = useStateA(false);
  return (
    <div style={{
      width: 1280, height: 900,
      display: 'flex',
      background: TOKENS.bg,
      fontFamily: '"Noto Sans SC", system-ui, sans-serif',
      overflow: 'hidden',
      borderRadius: 4,
    }}>
      {collapsed
        ? <SidebarCollapsedAuth locked={locked} onExpand={() => setCollapsed(false)} />
        : (locked
            ? <SidebarLoginForm onUnlock={() => setLocked(false)} onCollapse={() => setCollapsed(true)} />
            : <SidebarExpanded onCollapse={() => setCollapsed(true)} importOpen={true} setImportOpen={() => {}} />)
      }
      {locked
        ? <MaskedDashboard collapsed={collapsed} />
        : <UnlockedDashboard onLock={() => setLocked(true)} />
      }
    </div>
  );
}

Object.assign(window, {
  ArtboardA_CollapsedLocked,
  ArtboardB_LoginDefault,
  ArtboardC_LoginError,
  ArtboardD_Unlocked,
  ArtboardE_CollapsedUnlocked,
  Avatar, LockIcon, UnlockIcon,
  SidebarCollapsedAuth, SidebarLoginForm,
});
