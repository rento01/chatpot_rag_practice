'use client';
import { useState, type KeyboardEvent } from 'react';
import type { Collection } from '@/lib/types';

/**
 * チャット入力欄 + RAG トグル + コレクション選択。
 *
 * 教材としては「ここを ON にすると `use_rag=true` がリクエストに乗る」
 * と一目で対応関係が分かるよう、ラベル等は素直な英大文字で表示する。
 */
type Props = {
  onSend: (content: string) => void;
  onStop: () => void;
  streaming: boolean;
  collections: Collection[];
  selectedCollectionId: number | null;
  onCollectionChange: (id: number | null) => void;
  useRag: boolean;
  onUseRagChange: (next: boolean) => void;
};

export default function ChatComposer({
  onSend,
  onStop,
  streaming,
  collections,
  selectedCollectionId,
  onCollectionChange,
  useRag,
  onUseRagChange,
}: Props) {
  const [draft, setDraft] = useState('');

  const needsCollection = useRag && selectedCollectionId === null;
  const canSend = draft.trim() !== '' && !streaming && !needsCollection;

  const submit = () => {
    if (!canSend) return;
    onSend(draft.trim());
    setDraft('');
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter で送信
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="composer">
      <div className="composer-controls">
        <div className="rag-toggle" role="group" aria-label="RAG mode">
          <button
            type="button"
            className={useRag ? '' : 'off'}
            onClick={() => onUseRagChange(false)}
          >
            Chat
          </button>
          <button
            type="button"
            className={useRag ? 'on' : ''}
            onClick={() => onUseRagChange(true)}
          >
            RAG
          </button>
        </div>

        <div className="collection-picker">
          <label htmlFor="collection">Collection</label>
          <select
            id="collection"
            value={selectedCollectionId ?? ''}
            onChange={(e) =>
              onCollectionChange(e.target.value === '' ? null : Number(e.target.value))
            }
          >
            <option value="">(未選択)</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {needsCollection && (
          <span style={{ color: 'var(--hot)' }}>
            RAG モードにはコレクション選択が必要です（送信はコレクションを選んでから）
          </span>
        )}
      </div>

      <div className="composer-row">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="メッセージを入力 (Cmd/Ctrl + Enter で送信)"
          disabled={streaming}
          rows={2}
        />
        {streaming ? (
          <button type="button" className="stop-btn" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button
            type="button"
            className="send-btn"
            onClick={submit}
            disabled={!canSend}
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
}
