'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Collection, DocumentItem } from '@/lib/types';
import {
  createCollection,
  deleteCollection,
  uploadDocuments,
  deleteDocument,
  getDocumentText,
} from '@/lib/api';

interface Props {
  collections: Collection[];
  onRefresh: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentPanel({ collections, onRefresh }: Props) {
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [targetCollectionId, setTargetCollectionId] = useState<number | null>(null);
  const [viewModal, setViewModal] = useState<{ filename: string; text: string } | null>(null);
  const [loadingDocId, setLoadingDocId] = useState<number | null>(null);

  // Poll while any document is pending/indexing
  useEffect(() => {
    const hasPending = collections.some((col) =>
      col.documents.some((d) => d.status === 'pending' || d.status === 'indexing'),
    );
    if (!hasPending) return;
    const timer = setInterval(onRefresh, 2000);
    return () => clearInterval(timer);
  }, [collections, onRefresh]);

  const toggleExpand = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleCreate = useCallback(async () => {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      await createCollection(name);
      setNewName('');
      onRefresh();
    } finally {
      setCreating(false);
    }
  }, [newName, onRefresh]);

  const handleDeleteCollection = useCallback(
    async (id: number) => {
      if (!confirm('このコレクションとすべてのドキュメントを削除しますか？')) return;
      await deleteCollection(id);
      onRefresh();
    },
    [onRefresh],
  );

  const handleDeleteDocument = useCallback(
    async (id: number) => {
      await deleteDocument(id);
      onRefresh();
    },
    [onRefresh],
  );

  const handleViewDocument = useCallback(async (id: number) => {
    setLoadingDocId(id);
    try {
      const { text, filename } = await getDocumentText(id);
      setViewModal({ filename, text });
    } finally {
      setLoadingDocId(null);
    }
  }, []);

  const handleUpload = useCallback(
    async (collectionId: number, files: FileList | null) => {
      if (!files || files.length === 0) return;
      const pdfFiles = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.pdf'));
      if (pdfFiles.length === 0) return;
      setUploading(collectionId);
      try {
        await uploadDocuments(collectionId, pdfFiles);
        setExpanded((prev) => new Set([...prev, collectionId]));
        onRefresh();
      } finally {
        setUploading(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
        if (folderInputRef.current) folderInputRef.current.value = '';
      }
    },
    [onRefresh],
  );

  return (
    <>
      <div className="doc-panel">
        {/* New collection form */}
        <div className="doc-new-wrap">
          <input
            className="doc-new-input"
            placeholder="コレクション名..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          />
          <button className="doc-new-btn" onClick={handleCreate} disabled={creating || !newName.trim()}>
            作成
          </button>
        </div>

        {/* Hidden file inputs */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          style={{ display: 'none' }}
          onChange={(e) => {
            if (targetCollectionId !== null) handleUpload(targetCollectionId, e.target.files);
          }}
        />
        <input
          ref={folderInputRef}
          type="file"
          accept=".pdf"
          // @ts-expect-error webkitdirectory is not in TS types
          webkitdirectory=""
          multiple
          style={{ display: 'none' }}
          onChange={(e) => {
            if (targetCollectionId !== null) handleUpload(targetCollectionId, e.target.files);
          }}
        />

        {/* Collection list */}
        <div className="doc-list">
          {collections.length === 0 && (
            <div className="sidebar-empty">コレクションがありません</div>
          )}

          {collections.map((col) => (
            <div key={col.id} className="doc-collection">
              <div className="doc-col-header" onClick={() => toggleExpand(col.id)}>
                <svg
                  className={`doc-chevron${expanded.has(col.id) ? ' open' : ''}`}
                  width="10"
                  height="10"
                  viewBox="0 0 10 10"
                  fill="none"
                >
                  <path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="doc-col-name">{col.name}</span>
                <span className="doc-col-count">{col.documents.length}</span>

                <div className="doc-col-actions" onClick={(e) => e.stopPropagation()}>
                  {/* Upload files */}
                  <button
                    className="doc-action-btn"
                    title="PDFをアップロード"
                    onClick={() => {
                      setTargetCollectionId(col.id);
                      setTimeout(() => fileInputRef.current?.click(), 0);
                    }}
                    disabled={uploading === col.id}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                  </button>
                  {/* Upload folder */}
                  <button
                    className="doc-action-btn"
                    title="フォルダをアップロード"
                    onClick={() => {
                      setTargetCollectionId(col.id);
                      setTimeout(() => folderInputRef.current?.click(), 0);
                    }}
                    disabled={uploading === col.id}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                      <line x1="12" y1="11" x2="12" y2="17" />
                      <polyline points="9 14 12 11 15 14" />
                    </svg>
                  </button>
                  {/* Delete collection */}
                  <button
                    className="doc-action-btn danger"
                    title="コレクションを削除"
                    onClick={() => handleDeleteCollection(col.id)}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    </svg>
                  </button>
                </div>
              </div>

              {uploading === col.id && (
                <div className="doc-uploading">処理中...</div>
              )}

              {expanded.has(col.id) && (
                <div className="doc-files">
                  {col.documents.length === 0 && (
                    <div className="doc-empty">PDFをアップロードしてください</div>
                  )}
                  {col.documents.map((doc) => (
                    <DocFileRow
                      key={doc.id}
                      doc={doc}
                      loading={loadingDocId === doc.id}
                      onView={handleViewDocument}
                      onDelete={handleDeleteDocument}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Markdown viewer modal */}
      {viewModal && (
        <div className="doc-modal-overlay" onClick={() => setViewModal(null)}>
          <div className="doc-modal" onClick={(e) => e.stopPropagation()}>
            <div className="doc-modal-header">
              <span className="doc-modal-title">{viewModal.filename}</span>
              <button className="doc-modal-close" onClick={() => setViewModal(null)} aria-label="閉じる">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <div className="doc-modal-body">
              <ReactMarkdown>{viewModal.text || '（テキストなし）'}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const STATUS_LABEL: Record<string, string> = {
  pending: '待機中',
  indexing: 'インデックス中',
  ready: '',
  error: 'エラー',
};

function DocFileRow({
  doc,
  loading,
  onView,
  onDelete,
}: {
  doc: DocumentItem;
  loading: boolean;
  onView: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const isProcessing = doc.status === 'pending' || doc.status === 'indexing';

  return (
    <div className="doc-file-row">
      <span className="doc-file-name" title={doc.filename}>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span>{doc.filename}</span>
      </span>
      {doc.status !== 'ready' && (
        <span className={`doc-status-badge doc-status-${doc.status}`}>
          {isProcessing && (
            <svg width="9" height="9" viewBox="0 0 10 10" fill="none" className="doc-status-spin">
              <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="6 4" />
            </svg>
          )}
          {STATUS_LABEL[doc.status]}
        </span>
      )}
      {doc.status === 'ready' && (
        <span className="doc-file-meta">
          {doc.page_count != null ? `${doc.page_count}p · ` : ''}
          {formatBytes(doc.file_size)}
        </span>
      )}
      <button
        className="doc-action-btn"
        onClick={() => onView(doc.id)}
        title="テキストを表示"
        disabled={loading || isProcessing}
      >
        {loading ? (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="doc-status-spin">
            <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="6 4" />
          </svg>
        ) : (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
      <button
        className="doc-action-btn danger"
        onClick={() => onDelete(doc.id)}
        title="削除"
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M1 1l8 8M9 1L1 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}
