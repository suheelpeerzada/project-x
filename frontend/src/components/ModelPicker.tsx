import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, Search, Check } from 'lucide-react';
import { api } from '../services/api';
import { cn } from '../lib/utils';

/* =========================
   Types
========================= */

interface Provider {
  id: string;
  name: string;
}

interface LiveModel {
  id: string;
  owned_by: string | null;
  already_added: boolean;
  free: boolean | null;
}

export interface AddModelPayload {
  provider: string;
  model: string;
  /** Omitted => backend should reuse the key already saved for this provider */
  apiKey?: string;
}

interface ModelPickerProps {
  onAdd: (payload: AddModelPayload) => Promise<void>;
}

/* =========================
   Component
========================= */

export const ModelPicker: React.FC<ModelPickerProps> = ({ onAdd }) => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [provider, setProvider] = useState('');
  const [apiKey, setApiKey] = useState('');

  const [models, setModels] = useState<LiveModel[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    api.getProviders().then(setProviders).catch(() => setProviders([]));
  }, []);

  // Changing provider invalidates everything below it
  useEffect(() => {
    setModels(null);
    setSelected(null);
    setError(null);
    setFilter('');
  }, [provider]);

  const loadModels = async () => {
    if (!provider) return;
    setLoading(true);
    setError(null);
    setSelected(null);
    try {
      const res = await api.getProviderModels({
        provider,
        api_key: apiKey.trim() || undefined,
      });
      setModels(res.models);
    } catch (err) {
      setModels(null);
      setError(err instanceof Error ? err.message : 'Failed to load models');
    } finally {
      setLoading(false);
    }
  };

  // Free first, then available, then already-added at the bottom
  const visible = useMemo(() => {
    if (!models) return [];
    const q = filter.trim().toLowerCase();
    return models
      .filter((m) => m.id.toLowerCase().includes(q))
      .sort((a, b) => {
        if (a.already_added !== b.already_added) return a.already_added ? 1 : -1;
        if ((a.free === true) !== (b.free === true)) return a.free === true ? -1 : 1;
        return a.id.localeCompare(b.id);
      });
  }, [models, filter]);

  const handleAdd = async () => {
    if (!selected) return;
    setAdding(true);
    setError(null);
    try {
      await onAdd({
        provider,
        model: selected,
        apiKey: apiKey.trim() || undefined,
      });
      setApiKey('');
      await loadModels(); // refresh "already added" flags
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add model');
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Provider */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-zinc-500">PROVIDER</label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
        >
          <option value="" disabled>
            Select a provider
          </option>
          {providers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {/* Key + load */}
      {provider && (
        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-500">API KEY</label>
          <div className="flex gap-2">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Leave blank to reuse a saved key"
              className="flex-1 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-mono"
            />
            <button
              type="button"
              onClick={loadModels}
              disabled={loading}
              className="px-3 py-2 rounded-lg text-sm font-medium bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 disabled:opacity-60 flex items-center gap-2"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              Load models
            </button>
          </div>
          <p className="text-[10px] text-zinc-400">
            Stored locally. Only sent to the provider you selected.
          </p>
        </div>
      )}

      {error && (
        <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Live list */}
      {models && (
        <div className="space-y-2">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
            />
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder={`Search ${models.length} available models`}
              className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 pl-8 pr-3 py-2 text-sm"
            />
          </div>

          <div className="max-h-56 overflow-y-auto rounded-lg border border-zinc-200 dark:border-zinc-800 divide-y divide-zinc-100 dark:divide-zinc-800">
            {visible.length === 0 ? (
              <div className="px-3 py-4 text-xs text-zinc-500">No matching models.</div>
            ) : (
              visible.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  disabled={m.already_added}
                  onClick={() => setSelected(m.id)}
                  className={cn(
                    'w-full flex items-center justify-between gap-2 px-3 py-2 text-left text-sm',
                    m.already_added
                      ? 'opacity-50 cursor-not-allowed'
                      : 'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                    selected === m.id && 'bg-zinc-100 dark:bg-zinc-800'
                  )}
                >
                  <span className="font-mono text-xs truncate">{m.id}</span>
                  <span className="flex items-center gap-2 shrink-0">
                    {m.free === true && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                        Free
                      </span>
                    )}
                    {m.already_added && (
                      <span className="text-[10px] text-zinc-500">Added</span>
                    )}
                    {selected === m.id && <Check size={14} />}
                  </span>
                </button>
              ))
            )}
          </div>

          <button
            type="button"
            onClick={handleAdd}
            disabled={!selected || adding}
            className="w-full flex items-center justify-center gap-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {adding && <Loader2 size={14} className="animate-spin" />}
            Add selected model
          </button>
        </div>
      )}
    </div>
  );
};
