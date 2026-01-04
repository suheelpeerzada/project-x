import { useEffect, useState } from 'react';
import { api, registerAuthSync } from '../services/api';

export interface SystemState {
  configured: boolean;
  provider: string | null;
  model: string | null;
  display_name: string | null;
  auth_ok: boolean | null;
  api_key_present: boolean;
}

export function useAppConfig() {
  const [state, setState] = useState<SystemState | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const status = await api.getStatus();
    setState(status);
  };

  // Load status on boot
  useEffect(() => {
    api
      .getStatus()
      .then(setState)
      .finally(() => setLoading(false));
  }, []);

  // Register auth sync ONCE
  useEffect(() => {
    registerAuthSync(refresh);
  }, []);

  // 🔹 First-time setup
  const setup = async (payload: {
    provider: string;
    model_id: string;
    api_key?: string;
  }) => {
    await api.setup(payload);
    await refresh();
  };

  // 🔹 Update config from settings
  const updateConfig = async (payload: {
    model_id?: string;
    api_key?: string;
  }) => {
    await api.updateConfig(payload);
  
    try {
      await api.verifyConfig(); // ← THIS IS THE FIX
    } catch {
      // auth stays false, UI will lock chat
    }
  
    await refresh();
  };
  
  

  // 🔹 Full reset
  const reset = async () => {
    await api.resetConfig();
    setState(null);
  };

  return {
    state,
    loading,
    setup,
    updateConfig,
    reset,
    refresh,
  };
}