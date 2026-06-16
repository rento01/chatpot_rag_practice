import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'RAG Chat Template',
  description: 'RAG 構築を学習するための教材テンプレート',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@500;600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <header className="app-header">
          <Link href="/" className="brand">
            <span className="brand-mark">/</span>
            <span className="brand-text">RAG Chat Template</span>
          </Link>
          <nav className="app-nav" aria-label="Primary">
            <Link href="/" className="nav-link">Chat</Link>
            <Link href="/ingest" className="nav-link">Ingest</Link>
          </nav>
          <div className="app-tagline">学習用テンプレ / Phase 0-1</div>
        </header>
        {children}
      </body>
    </html>
  );
}
