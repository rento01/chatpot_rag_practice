'use client';
import { useState, useRef, useCallback } from 'react';
import type { Collection } from '@/lib/types';

interface Props {
  onSend: (content: string) => void;
  disabled: boolean;
  streaming?: boolean;
  onStop?: () => void;
  collections: Collection[];
  selectedCollectionId: number | null;
  onCollectionChange: (id: number | null) => void;
  deepResearch: boolean;
  onDeepResearchChange: (val: boolean) => void;
}

export default function ChatInput({
  onSend,
  disabled,
  streaming = false,
  onStop,
  collections,
  selectedCollectionId,
  onCollectionChange,
  deepResearch,
  onDeepResearchChange,
}: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    if (streaming) {
      onStop?.();
      return;
    }
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, disabled, streaming, onStop, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (streaming) return;
      submit();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  };

  return (
    <div className="input-area">
      <div className="input-inner">
        {/* Agent selector */}
        {collections.length > 0 && (
          <div className="agent-selector">
            <span className="agent-label">エージェント</span>
            <button
              className={`agent-pill${selectedCollectionId === null ? ' active' : ''}`}
              onClick={() => onCollectionChange(null)}
            >
              通常
            </button>
            {collections.map((col) => (
              <button
                key={col.id}
                className={`agent-pill${selectedCollectionId === col.id ? ' active' : ''}`}
                onClick={() => onCollectionChange(col.id)}
              >
                {col.name}
              </button>
            ))}
          </div>
        )}

        {/* [P3 DeepResearch] モード切替トグル */}
        {selectedCollectionId !== null && (
          <label className="deep-research-toggle">
            <input
              type="checkbox"
              checked={deepResearch}
              onChange={(e) => onDeepResearchChange(e.target.checked)}
            />
            <span className="deep-research-label">Deep Research</span>
          </label>
        )}

        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="message-textarea"
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="メッセージを入力... (Shift+Enter で改行)"
            disabled={disabled && !streaming}
            rows={1}
          />
          {streaming ? (
            <button
              className="send-btn stop-btn"
              onClick={submit}
              title="生成を停止"
              aria-label="生成を停止"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <rect x="4" y="4" width="10" height="10" rx="1.5" fill="currentColor" />
              </svg>
            </button>
          ) : (
            <button
              className="send-btn"
              onClick={submit}
              disabled={disabled || !value.trim()}
              title="送信"
              aria-label="送信"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path
                  d="M2 9h14M9 2l7 7-7 7"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
