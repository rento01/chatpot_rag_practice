'use client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  ApiError,
  createCollection,
  deleteCollection,
  deleteDocument,
  listCollections,
  uploadDocuments,
} from '@/lib/api';
import type { Collection, DocumentItem, DocumentStatus } from '@/lib/types';

/**
 * ファイル取り込み画面。
 *
 * ここでは:
 *   1. コレクション作成
 *   2. コレクション選択 → PDF アップロード
 *   3. アップロード済みドキュメントの一覧と状態確認
 * までを行う。実際の検索インデックス構築は backend/rag.py 側で
 * Phase 2-1 以降に実装する想定（教材初期段階では status が "error" に倒れる）。
 */
export default function IngestPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await listCollections();
      setCollections(next);
      // 選択中のコレクションが消えた場合は選択解除
      if (selectedId !== null && !next.find((c) => c.id === selectedId)) {
        setSelectedId(null);
      }
    } catch {
      setError('コレクション一覧の取得に失敗しました');
    }
  }, [selectedId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // インデックス処理中のコレクションがあれば 3 秒おきにポーリング
  useEffect(() => {
    const hasPending = collections.some((c) =>
      c.documents.some((d) => d.status === 'pending' || d.status === 'indexing'),
    );
    if (!hasPending) return;
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [collections, refresh]);

  const selected = useMemo(
    () => collections.find((c) => c.id === selectedId) ?? null,
    [collections, selectedId],
  );

  // ──────────────────────────────────────────────
  // 操作
  // ──────────────────────────────────────────────
  const onCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    try {
      const col = await createCollection(name);
      setNewName('');
      setSelectedId(col.id);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'コレクション作成に失敗しました');
    }
  };

  const onUpload = async (files: FileList | null) => {
    if (!files || files.length === 0 || selectedId === null) return;
    setUploading(true);
    setError(null);
    try {
      await uploadDocuments(selectedId, Array.from(files));
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'アップロードに失敗しました');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const onDeleteCollection = async (id: number) => {
    if (!confirm('このコレクションと配下のドキュメントを削除します。よろしいですか？')) {
      return;
    }
    try {
      await deleteCollection(id);
      if (selectedId === id) setSelectedId(null);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'コレクション削除に失敗しました');
    }
  };

  const onDeleteDoc = async (id: number) => {
    try {
      await deleteDocument(id);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'ドキュメント削除に失敗しました');
    }
  };

  return (
    <div className="ingest-shell">
      <h1>ファイル取り込み</h1>
      <p className="lead">
        コレクションを 1 つ作り、PDF をアップロードすると、バックエンドの
        <code> /collections/&lt;id&gt;/documents </code>
        にバイナリが届きます。Phase 2-1 でチャンク分割と ChromaDB への保存を
        実装すると、ここからの取り込みでステータスが <code>ready</code> に変わります。
      </p>

      {error && (
        <div
          className="error-banner"
          role="alert"
          onClick={() => setError(null)}
          style={{ marginBottom: 20 }}
        >
          {error}
        </div>
      )}

      <section className="section" aria-label="Create collection">
        <h2>新しいコレクションを作る</h2>
        <p className="section-hint">
          コレクションは「同じ目的の文書をまとめる単位」です。<br />
          例: <code>HR-handbook</code> / <code>security-policy</code> など。
        </p>
        <div className="form-row">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="コレクション名"
          />
          <button
            type="button"
            className="btn-primary"
            disabled={!newName.trim()}
            onClick={onCreate}
          >
            作成
          </button>
        </div>
      </section>

      <section className="section" aria-label="Upload PDFs">
        <h2>PDF をアップロード</h2>
        <p className="section-hint">
          アップロード対象のコレクションを選んで、PDF を選択してください。
        </p>
        <div className="form-row" style={{ marginBottom: 16 }}>
          <select
            value={selectedId ?? ''}
            onChange={(e) =>
              setSelectedId(e.target.value === '' ? null : Number(e.target.value))
            }
          >
            <option value="">(コレクションを選択)</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            multiple
            onChange={(e) => onUpload(e.target.files)}
            disabled={selectedId === null || uploading}
          />
        </div>

        {selected && <DocumentTable documents={selected.documents} onDelete={onDeleteDoc} />}
      </section>

      <section className="section" aria-label="Collections">
        <h2>コレクション一覧</h2>
        {collections.length === 0 ? (
          <p className="section-hint">まだコレクションがありません。</p>
        ) : (
          <ul className="collection-list">
            {collections.map((c) => (
              <li key={c.id} className="collection-row">
                <div>
                  <span className="name">{c.name}</span>
                  <span className="count" style={{ marginLeft: 12 }}>
                    {c.documents.length} docs
                  </span>
                </div>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => onDeleteCollection(c.id)}
                >
                  削除
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ──────────────────────────────────────────────
// 内部コンポーネント
// ──────────────────────────────────────────────

function DocumentTable({
  documents,
  onDelete,
}: {
  documents: DocumentItem[];
  onDelete: (id: number) => void;
}) {
  if (documents.length === 0) {
    return <p className="section-hint">このコレクションにはまだドキュメントがありません。</p>;
  }
  return (
    <table className="doc-table">
      <thead>
        <tr>
          <th>Filename</th>
          <th>Size</th>
          <th>Pages</th>
          <th>Status</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {documents.map((d) => (
          <tr key={d.id}>
            <td>{d.filename}</td>
            <td>{formatBytes(d.file_size)}</td>
            <td>{d.page_count ?? '—'}</td>
            <td>
              <span className={`status-pill status-${d.status}`}>{statusLabel(d.status)}</span>
            </td>
            <td style={{ textAlign: 'right' }}>
              <button type="button" className="btn-danger" onClick={() => onDelete(d.id)}>
                削除
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function statusLabel(s: DocumentStatus): string {
  switch (s) {
    case 'pending':
      return 'pending';
    case 'indexing':
      return 'indexing';
    case 'ready':
      return 'ready';
    case 'error':
      return 'error';
  }
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
