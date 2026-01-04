export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface Model {
  id: string;
  name: string;
  size: string;
  quantization: string;
}

export interface HistoryItem {
  id: string;
  title: string;
  timestamp: Date;
  preview: string;
}

export type ContextStatus = 'safe' | 'warning' | 'critical';

// New types for Configuration Flow
export interface AppStatus {
  configured: boolean;
  last_model: string | null;
}

export interface ConfigPayload {
  modelId: string;
  apiKey: string;
}

// New types for Model Management
export interface StoredModel {
  id: string;
  name: string;
  provider: string;
  apiKey: string;
}
