const BASE_URL = 'http://127.0.0.1:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
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
      auth_ok: boolean;
      api_key_present: boolean;
    }>('/status'),

  // Providers / Models
  getProviders: () =>
    request<{ id: string; name: string }[]>('/providers'),

  getModels: (provider: string) =>
    request<{ id: string; name: string }[]>(
      `/models?provider=${provider}`
    ),

  // Config
  setup: (payload: {
    provider: string;
    model_id: string;
    api_key?: string;
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
  
  verifyConfig: () =>
      request<{ ok: true }>('/config/verify', {
        method: 'POST',
      }),
    

  // Chat
  chat: async (payload: {
    model_id: string;
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
}  
