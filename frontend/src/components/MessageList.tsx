'use client';
import type { ChatMessage } from '@/lib/types';

type Props = {
  messages: ChatMessage[];
  streaming: boolean;
  streamingText: string;
};

/**
 * チャットメッセージ列を表示する。Markdown レンダリングは
 * 教材初期段階では入れず、改行のみ保持する単純表示にする。
 */
export default function MessageList({ messages, streaming, streamingText }: Props) {
  if (messages.length === 0 && !streaming) {
    return (
      <div className="chat-empty">
        <h1>RAG Chat Template</h1>
        <p>
          ローカル LLM (Ollama) で動く最小チャット。<br />
          下の <span className="hint-code">RAG</span> トグルを ON にして、
          コレクションを選ぶと、参照モードに切り替わります。
          <br />
          検索本体は Phase 2 以降で実装します。
        </p>
      </div>
    );
  }

  return (
    <div className="chat-thread">
      {messages.map((m, i) => (
        <div key={i} className={`msg msg-${m.role}`}>
          <div className="msg-role">{m.role === 'user' ? 'You' : 'Assistant'}</div>
          <div className="msg-body">{m.content}</div>
        </div>
      ))}
      {streaming && (
        <div className="msg msg-assistant">
          <div className="msg-role">Assistant</div>
          <div className="msg-body msg-streaming">{streamingText || '...'}</div>
        </div>
      )}
    </div>
  );
}
