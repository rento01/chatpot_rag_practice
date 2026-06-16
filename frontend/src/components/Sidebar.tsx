'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import type { Collection, Conversation } from '@/lib/types';
import DocumentPanel from './DocumentPanel';

interface Props {
  conversations: Conversation[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onDelete: (id: number) => void;
  onRename: (id: number, title: string) => void;
  onTogglePin: (id: number) => void;
  onArchive: (id: number) => void;
  collections: Collection[];
  onRefreshCollections: () => void;
}

interface Group {
  label: string;
  items: Conversation[];
}

function groupByDate(conversations: Conversation[]): Group[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86_400_000);
  const weekAgo = new Date(today.getTime() - 7 * 86_400_000);

  const groups: Group[] = [
    { label: 'ピン留め', items: [] },
    { label: '今日', items: [] },
    { label: '昨日', items: [] },
    { label: '過去7日間', items: [] },
    { label: 'それ以前', items: [] },
  ];

  for (const conv of conversations) {
    if (conv.archived) continue;
    if (conv.pinned) {
      groups[0].items.push(conv);
      continue;
    }
    const d = new Date(conv.updated_at);
    if (d >= today) groups[1].items.push(conv);
    else if (d >= yesterday) groups[2].items.push(conv);
    else if (d >= weekAgo) groups[3].items.push(conv);
    else groups[4].items.push(conv);
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onRename,
  onTogglePin,
  onArchive,
  collections,
  onRefreshCollections,
}: Props) {
  const [tab, setTab] = useState<'chat' | 'docs'>('chat');
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const editRef = useRef<HTMLInputElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.conv-dropdown') && !target.closest('.conv-menu-btn')) {
        setOpenMenuId(null);
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  useEffect(() => {
    if (editingId !== null) editRef.current?.focus();
  }, [editingId]);

  const filtered = conversations.filter((c) =>
    (c.title ?? '').toLowerCase().includes(searchQuery.toLowerCase()),
  );
  const groups = groupByDate(filtered);

  const startEdit = useCallback((conv: Conversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title ?? '');
    setOpenMenuId(null);
  }, []);

  const commitEdit = useCallback(
    (id: number) => {
      if (editTitle.trim()) onRename(id, editTitle.trim());
      setEditingId(null);
    },
    [editTitle, onRename],
  );

  const cancelEdit = useCallback(() => setEditingId(null), []);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          話し相手<span>.</span>AI
        </div>
        {/* Tab switcher */}
        <div className="sidebar-tabs">
          <button
            className={`sidebar-tab${tab === 'chat' ? ' active' : ''}`}
            onClick={() => setTab('chat')}
          >
            チャット
          </button>
          <button
            className={`sidebar-tab${tab === 'docs' ? ' active' : ''}`}
            onClick={() => setTab('docs')}
          >
            ドキュメント
          </button>
        </div>
        {tab === 'chat' && (
          <button className="btn-new" onClick={onNew}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path
                d="M7 1v12M1 7h12"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            新しいセッションを開始
          </button>
        )}
      </div>

      {tab === 'docs' && (
        <DocumentPanel collections={collections} onRefresh={onRefreshCollections} />
      )}

      {/* Search + list — only shown in chat tab */}
      {tab === 'chat' && (<>
      <div className="sidebar-search-wrap">
        <svg
          className="sidebar-search-icon"
          width="13"
          height="13"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.5" />
          <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          placeholder="履歴を検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="sidebar-search-input"
          aria-label="会話を検索"
        />
        {searchQuery && (
          <button
            className="sidebar-search-clear"
            onClick={() => setSearchQuery('')}
            aria-label="検索をクリア"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path
                d="M1 1l8 8M9 1L1 9"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        )}
      </div>

      <div className="sidebar-list">
        {groups.length === 0 && (
          <div className="sidebar-empty">
            {searchQuery ? '一致する会話が見つかりません' : 'まだ会話がありません'}
          </div>
        )}

        {groups.map((group) => (
          <div key={group.label} className="sidebar-group">
            <span className="sidebar-date-label">{group.label}</span>

            {group.items.map((conv) => (
              <div
                key={conv.id}
                className={`conv-item${activeId === conv.id ? ' active' : ''}`}
                onClick={() => editingId !== conv.id && onSelect(conv.id)}
              >
                {editingId === conv.id ? (
                  <div className="conv-edit-wrap" onClick={(e) => e.stopPropagation()}>
                    <input
                      ref={editRef}
                      className="conv-edit-input"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') commitEdit(conv.id);
                        if (e.key === 'Escape') cancelEdit();
                      }}
                      onBlur={() => commitEdit(conv.id)}
                    />
                    <button
                      className="conv-edit-ok"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        commitEdit(conv.id);
                      }}
                      aria-label="確定"
                    >
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path
                          d="M1 5l3 3 5-7"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                    <button
                      className="conv-edit-cancel"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        cancelEdit();
                      }}
                      aria-label="キャンセル"
                    >
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path
                          d="M1 1l8 8M9 1L1 9"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                        />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="conv-item-label">
                      {conv.pinned && (
                        <svg
                          className="conv-pin-icon"
                          width="9"
                          height="9"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                          aria-hidden="true"
                        >
                          <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z" />
                        </svg>
                      )}
                      {conv.title ?? `会話 #${conv.id}`}
                    </span>

                    <div className="conv-item-actions">
                      {conv.message_count > 0 && (
                        <span className="conv-msg-count">{conv.message_count}</span>
                      )}
                      <div className="conv-menu-wrap">
                        <button
                          className="conv-menu-btn"
                          title="オプション"
                          onClick={(e) => {
                            e.stopPropagation();
                            setOpenMenuId(openMenuId === conv.id ? null : conv.id);
                          }}
                          aria-label="オプションメニュー"
                        >
                          <svg width="13" height="3" viewBox="0 0 13 3" fill="currentColor" aria-hidden="true">
                            <circle cx="1.5" cy="1.5" r="1.5" />
                            <circle cx="6.5" cy="1.5" r="1.5" />
                            <circle cx="11.5" cy="1.5" r="1.5" />
                          </svg>
                        </button>

                        {openMenuId === conv.id && (
                          <div className="conv-dropdown" role="menu">
                            <button
                              className="conv-dropdown-item"
                              role="menuitem"
                              onClick={(e) => {
                                e.stopPropagation();
                                startEdit(conv);
                              }}
                            >
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                              </svg>
                              名前を変更
                            </button>
                            <button
                              className="conv-dropdown-item"
                              role="menuitem"
                              onClick={(e) => {
                                e.stopPropagation();
                                onTogglePin(conv.id);
                                setOpenMenuId(null);
                              }}
                            >
                              <svg width="12" height="12" viewBox="0 0 24 24" fill={conv.pinned ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                                <circle cx="12" cy="10" r="3" />
                              </svg>
                              {conv.pinned ? 'ピン留め解除' : 'ピン留め'}
                            </button>
                            <button
                              className="conv-dropdown-item"
                              role="menuitem"
                              onClick={(e) => {
                                e.stopPropagation();
                                onArchive(conv.id);
                                setOpenMenuId(null);
                              }}
                            >
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="21 8 21 21 3 21 3 8" />
                                <rect x="1" y="3" width="22" height="5" />
                                <line x1="10" y1="12" x2="14" y2="12" />
                              </svg>
                              アーカイブ
                            </button>
                            <div className="conv-dropdown-sep" />
                            <button
                              className="conv-dropdown-item danger"
                              role="menuitem"
                              onClick={(e) => {
                                e.stopPropagation();
                                onDelete(conv.id);
                                setOpenMenuId(null);
                              }}
                            >
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                                <path d="M10 11v6M14 11v6" />
                                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                              </svg>
                              削除
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
      </>)}
    </aside>
  );
}
