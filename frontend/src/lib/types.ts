/**
 * バックエンド API と型を揃えるための共有型。
 *
 * 教材としての方針:
 * - 余計なフィールドは型からも消しておく
 * - 「DB スキーマ → Pydantic → ここ」が 1:1 で対応していることが
 *   コードを追うだけで分かるようにする
 */

export interface Conversation {
  id: number;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export type DocumentStatus = 'pending' | 'indexing' | 'ready' | 'error';

export interface DocumentItem {
  id: number;
  collection_id: number;
  filename: string;
  page_count: number | null;
  file_size: number;
  status: DocumentStatus;
  indexed_at: string | null;
  created_at: string;
}

export interface Collection {
  id: number;
  name: string;
  created_at: string;
  documents: DocumentItem[];
}
