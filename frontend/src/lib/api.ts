import type { Collection, Conversation, ConversationDetail, ChatMessage, DeepResearchProgress, DocumentItem } from './types';

const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = RequestInit & {
  timeoutMs?: number;
  /** タイムアウト・エラー時に表示するアクション名（例: "会話一覧の取得"） */
  action?: string;
};

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const contentType = res.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      const body = await res.json();
      if (body && typeof body === 'object' && 'detail' in body) {
        const detail = (body as { detail: unknown }).detail;
        if (typeof detail === 'string') return detail;
        return JSON.stringify(detail);
      }
      return JSON.stringify(body);
    }
    return await res.text();
  } catch {
    return '';
  }
}

async function request(path: string, options: RequestOptions = {}): Promise<Response> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, action, signal: externalSignal, ...init } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new DOMException('Timeout', 'TimeoutError')), timeoutMs);
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort(externalSignal.reason);
    else externalSignal.addEventListener('abort', () => controller.abort(externalSignal.reason), { once: true });
  }

  try {
    const res = await fetch(path, { ...init, signal: controller.signal });
    if (!res.ok) {
      const detail = await extractErrorDetail(res);
      throw new ApiError(res.status, detail || `${action ?? path} に失敗しました`);
    }
    return res;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      if (externalSignal?.aborted) throw err;
      throw new ApiError(0, `${action ?? path} がタイムアウトしました (${timeoutMs}ms)`);
    }
    throw new ApiError(0, `${action ?? path} 中にネットワークエラーが発生しました`);
  } finally {
    clearTimeout(timer);
  }
}

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const res = await request(path, options);
  return res.json() as Promise<T>;
}

export async function listConversations(): Promise<Conversation[]> {
  return requestJson('/api/conversations', { action: '会話一覧の取得' });
}

export async function createConversation(title?: string): Promise<Conversation> {
  return requestJson('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title ?? null }),
    action: '会話の作成',
  });
}

export async function getConversation(id: number): Promise<ConversationDetail> {
  return requestJson(`/api/conversations/${id}`, { action: '会話詳細の取得' });
}

export async function updateConversation(
  id: number,
  patch: { title?: string; pinned?: boolean; archived?: boolean },
): Promise<Conversation> {
  return requestJson(`/api/conversations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
    action: '会話の更新',
  });
}

export async function deleteConversation(id: number): Promise<void> {
  await request(`/api/conversations/${id}`, { method: 'DELETE', action: '会話の削除' });
}

export async function listCollections(): Promise<Collection[]> {
  return requestJson('/api/collections', { action: 'コレクション一覧の取得' });
}

export async function createCollection(name: string): Promise<Collection> {
  return requestJson('/api/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
    action: 'コレクションの作成',
  });
}

export async function deleteCollection(id: number): Promise<void> {
  await request(`/api/collections/${id}`, { method: 'DELETE', action: 'コレクションの削除' });
}

export async function uploadDocuments(collectionId: number, files: File[]): Promise<DocumentItem[]> {
  const form = new FormData();
  for (const file of files) form.append('files', file);
  return requestJson(`/api/collections/${collectionId}/documents`, {
    method: 'POST',
    body: form,
    timeoutMs: 120_000,
    action: 'ドキュメントのアップロード',
  });
}

export async function deleteDocument(id: number): Promise<void> {
  await request(`/api/documents/${id}`, { method: 'DELETE', action: 'ドキュメントの削除' });
}

export function getDocumentFileUrl(id: number): string {
  return `/api/documents/${id}/file`;
}

export async function getDocumentText(id: number): Promise<{ text: string; filename: string }> {
  return requestJson(`/api/documents/${id}/text`, { action: 'ドキュメントテキストの取得' });
}

export async function* streamChat(
  messages: ChatMessage[],
  conversationId: number,
  signal?: AbortSignal,
  collectionId?: number | null,
): AsyncGenerator<string> {
  let res: Response;
  try {
    res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages,
        conversation_id: conversationId,
        collection_id: collectionId ?? null,
      }),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError(0, 'チャット送信中にネットワークエラーが発生しました');
  }
  if (!res.ok || !res.body) {
    const detail = await extractErrorDetail(res);
    throw new ApiError(res.status, detail || 'チャット送信に失敗しました');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      yield decoder.decode(value, { stream: true });
    }
  } finally {
    reader.releaseLock();
  }
}

// [P3 DeepResearch]
export async function startDeepResearch(
  query: string,
  collectionId: number,
  conversationId: number | null,
): Promise<string> {
  const res = await fetch('/api/deep-research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      collection_id: collectionId,
      conversation_id: conversationId,
    }),
  });
  if (!res.ok) throw new Error('Deep research request failed');
  const data = await res.json();
  return data.job_id;
}

export async function pollDeepResearch(jobId: string): Promise<DeepResearchProgress> {
  const res = await fetch(`/api/deep-research/${jobId}/progress`);
  if (!res.ok) throw new Error('Failed to poll deep research progress');
  return res.json();
}

export async function saveDeepResearch(jobId: string): Promise<void> {
  const res = await fetch(`/api/deep-research/${jobId}/save`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to save deep research result');
}
