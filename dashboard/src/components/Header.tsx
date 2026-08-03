import { useAccount, useConnect, useDisconnect } from 'wagmi';
import { useWebSocket, WSStatus } from '../hooks/useWebSocket';
import type { Lang } from '../utils/i18n';
import { createTranslator } from '../utils/i18n';

interface HeaderProps {
  lang: Lang;
  setLang: (l: Lang) => void;
}

export default function Header({ lang, setLang }: HeaderProps) {
  const t = createTranslator(lang);
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending } = useConnect();
  const { disconnect } = useDisconnect();
  const wsStatus: WSStatus = useWebSocket();

  const shortAddr = address ? `${address.slice(0, 6)}…${address.slice(-4)}` : '';

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">⛏️ Sovereign Resource DAO</div>
      </div>

      <div className="header-right">
        <span title={`WebSocket: ${wsStatus}`}>
          <span className={`ws-dot ${wsStatus}`} />
        </span>

        <div className="lang-toggle">
          <button className={`lang-btn ${lang === 'en' ? 'active' : ''}`} onClick={() => setLang('en')}>EN</button>
          <button className={`lang-btn ${lang === 'sw' ? 'active' : ''}`} onClick={() => setLang('sw')}>SW</button>
        </div>

        {isConnected ? (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--accent)' }}>{shortAddr}</span>
            <button className="btn btn-outline btn-sm" onClick={() => disconnect()}>
              {t('nav.connected')} ✕
            </button>
          </div>
        ) : (
          <button
            className="btn btn-wallet"
            disabled={isPending}
            onClick={() => connect({ connector: connectors[0] })}
          >
            {isPending ? '…' : t('nav.connectWallet')}
          </button>
        )}
      </div>
    </header>
  );
}
