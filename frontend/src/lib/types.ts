export interface Conversation {
  id: number;
  title: string | null;
  pinned: boolean;
  archived: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources_json?: string | null;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface SourceDoc {
  id: number;
  filename: string;
  heading?: string;
  content?: string;
  chunk_index?: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceDoc[];
}

export interface DocumentItem {
  id: number;
  collection_id: number;
  filename: string;
  page_count: number | null;
  file_size: number;
  status: 'pending' | 'indexing' | 'ready' | 'error';
  indexed_at: string | null;
  created_at: string;
}

export interface Collection {
  id: number;
  name: string;
  created_at: string;
  documents: DocumentItem[];
}

// [P3 DeepResearch]
export interface DeepResearchSource {
  source_file: string;
  heading: string;
  content: string;
  document_id: number | null;
}

export interface DeepResearchSubQuery {
  sub_query: string;
  status: 'pending' | 'searching' | 'done';
  sources: DeepResearchSource[];
}

export interface DeepResearchProgress {
  job_id: string;
  status: 'decomposing' | 'searching' | 'synthesizing' | 'done' | 'error';
  query: string;
  sub_queries: DeepResearchSubQuery[];
  final_answer: string | null;
  error: string | null;
}
