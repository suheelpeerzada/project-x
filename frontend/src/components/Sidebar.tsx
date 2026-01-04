import React, { useState } from 'react';
import {
  Settings,
  HardDrive,
  Cpu,
  Database,
  History,
  Box,
  Clock,
} from 'lucide-react';
import { cn } from '../lib/utils';

/* =========================
   Types
========================= */

export interface SidebarModel {
  id: string;
  name: string;
  meta?: {
    size?: string;
    quantization?: string;
  };
}

export interface ChatHistoryItem {
  id: string;
  title: string;
  preview?: string;
  timestamp: string; // ISO string
}

interface SidebarProps {
  models: SidebarModel[];
  activeModelId: string | null;
  history: ChatHistoryItem[];

  onRequestModelSelect: (id: string) => void;
  onOpenSettings: () => void;
}

type Tab = 'models' | 'history';

/* =========================
   Component
========================= */

export const Sidebar: React.FC<SidebarProps> = ({
  models,
  activeModelId,
  history,
  onRequestModelSelect,
  onOpenSettings,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('models');

  const formatDate = (date: Date) => {
    const now = new Date();
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return 'Previous 7 Days';
    return 'Older';
  };

  return (
    <aside className="w-64 bg-zinc-50 dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800 flex flex-col h-full shrink-0">
      
      {/* ================= Tabs ================= */}
      <div className="flex border-b border-zinc-200 dark:border-zinc-900 px-2 pt-2">
        <button
          onClick={() => setActiveTab('models')}
          className={cn(
            'flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium',
            activeTab === 'models'
              ? 'text-zinc-900 dark:text-zinc-200'
              : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-400'
          )}
        >
          <Box size={16} />
          Models
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={cn(
            'flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium',
            activeTab === 'history'
              ? 'text-zinc-900 dark:text-zinc-200'
              : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-400'
          )}
        >
          <History size={16} />
          History
        </button>
      </div>

      {/* ================= Content ================= */}
      <div className="flex-1 overflow-y-auto">

        {/* -------- Models -------- */}
        {activeTab === 'models' && (
          <div className="py-2">
            <div className="px-4 py-4">
              <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                <HardDrive size={14} />
                <span className="text-[10px] font-semibold tracking-wider uppercase">
                  Local System
                </span>
              </div>
            </div>

            {models.length === 0 ? (
              <div className="px-5 py-6 text-sm text-zinc-500 dark:text-zinc-400">
                No models available
              </div>
            ) : (
              models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => onRequestModelSelect(model.id)}
                  className={cn(
                    'w-full text-left px-5 py-3 flex flex-col gap-1 border-l-2 transition-colors',
                    activeModelId === model.id
                      ? 'bg-zinc-200/50 dark:bg-zinc-900/50 border-zinc-400'
                      : 'border-transparent hover:bg-zinc-200/30 dark:hover:bg-zinc-900/30'
                  )}
                >
                  <span
                    className={cn(
                      'text-sm font-medium',
                      activeModelId === model.id
                        ? 'text-zinc-900 dark:text-zinc-200'
                        : 'text-zinc-600 dark:text-zinc-400'
                    )}
                  >
                    {model.name}
                  </span>

                  {(model.meta?.size || model.meta?.quantization) && (
                    <div className="flex items-center gap-3 text-[10px] text-zinc-500 dark:text-zinc-600 font-mono">
                      {model.meta?.size && (
                        <span className="flex items-center gap-1">
                          <Database size={10} /> {model.meta.size}
                        </span>
                      )}
                      {model.meta?.quantization && (
                        <span className="flex items-center gap-1">
                          <Cpu size={10} /> {model.meta.quantization}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        )}

        {/* -------- History -------- */}
        {activeTab === 'history' && (
          <div className="py-2">
            <div className="px-4 py-4">
              <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                <Clock size={14} />
                <span className="text-[10px] font-semibold tracking-wider uppercase">
                  Recent Chats
                </span>
              </div>
            </div>

            {history.length === 0 ? (
              <div className="px-5 py-6 text-sm text-zinc-500 dark:text-zinc-400">
                No chat history yet
              </div>
            ) : (
              history.map((item) => (
                <button
                  key={item.id}
                  className="w-full text-left px-5 py-3 hover:bg-zinc-200/50 dark:hover:bg-zinc-900/30"
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300 truncate pr-2">
                      {item.title}
                    </span>
                    <span className="text-[10px] text-zinc-500">
                      {formatDate(new Date(item.timestamp))}
                    </span>
                  </div>

                  {item.preview && (
                    <p className="text-[11px] text-zinc-500 truncate">
                      {item.preview}
                    </p>
                  )}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* ================= Footer ================= */}
      <div className="p-4 border-t border-zinc-200 dark:border-zinc-900">
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-3 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 w-full px-2 py-2 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-900"
        >
          <Settings size={18} />
          <span className="text-sm">System Settings</span>
        </button>
      </div>
    </aside>
  );
};
