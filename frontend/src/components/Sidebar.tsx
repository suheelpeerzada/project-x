import React, { useState } from 'react';
import {
  Trash2,
  Settings,
  HardDrive,
  Cpu,
  Database,
  History,
  Box,
  Clock,
  Plus,
} from 'lucide-react';
import { cn } from '../lib/utils';

/* =========================
   Types
========================= */

export interface SidebarModel {
  id: string;
  name: string;
  meta?: {
    size?: string | null;
    quantization?: string | null;
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
  activeConversationId?: string | null;

  onRequestModelSelect: (id: string) => void;
  onDeleteModel?: (id: string) => void;
  onOpenSettings: () => void;
  onAddModel: () => void;

  onNewChat?: () => void;
  onSelectConversation?: (id: string) => void;
  onDeleteConversation?: (id: string) => void;
}

type Tab = 'models' | 'history';

/* =========================
   Helpers
========================= */

const DAY_MS = 24 * 60 * 60 * 1000;

/** Calendar-day label (not a rolling 24h window). */
const dayLabel = (iso: string): string => {
  const now = new Date();
  const startOfToday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate()
  ).getTime();
  const d = new Date(iso);
  const startOfThatDay = new Date(
    d.getFullYear(),
    d.getMonth(),
    d.getDate()
  ).getTime();
  const diffDays = Math.round((startOfToday - startOfThatDay) / DAY_MS);

  if (diffDays <= 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return 'Previous 7 Days';
  return 'Older';
};

/** Items arrive newest-first, so groups come out in display order. */
const groupHistory = (items: ChatHistoryItem[]) => {
  const groups: { label: string; items: ChatHistoryItem[] }[] = [];
  for (const item of items) {
    const label = dayLabel(item.timestamp);
    const last = groups[groups.length - 1];
    if (last && last.label === label) {
      last.items.push(item);
    } else {
      groups.push({ label, items: [item] });
    }
  }
  return groups;
};

/* =========================
   Component
========================= */

export const Sidebar: React.FC<SidebarProps> = ({
  models,
  activeModelId,
  history,
  activeConversationId = null,
  onRequestModelSelect,
  onDeleteModel,
  onOpenSettings,
  onAddModel,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('models');

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
            {/* Header */}
            <div className="px-4 py-4">
              <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                <HardDrive size={14} />
                <span className="text-[10px] font-semibold tracking-wider uppercase">
                  Local System
                </span>
              </div>
            </div>

            {/* Model list */}
            {models.length === 0 ? (
              <div className="px-5 py-6 text-sm text-zinc-500 dark:text-zinc-400">
                No models available
              </div>
            ) : (
              models.map((model) => (
                <div
                  key={model.id}
                  className={cn(
                    'group w-full px-5 py-3 flex flex-col gap-1 border-l-2 transition-colors cursor-pointer relative',
                    activeModelId === model.id
                      ? 'bg-zinc-200/50 dark:bg-zinc-900/50 border-zinc-400'
                      : 'border-transparent hover:bg-zinc-200/30 dark:hover:bg-zinc-900/30'
                  )}
                  onClick={() => onRequestModelSelect(model.id)}
                >
                  {/* Row: Name + Trash Icon */}
                  <div className="flex items-start justify-between">
                    {/* Model name */}
                    <div className="flex-1">
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
                    </div>

                    {/* Trash icon on hover */}
                    <button
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-zinc-500 hover:text-red-600 dark:hover:text-red-400 p-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Delete model "${model.name}"?`)) {
                          onDeleteModel?.(model.id);
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  {/* Metadata row (optional) */}
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
                </div>
              ))
            )}

            {/* -------- Add Model -------- */}
            <div className="px-5 py-3">
              <button
                onClick={onAddModel}
                className="w-full flex items-center gap-2 text-sm
                          text-zinc-500 hover:text-zinc-700
                          dark:text-zinc-400 dark:hover:text-zinc-300
                          px-3 py-2 rounded-md
                          border border-dashed
                          border-zinc-300 dark:border-zinc-700
                          hover:bg-zinc-100 dark:hover:bg-zinc-900"
              >
                <span className="text-lg leading-none">+</span>
                <span>Add model</span>
              </button>
            </div>
          </div>
        )}

        {/* -------- History -------- */}
        {activeTab === 'history' && (
          <div className="py-2">
            {/* New chat */}
            <div className="px-4 pt-2 pb-1">
              <button
                onClick={onNewChat}
                className="w-full flex items-center justify-center gap-2 text-sm font-medium
                          text-zinc-700 dark:text-zinc-300
                          px-3 py-2 rounded-md border
                          border-zinc-300 dark:border-zinc-700
                          hover:bg-zinc-100 dark:hover:bg-zinc-900"
              >
                <Plus size={16} />
                New chat
              </button>
            </div>

            {history.length === 0 ? (
              <div className="px-5 py-6 text-sm text-zinc-500 dark:text-zinc-400">
                No chat history yet
              </div>
            ) : (
              groupHistory(history).map((group) => (
                <div key={group.label}>
                  <div className="px-4 pt-4 pb-2">
                    <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400">
                      <Clock size={12} />
                      <span className="text-[10px] font-semibold tracking-wider uppercase">
                        {group.label}
                      </span>
                    </div>
                  </div>

                  {group.items.map((item) => (
                    <div
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => onSelectConversation?.(item.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') onSelectConversation?.(item.id);
                      }}
                      className={cn(
                        'group w-full text-left px-5 py-3 border-l-2 cursor-pointer transition-colors',
                        activeConversationId === item.id
                          ? 'bg-zinc-200/50 dark:bg-zinc-900/50 border-zinc-400'
                          : 'border-transparent hover:bg-zinc-200/30 dark:hover:bg-zinc-900/30'
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span
                          className={cn(
                            'text-sm font-medium truncate',
                            activeConversationId === item.id
                              ? 'text-zinc-900 dark:text-zinc-200'
                              : 'text-zinc-700 dark:text-zinc-300'
                          )}
                        >
                          {item.title}
                        </span>

                        <button
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-zinc-500 hover:text-red-600 dark:hover:text-red-400 p-0.5 shrink-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(`Delete chat "${item.title}"?`)) {
                              onDeleteConversation?.(item.id);
                            }
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>

                      {item.preview && (
                        <p className="text-[11px] text-zinc-500 truncate mt-0.5">
                          {item.preview}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
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
