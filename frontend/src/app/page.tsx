'use client';
import { useCallback, useEffect, useRef, useState } from 'react';

import ChatComposer from '@/components/ChatComposer';
import ConversationSidebar from '@/components/ConversationSidebar';
import MessageList from '@/components/MessageList';
import {
  ApiError,
  createConversation,
  getConversation,
  listCollections,
  listConversations,
  streamChat,
} from '@/lib/api';
import type { ChatMessage, Collection, Conversation } from '@/lib/types';

/**
 * チャット画面。
 *
 * 教材として、ここ 1 ファイルに状態管理ロジックを集約しておく。
 * フックの分割はあえてせず、初学者が React フックの並びをそのまま
 * 上から下に読めるようにしている。
 */
export default function ChatPage() {
  // 会話まわり
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // ストリーミング
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  // コレクション + RAG モード
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [useRag, setUseRag] = useState(false);

  const [error, setError] = useState<string | null>(null);

  // ──────────────────────────────────────────────
  // 初期ロード
  // ──────────────────────────────────────────────
  const loadConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch {
      // 一覧の取得失敗はトーストにせず、サイドバーに反映しないだけ
    }
  }, []);

  const loadCollections = useCallback(async () => {
    try {
      setCollections(await listCollections());
    } catch {
      // 同上
    }
  }, []);

  useEffect(() => {
    loadConversations();
    loadCollections();
  }, [loadConversations, loadCollections]);

  // ──────────────────────────────────────────────
  // 会話操作
  // ──────────────────────────────────────────────
  const selectConversation = useCallback(async (id: number) => {
    try {
      const detail = await getConversation(id);
      setActiveId(id);
      setMessages(
        detail.messages.map((m) => ({ role: m.role, content: m.content })),
      );
      setError(null);
    } catch {
      setError('会話の読み込みに失敗しました');
    }
  }, []);

  const newSession = useCallback(() => {
    setActiveId(null);
    setMessages([]);
    setError(null);
  }, []);

  // ──────────────────────────────────────────────
  // 送信
  // ──────────────────────────────────────────────
  const send = useCallback(
    async (content: string) => {
      if (!content || streaming) return;
      setError(null);

      // 会話がまだ無ければ最初の発話タイトルで自動作成する
      let convId = activeId;
      if (convId === null) {
        try {
          const conv = await createConversation(content.slice(0, 50));
          convId = conv.id;
          setActiveId(conv.id);
          setConversations((prev) => [conv, ...prev]);
        } catch (e) {
          setError(
            e instanceof ApiError ? e.detail : '会話の作成に失敗しました',
          );
          return;
        }
      }

      const userMsg: ChatMessage = { role: 'user', content };
      const nextMessages = [...messages, userMsg];
      setMessages(nextMessages);
      setStreaming(true);
      setStreamingText('');

      const controller = new AbortController();
      abortRef.current = controller;

      let accumulated = '';
      let aborted = false;

      try {
        for await (const chunk of streamChat(nextMessages, {
          conversationId: convId,
          collectionId: selectedCollectionId,
          useRag,
          signal: controller.signal,
        })) {
          accumulated += chunk;
          setStreamingText(accumulated);
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') {
          aborted = true;
        } else {
          setError(e instanceof ApiError ? e.detail : '応答の取得に失敗しました');
        }
      } finally {
        const finalText =
          aborted && accumulated
            ? `${accumulated}\n\n_（停止しました）_`
            : accumulated;
        if (finalText) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: finalText },
          ]);
        }
        await loadConversations();
        setStreaming(false);
        setStreamingText('');
        abortRef.current = null;
      }
    },
    [activeId, messages, streaming, selectedCollectionId, useRag, loadConversations],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // ──────────────────────────────────────────────
  // 描画
  // ──────────────────────────────────────────────
  return (
    <div className="chat-shell">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={newSession}
      />

      <main className="chat-main">
        <MessageList
          messages={messages}
          streaming={streaming}
          streamingText={streamingText}
        />

        {error && (
          <div
            className="error-banner"
            role="alert"
            onClick={() => setError(null)}
            title="クリックで閉じる"
          >
            {error}
          </div>
        )}

        <ChatComposer
          onSend={send}
          onStop={stop}
          streaming={streaming}
          collections={collections}
          selectedCollectionId={selectedCollectionId}
          onCollectionChange={setSelectedCollectionId}
          useRag={useRag}
          onUseRagChange={setUseRag}
        />
      </main>
    </div>
  );
}
