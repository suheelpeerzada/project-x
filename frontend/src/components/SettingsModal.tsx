import React, { useEffect, useState } from 'react';
import {
  X,
  Save,
  RotateCcw,
  Loader2,
  Settings,
  LayoutGrid,
} from 'lucide-react';
import { cn } from '../lib/utils';

/* =========================
   Types
========================= */

interface SettingsModel {
  id: string;
  name: string;
}

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;

  currentModelId: string | null;
  models: SettingsModel[];

  onSave: (payload: { model_id: string; api_key?: string }) => Promise<void>;
  onReset: () => Promise<void>;
}

type Tab = 'general' | 'models';

/* =========================
   Component
========================= */

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentModelId,
  models,
  onSave,
  onReset,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('general');

  const [modelId, setModelId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  /* =========================
     Effects
  ========================= */

  useEffect(() => {
    if (isOpen) {
      setModelId(currentModelId);
      setApiKey('');
      setShowResetConfirm(false);
      setActiveTab('general');
    }
  }, [isOpen, currentModelId]);

  if (!isOpen) return null;

  /* =========================
     Handlers
  ========================= */

  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modelId) return;

    setIsSaving(true);
    try {
      const payload: { model_id: string; api_key?: string } = {
        model_id: modelId,
      };
      
      if (apiKey.trim()) {
        payload.api_key = apiKey.trim();
      }
      
      await onSave(payload);
      
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await onReset();
      onClose();
    } finally {
      setIsResetting(false);
    }
  };

  /* =========================
     Render
  ========================= */

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/20 dark:bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 shrink-0">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            System Configuration
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Tabs */}
          <div className="w-48 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/30 p-3 space-y-1">
            <button
              onClick={() => setActiveTab('general')}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md',
                activeTab === 'general'
                  ? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                  : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-900'
              )}
            >
              <Settings size={16} />
              General
            </button>

            <button
              onClick={() => setActiveTab('models')}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md',
                activeTab === 'models'
                  ? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                  : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-900'
              )}
            >
              <LayoutGrid size={16} />
              Models
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'general' && (
              <form
                onSubmit={handleSaveGeneral}
                className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300"
              >
                <div className="space-y-4">
                  {/* Active Model */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                      Active Model
                    </label>

                    {models.length === 0 ? (
                      <div className="text-sm text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg px-3 py-2">
                        No models available.
                      </div>
                    ) : (
                      <select
                        value={modelId ?? ''}
                        onChange={(e) => setModelId(e.target.value)}
                        className="w-full bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-500/20 focus:border-zinc-500 dark:text-zinc-200"
                        required
                      >
                        <option value="" disabled>
                          Select a model
                        </option>
                        {models.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name}
                          </option>
                        ))}
                      </select>
                    )}

                    <p className="text-[11px] text-zinc-500">
                      Select which model is active for new chats.
                    </p>
                  </div>

                  {/* API Key */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                      Update API Key
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Leave blank to keep current key"
                      className="w-full bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-500/20 focus:border-zinc-500 dark:text-zinc-200 font-mono"
                    />
                  </div>
                </div>

                <div className="pt-6 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                  {!showResetConfirm ? (
                    <button
                      type="button"
                      onClick={() => setShowResetConfirm(true)}
                      className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
                    >
                      <RotateCcw size={16} />
                      Reset Config
                    </button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-zinc-500 font-medium">
                        Are you sure?
                      </span>
                      <button
                        type="button"
                        onClick={handleReset}
                        disabled={isResetting}
                        className="text-xs bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-md flex items-center gap-1"
                      >
                        {isResetting && (
                          <Loader2 size={12} className="animate-spin" />
                        )}
                        Confirm
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowResetConfirm(false)}
                        className="text-xs text-zinc-500 hover:text-zinc-700 px-2"
                      >
                        Cancel
                      </button>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSaving || !modelId}
                    className="bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors flex items-center gap-2 disabled:opacity-70"
                  >
                    {isSaving ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Save size={16} />
                    )}
                    Save Changes
                  </button>
                </div>
              </form>
            )}

            {activeTab === 'models' && (
              <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-200">
                  Model Management
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  Model registry management will be available in a future update.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
