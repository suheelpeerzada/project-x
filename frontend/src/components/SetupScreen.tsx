import React, { useState, useEffect } from 'react';
import { ShieldCheck, Key, ArrowRight, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';

/* =========================
   Types
========================= */

interface SetupModel {
  id: string;
  name: string;
  meta?: {
    size?: string;
  };
}

interface Model {
  id: string;
  name: string;
}


interface Provider {
  id: string;
  name: string;
}

/* =========================
   Component
========================= */

export const SetupScreen: React.FC= () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [modelsLoading, setModelsLoading] = useState(false);
  const CUSTOM = 'custom-openai';
  const MANUAL = '__manual__';
  const API_KEY_REQUIRED_PROVIDERS = ['groq', 'openai'];
  const [manualModel, setManualModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [savingConfig, setSavingConfig] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  const isCustom = selectedProvider === CUSTOM;
  const modelToUse =
    isCustom || selectedModel === MANUAL ? manualModel.trim() : (selectedModel ?? '');
  const canFinish =
    !!selectedProvider &&
    !!modelToUse &&
    (!isCustom || !!baseUrl.trim()) &&
    (isCustom || !API_KEY_REQUIRED_PROVIDERS.includes(selectedProvider) || !!apiKey);



  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // F1 ends here — model selection comes next
  };
  

  useEffect(() => {
    fetch('http://127.0.0.1:8000/providers')
      .then(res => res.json())
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  useEffect(() => {
    setManualModel('');
    setBaseUrl('');
    if (!selectedProvider) {
      setModels([]);
      setSelectedModel(null);
      return;
    }
  
    setModelsLoading(true);
  
    fetch(`http://127.0.0.1:8000/models?provider=${selectedProvider}`)
      .then(res => res.json())
      .then((data: Model[]) => {
        setModels(data);
        setSelectedModel(null); // reset when provider changes
      })
      .catch(() => {
        setModels([]);
        setSelectedModel(null);
      })
      .finally(() => setModelsLoading(false));
  }, [selectedProvider]);
  

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4 transition-colors duration-300">
      <div className="w-full max-w-md animate-in fade-in zoom-in-95 duration-500">
        
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900 mb-4 shadow-lg shadow-zinc-200 dark:shadow-zinc-900/50">
            <ShieldCheck size={24} />
          </div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Welcome to Project-X
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-2 text-sm">
            Secure, local-first AI environment setup.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xl shadow-zinc-200/50 dark:shadow-black/20 overflow-hidden">
          <div className="p-6 md:p-8 space-y-6">
            {/* Provider Selection */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-zinc-500">
                  PROVIDER
                </label>

                <select
                  value={selectedProvider ?? ''}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800
                            bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
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

              {/* Model Selection */}
              {isCustom ? (
                <div className="space-y-3">
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-zinc-500">
                      BASE URL
                    </label>
                    <input
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      placeholder="https://router.huggingface.co/v1"
                      className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800
                                bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-mono"
                    />
                    <p className="text-[10px] text-zinc-400">
                      Any OpenAI-compatible server: Hugging Face router, DeepSeek,
                      OpenRouter, Ollama (http://localhost:11434/v1), LM Studio…
                    </p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-zinc-500">
                      MODEL ID
                    </label>
                    <input
                      value={manualModel}
                      onChange={(e) => setManualModel(e.target.value)}
                      placeholder="e.g. openai/gpt-oss-120b"
                      className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800
                                bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-mono"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-500">
                    MODEL
                  </label>

                  <select
                    value={selectedModel ?? ''}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={!selectedProvider || modelsLoading}
                    className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800
                              bg-white dark:bg-zinc-900 px-3 py-2 text-sm
                              disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option value="" disabled>
                      {modelsLoading ? 'Loading models...' : 'Select a model'}
                    </option>

                    {models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}

                    {selectedProvider && !modelsLoading && (
                      <option value={MANUAL}>Other (type a model ID)…</option>
                    )}
                  </select>

                  {selectedModel === MANUAL && (
                    <input
                      value={manualModel}
                      onChange={(e) => setManualModel(e.target.value)}
                      placeholder="Exact model ID, e.g. llama-3.3-70b-versatile"
                      className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800
                                bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-mono"
                    />
                  )}
                </div>
              )}
              {selectedProvider &&
                (isCustom || API_KEY_REQUIRED_PROVIDERS.includes(selectedProvider)) && (
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-zinc-500">
                      {isCustom ? 'API KEY (OPTIONAL FOR LOCAL SERVERS)' : 'API KEY'}
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="sk-..."
                      className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800
                                bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
                    />
                    <p className="text-[10px] text-zinc-400">
                      Stored locally. Never sent anywhere else.
                    </p>
                  </div>
              )}
              {setupError && (
                <p className="text-xs text-red-500">{setupError}</p>
              )}
              <button
                type="button"
                disabled={!canFinish || savingConfig}
                onClick={async () => {
                  setSavingConfig(true);
                  setSetupError(null);
                  try {
                    const res = await fetch('http://127.0.0.1:8000/config/setup', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        provider: selectedProvider,
                        model_id: modelToUse,
                        api_key: apiKey,
                        base_url: isCustom ? baseUrl.trim() : undefined,
                      }),
                    });
                    if (!res.ok) {
                      let detail = await res.text();
                      try {
                        const j = JSON.parse(detail);
                        detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j);
                      } catch { /* keep raw text */ }
                      setSetupError(`Setup failed (${res.status}): ${detail}`);
                      return;
                    }
                    window.location.reload();
                  } catch {
                    setSetupError('Could not reach the backend. Is it running?');
                  } finally {
                    setSavingConfig(false);
                  }
                }}
                className={cn(
                  "w-full flex items-center justify-center gap-2 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 py-3 rounded-lg font-medium text-sm transition-all duration-200",
                  "hover:bg-zinc-800 dark:hover:bg-zinc-200 hover:shadow-lg",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                {savingConfig ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Saving configuration…
                  </>
                ) : (
                  <>
                    Finish setup
                    <ArrowRight size={16} />
                  </>
                )}
              </button>

          </div>

          {/* Footer */}
          <div className="bg-zinc-50 dark:bg-zinc-950/50 px-6 py-4 border-t border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center justify-center gap-2 text-[10px] text-zinc-400 dark:text-zinc-500">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Secure Connection Ready
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
