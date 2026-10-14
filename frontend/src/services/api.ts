const BASE_URL = 'http://127.0.0.1:8000';

/** Turn a failed response into a readable message (unwraps FastAPI's {"detail": ...}). */
async function readError(res: Response): Promise<string> {
  const text = await res.text();
  let detail = text;
  try {
    const j = JSON.parse(text);
    detail =
      typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j);
  } catch {
    /* not JSON, keep raw text */
  }
  return detail || `Request failed: ${res.status}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    throw new Error(await readError(res));
  }

  return res.json();
}

let onAuthStateChange: (() => Promise<void>) | null = null;

export const registerAuthSync = (fn: () => Promise<void>) => {
  onAuthStateChange = fn;
};

export const api = {
  // System
  getStatus: () =>
    request<{
      configured: boolean;
      provider: string | null;
      model: string | null;
      display_name: string | null;
      auth_ok: boolean | null;
      api_key_present: boolean;
      chat_enabled: boolean;
      last_error: { code: string; message: string } | null;
    }>('/status'),

  // Providers / Models
  getProviders: () =>
    request<{ id: string; name: string }[]>('/providers'),

  getModels: (provider: string) =>
    request<{ id: string; name: string }[]>(
      `/models?provider=${provider}`
    ),

  // Live model list for a provider (backend: POST /providers/models).
  // Omit api_key to reuse a key already saved for that provider.
  getProviderModels: (payload: { provider: string; api_key?: string }) =>
    request<{
      provider: string;
      models: {
        id: string;
        owned_by: string | null;
        already_added: boolean;
        free: boolean | null;
      }[];
    }>('/providers/models', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Config
  setup: (payload: {
    provider: string;
    model_id: string;
    api_key?: string;
    base_url?: string;
  }) =>
    request<{ ok: true }>('/config/setup', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateConfig: (payload: { api_key?: string }) =>
    request<{ ok: true }>('/config/update', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  resetConfig: () =>
    request<{ ok: true }>('/config/reset', {
      method: 'POST',
    }),

  verifyConfig: async () => {
    // verified=false means "could not confirm" (network, rate limit, model gone);
    // `detail` then explains why.
    try {
      return await request<{
        ok: true;
        verified?: boolean;
        detail?: string;
      }>('/config/verify', {
        method: 'POST',
      });
    } finally {
      // force frontend to sync with backend, even after a 401
      // (the backend records auth_ok=false, so the lock reason stays current)
      if (onAuthStateChange) {
        try {
          await onAuthStateChange();
        } catch {
          /* never mask the original result/error */
        }
      }
    }
  },

  // Registry: Load backend model registry
  getConfigModels: () =>
    request<
      {
        id: string;
        provider: string;
        model: string;
        name: string;
        meta: { size: string | null; quantization: string | null };
        is_active: boolean;
      }[]
    >('/config/models'),

  // Registry: Delete a model
  deleteModel: (payload: { model_id: string }) =>
    request<{ ok: boolean; models: any[] }>('/config/models/delete', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // History
  getHistory: () =>
    request<
      { id: string; title: string; preview: string; timestamp: string }[]
    >('/history'),

  getConversation: (id: string) =>
    request<{
      id: string;
      title: string;
      messages: {
        id: string;
        role: 'user' | 'assistant';
        content: string;
        model: string | null;
        timestamp: string;
      }[];
    }>(`/history/${id}`),

  renameConversation: (id: string, title: string) =>
    request<{ ok: true; title: string }>(`/history/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),

  deleteConversation: (id: string) =>
    request<{ ok: true }>(`/history/${id}`, { method: 'DELETE' }),

  clearHistory: () => request<{ ok: true }>('/history', { method: 'DELETE' }),

  // Registry: Add a model (omit api_key to reuse a saved key for the provider)
  addModel: (payload: {
    provider: string;
    model: string;
    api_key?: string;
    base_url?: string;
  }) =>
    request<{ model_id: string; message: string }>('/config/models/add', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Registry: Switch the active model
  switchModel: (payload: { model_id: string }) =>
    request<{ active_model_id: string; message: string }>(
      '/config/models/switch',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  // Chat (streaming): tokens are delivered to onToken as they arrive
  chatStream: async (
    payload: {
      messages: { role: string; content: string }[];
      conversation_id?: string | null;
    },
    onToken: (text: string) => void,
    options?: {
      signal?: AbortSignal;
      /** Called with the conversation id the backend assigned or confirmed */
      onConversation?: (id: string) => void;
    }
  ) => {
    try {
      const res = await fetch(`${BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: options?.signal,
      });

      if (!res.ok) {
        throw new Error(await readError(res));
      }

      const conversationId = res.headers.get('X-Conversation-Id');
      if (conversationId) {
        options?.onConversation?.(conversationId);
      }

      if (!res.body) {
        throw new Error('Streaming is not supported by this browser');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        if (text) onToken(text);
      }
      const tail = decoder.decode();
      if (tail) onToken(tail);
    } catch (err) {
      // auth/model state may have changed → resync once
      if (onAuthStateChange) {
        await onAuthStateChange();
      }
      throw err;
    }
  },

  // Chat
  chat: async (payload: {
    messages: { role: string; content: string }[];
  }) => {
    try {
      return await request<{ content: string }>('/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch (err) {
      // auth may have changed → resync once
      if (onAuthStateChange) {
        await onAuthStateChange();
      }
      throw err;
    }
  },
};
