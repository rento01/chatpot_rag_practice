'use client';
import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage, DeepResearchProgress, SourceDoc } from '@/lib/types';

function SourceItem({ src }: { src: SourceDoc }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="source-item">
      <div className="source-header">
        <a
          href={`/api/documents/${src.id}/file`}
          target="_blank"
          rel="noreferrer"
          className="source-chip"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          {src.chunk_index != null && <span className="source-index">[{src.chunk_index}]</span>}
          {src.filename}
        </a>
        {src.content && (
          <button
            className="source-toggle"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
          >
            {open ? '▲ 閉じる' : '▼ 全文'}
          </button>
        )}
      </div>
      {src.content && (
        <div className="source-preview">
          {src.content.slice(0, 80).replace(/\n/g, ' ')}...
        </div>
      )}
      {open && src.content && (
        <div className="source-content">
          <ReactMarkdown>{src.content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

const STATUS_LABELS: Record<string, string> = {
  decomposing: '質問を分解中...',
  searching: 'サブクエリで検索中...',
  synthesizing: '調査結果を統合中...',
  done: '完了',
  error: 'エラー',
};
const SUB_ICONS: Record<string, string> = { pending: '', searching: '', done: '' };

function ResearchProgress({ progress }: { progress: DeepResearchProgress }) {
  return (
    <div className="message assistant">
      <div className="message-role">AI</div>
      <div className="message-bubble deep-research-progress">
        <div className="dr-status">{STATUS_LABELS[progress.status] ?? progress.status}</div>
        {progress.sub_queries.map((sq, i) => (
          <div key={i} className="dr-subquery">
            {SUB_ICONS[sq.status] ?? ''} {sq.sub_query}
          </div>
        ))}
      </div>
    </div>
  );
}

interface Props {
  messages: ChatMessage[];
  streaming: boolean;
  streamingText: string;
  researchProgress?: DeepResearchProgress | null;
}

export default function MessageList({ messages, streaming, streamingText, researchProgress }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  if (messages.length === 0 && !streaming) {
    return (
      <div className="messages-wrap">
        <div className="messages-inner">
          <div className="empty-state">
            <div className="empty-title">何を知りたいですか？</div>
            <div className="empty-sub">
              下のテキストボックスにメッセージを入力してください
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-wrap">
      <div className="messages-inner">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-role">
              {msg.role === 'user' ? 'あなた' : 'AI'}
            </div>
            <div className="message-bubble">
              {msg.role === 'assistant' ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="message-sources">
                <span className="sources-label">参照ドキュメント</span>
                <div className="sources-list">
                  {msg.sources.map((src, si) => (
                    <SourceItem key={`${src.id}-${si}`} src={src} />
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* [P3 DeepResearch] 進捗表示 */}
        {researchProgress && researchProgress.status !== 'done' && researchProgress.status !== 'error' && (
          <ResearchProgress progress={researchProgress} />
        )}

        {streaming && !streamingText && !researchProgress && (
          <div className="message assistant">
            <div className="message-role">AI</div>
            <div className="message-bubble thinking">
              <span className="thinking-dot" />
              <span className="thinking-dot" />
              <span className="thinking-dot" />
            </div>
          </div>
        )}

        {streaming && streamingText && (
          <div className="message assistant">
            <div className="message-role">AI</div>
            <div className="message-bubble">
              <ReactMarkdown>{streamingText}</ReactMarkdown>
              <span className="streaming-cursor" aria-hidden="true" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
