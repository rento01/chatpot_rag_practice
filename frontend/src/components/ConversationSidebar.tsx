'use client';
import type { Conversation } from '@/lib/types';

/**
 * 会話一覧のサイドバー。
 * 教材向けに、ピン留め・アーカイブなどは持たない。
 */
type Props = {
  conversations: Conversation[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
};

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
}: Props) {
  return (
    <aside className="sidebar" aria-label="Conversation history">
      <div className="sidebar-head">
        <h2>Conversations</h2>
        <button className="new-conv-btn" onClick={onNew} type="button">
          + New
        </button>
      </div>

      {conversations.length === 0 ? (
        <div className="conv-empty">
          まだ会話がありません。下のメッセージ欄に質問を入力すると、
          自動的に新しい会話として記録されます。
        </div>
      ) : (
        <ul className="conv-list">
          {conversations.map((conv) => (
            <li
              key={conv.id}
              className={`conv-item ${conv.id === activeId ? 'active' : ''}`}
              onClick={() => onSelect(conv.id)}
            >
              <span className="conv-title">{conv.title || '無題の会話'}</span>
              <span className="conv-meta">{conv.message_count}</span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
