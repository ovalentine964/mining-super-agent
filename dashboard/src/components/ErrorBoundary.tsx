import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', minHeight: '40vh', padding: '2rem',
          textAlign: 'center', fontFamily: 'system-ui, sans-serif',
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
          <h2 style={{ margin: '0 0 0.5rem', color: '#e74c3c' }}>
            Something went wrong
          </h2>
          <p style={{ color: '#666', maxWidth: '28rem', marginBottom: '1.5rem' }}>
            {this.state.error?.message || 'An unexpected error occurred while rendering the dashboard.'}
          </p>
          <button
            onClick={this.handleReset}
            style={{
              padding: '0.6rem 1.5rem', border: 'none', borderRadius: '6px',
              background: '#3498db', color: '#fff', cursor: 'pointer',
              fontSize: '0.95rem', fontWeight: 600,
            }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
