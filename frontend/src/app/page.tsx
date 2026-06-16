'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import Sidebar from '@/components/Sidebar';
import MessageList from '@/components/MessageList';
import ChatInput from '@/components/ChatInput';
import {
  listConversations,
  createConversation,
  getConversation,
  deleteConversation,
  updateConversation,
  streamChat,
  listCollections,
  ApiError,
  startDeepResearch,
  pollDeepResearch,
  saveDeepResearch,
} from '@/lib/api';
import type { Collection, Conversation, ChatMessage, DeepResearchProgress, SourceDoc } from '@/lib/types';

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [deepResearch, setDeepResearch] = useState(false);
  const [researchProgress, setResearchProgress] = useState<DeepResearchProgress | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch {
      // silently fail on background refresh
    }
  }, []);

  const loadCollections = useCallback(async () => {
    try {
      setCollections(await listCollections());
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    loadConversations();
    loadCollections();
  }, [loadConversations, loadCollections]);

  const selectConversation = useCallback(async (id: number) => {
    try {
      const detail = await getConversation(id);
      setActiveId(id);
      setMessages(detail.messages.map((m) => {
        let sources: SourceDoc[] | undefined;
        if (m.sources_json) {
          try { sources = JSON.parse(m.sources_json); } catch {}
        }
        return { role: m.role, content: m.content, sources };
      }));
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

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteConversation(id);
        if (activeId === id) newSession();
        await loadConversations();
      } catch {
        setError('削除に失敗しました');
      }
    },
    [activeId, newSession, loadConversations],
  );

  const handleRename = useCallback(
    async (id: number, title: string) => {
      try {
        await updateConversation(id, { title });
        await loadConversations();
      } catch {
        setError('名前の変更に失敗しました');
      }
    },
    [loadConversations],
  );

  const handleTogglePin = useCallback(
    async (id: number) => {
      const conv = conversations.find((c) => c.id === id);
      if (!conv) return;
      try {
        await updateConversation(id, { pinned: !conv.pinned });
        await loadConversations();
      } catch {
        setError('ピン留めの変更に失敗しました');
      }
    },
    [conversations, loadConversations],
  );

  const handleArchive = useCallback(
    async (id: number) => {
      try {
        await updateConversation(id, { archived: true });
        if (activeId === id) newSession();
        await loadConversations();
      } catch {
        setError('アーカイブに失敗しました');
      }
    },
    [activeId, newSession, loadConversations],
  );

  const handleSend = useCallback(
    async (content: string) => {
      if (!content.trim() || streaming) return;
      setError(null);

      let convId = activeId;
      if (convId === null) {
        try {
          const conv = await createConversation(content.slice(0, 50));
          convId = conv.id;
          setActiveId(conv.id);
          setConversations((prev) => [conv, ...prev]);
        } catch (e) {
          setError(e instanceof ApiError ? e.detail : '会話の作成に失敗しました');
          return;
        }
      }

      const userMsg: ChatMessage = { role: 'user', content };
      const nextMessages = [...messages, userMsg];
      setMessages(nextMessages);
      setStreaming(true);
      setStreamingText('');

      if (deepResearch && selectedCollectionId !== null) {
        // [P3 DeepResearch] DeepResearch モード
        try {
          const jobId = await startDeepResearch(content, selectedCollectionId, convId);
          const poll = async () => {
            // eslint-disable-next-line no-constant-condition
            while (true) {
              const progress = await pollDeepResearch(jobId);
              setResearchProgress(progress);
              if (progress.status === 'done') {
                await saveDeepResearch(jobId);
                if (convId !== null) {
                  const detail = await getConversation(convId);
                  setMessages(detail.messages.map((m) => ({ role: m.role, content: m.content })));
                }
                setResearchProgress(null);
                await loadConversations();
                break;
              }
              if (progress.status === 'error') {
                setError(`DeepResearch エラー: ${progress.error ?? '不明なエラー'}`);
                setResearchProgress(null);
                break;
              }
              await new Promise((r) => setTimeout(r, 1500));
            }
          };
          await poll();
        } catch {
          setError('DeepResearch の実行に失敗しました');
          setResearchProgress(null);
        } finally {
          setStreaming(false);
        }
      } else {
        // 通常チャットモード
        const controller = new AbortController();
        abortRef.current = controller;

        let accumulated = '';
        let aborted = false;
        try {
          const SOURCES_MARKER = '\n\n__SOURCES__\n';
          for await (const chunk of streamChat(nextMessages, convId, controller.signal, selectedCollectionId)) {
            accumulated += chunk;
            const markerIdx = accumulated.indexOf(SOURCES_MARKER);
            setStreamingText(markerIdx !== -1 ? accumulated.slice(0, markerIdx) : accumulated);
          }
        } catch (e: unknown) {
          if (e instanceof Error && e.name === 'AbortError') {
            aborted = true;
          } else {
            setError(e instanceof ApiError ? e.detail : '応答の取得に失敗しました');
          }
        } finally {
          const SOURCES_MARKER = '\n\n__SOURCES__\n';
          const markerIdx = accumulated.indexOf(SOURCES_MARKER);
          let finalText = accumulated;
          let sources: SourceDoc[] | undefined;
          if (markerIdx !== -1) {
            finalText = accumulated.slice(0, markerIdx);
            try { sources = JSON.parse(accumulated.slice(markerIdx + SOURCES_MARKER.length)); } catch {}
          }
          if (aborted && finalText) {
            finalText += '\n\n_（停止しました）_';
          }
          if (finalText) {
            setMessages((prev) => [...prev, { role: 'assistant', content: finalText, sources }]);
          }
          await loadConversations();
          setStreaming(false);
          setStreamingText('');
          abortRef.current = null;
        }
      }
    },
    [activeId, messages, streaming, loadConversations, selectedCollectionId, deepResearch],
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return (
    <div className="app-shell">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={newSession}
        onDelete={handleDelete}
        onRename={handleRename}
        onTogglePin={handleTogglePin}
        onArchive={handleArchive}
        collections={collections}
        onRefreshCollections={loadCollections}
      />
      <main className="main-area">
        <MessageList
          messages={messages}
          streaming={streaming}
          streamingText={streamingText}
          researchProgress={researchProgress}
        />
        {error && (
          <div className="error-toast" onClick={() => setError(null)}>
            {error}
          </div>
        )}
        <ChatInput
          onSend={handleSend}
          disabled={streaming}
          streaming={streaming}
          onStop={stopStreaming}
          collections={collections}
          selectedCollectionId={selectedCollectionId}
          onCollectionChange={setSelectedCollectionId}
          deepResearch={deepResearch}
          onDeepResearchChange={setDeepResearch}
        />
      </main>
    </div>
  );
}
