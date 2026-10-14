import { useEffect, useRef, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { MessageBubble } from './components/MessageBubble';
import { InputArea } from './components/InputArea';
import { StatusIndicator } from './components/StatusIndicator';
import { ThemeToggle } from './components/ThemeToggle';
import { SetupScreen } from './components/SetupScreen';
import { SettingsModal } from './components/SettingsModal';
import type { AddModelPayload } from './components/ModelPicker';
import type { ChatHistoryItem } from './components/Sidebar';
import { useAppConfig } from './hooks/useAppConfig';
import { Message } from './types';
import { Terminal, Loader2 } from 'lucide-react';
import { api } from './services/api';
import { cn } from './lib/utils';

/* =========================
   Types
========================= */

interface Model {
  id: string;
  provider: string;
  model: string;
  name: string;
  meta?: {
    size?: string | null;
    quantization?: string | null;
  };
  is_active: boolean;
}

/* =========================
   App
========================= */

function App() {
  const {
    state,
    loading,
    updateConfig,
    reset: resetConfig,
    refresh,
  } = useAppConfig();

  // List of models from backend
  const [models, setModels] = useState<Model[]>([]);
  const [activeModelId, setActiveModelId] = useState<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<'general' | 'models'>('general');

  // Chat history: the id is internal plumbing, the user never sees it
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Only auto-follow new text while the reader is at (or near) the bottom
  const stickToBottom = useRef(true);
  const [isStreaming, setIsStreaming] = useState(false);

  // ✅ SINGLE SOURCE OF TRUTH: the backend decides (/status → chat_enabled)
  const chatEnabled = state?.chat_enabled === true;
  const chatLocked = !chatEnabled;

  // Why is chat locked? Shown in the overlay instead of a generic message.
  const lockReason =
    state?.last_error?.message ??
    (state?.auth_ok === false
      ? 'The provider rejected your API key. Update it in Settings.'
      : state?.auth_ok === null
      ? 'Your API key has not been verified yet. Open Settings to verify it.'
      : 'Chat is unavailable.');

  const contextLoad = 0;

  /* =========================
     Effects
  ========================= */

  // Follow the stream only if the user hasn't scrolled up to read
  useEffect(() => {
    if (stickToBottom.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
    }
  }, [messages]);

  useEffect(() => {
    if (!state?.configured) return;

    api.getConfigModels().then((list) => {
      setModels(list);
      const active = list.find((m) => m.is_active);
      setActiveModelId(active ? active.id : null);
    }).catch(() => {
      /* keep the previous list if the backend is briefly unreachable */
    });
  }, [state]);

  /* =========================
     Handlers
  ========================= */

  const loadHistory = async () => {
    try {
      setHistory(await api.getHistory());
    } catch {
      /* history is optional; chat keeps working without it */
    }
  };

  useEffect(() => {
    if (state?.configured) loadHistory();
  }, [state?.configured]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    stickToBottom.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  const handleNewChat = () => {
    if (isStreaming) return;
    setConversationId(null);
    setMessages([]);
    stickToBottom.current = true;
  };

  const handleOpenConversation = async (id: string) => {
    if (isStreaming || id === conversationId) return;
    try {
      const conv = await api.getConversation(id);
      setConversationId(conv.id);
      setMessages(
        conv.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: new Date(m.timestamp),
        }))
      );
      stickToBottom.current = true;
    } catch {
      await loadHistory(); // it may have been deleted
    }
  };

  const handleDeleteConversation = async (id: string) => {
    if (isStreaming) return;
    await api.deleteConversation(id);
    if (id === conversationId) {
      setConversationId(null);
      setMessages([]);
    }
    await loadHistory();
  };

  const handleSendMessage = async (content: string) => {
    if (!state?.model || !chatEnabled || isStreaming) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    const assistantId = crypto.randomUUID();

    stickToBottom.current = true;
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: 'assistant', content: '', timestamp: new Date() },
    ]);
    setIsStreaming(true);

    const append = (text: string) =>
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: m.content + text } : m
        )
      );

    try {
      // Only the new message is sent. With a conversation id the backend
      // rebuilds the context from its own saved history.
      await api.chatStream(
        {
          messages: [{ role: 'user', content }],
          conversation_id: conversationId,
        },
        append,
        { onConversation: setConversationId }
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      if (msg === 'Conversation not found') setConversationId(null);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content ? `${m.content}\n\n⚠️ ${msg}` : `⚠️ ${msg}` }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
      loadHistory();
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    await api.deleteModel({ model_id: modelId });

    const list = await api.getConfigModels();
    setModels(list);

    const active = list.find((m) => m.is_active);
    setActiveModelId(active ? active.id : null);
  };

  const reloadModels = async () => {
    const list = await api.getConfigModels();
    setModels(list);
    const active = list.find((m) => m.is_active);
    setActiveModelId(active ? active.id : null);
  };

  // Switch active model, then verify it (auth_ok is tracked per model)
  const handleSwitchModel = async (modelId: string) => {
    if (modelId === activeModelId) return;

    await api.switchModel({ model_id: modelId });
    try {
      await api.verifyConfig();
    } catch {
      // 401 → backend recorded it; state is re-pulled below
    }
    await refresh();
    await reloadModels();
  };

  // Add a model chosen in the live picker (does not change the active model)
  const handleAddModel = async (payload: AddModelPayload) => {
    await api.addModel({
      provider: payload.provider,
      model: payload.model,
      api_key: payload.apiKey,
      base_url: payload.baseUrl,
    });
    await reloadModels();
  };

  const openSettings = (tab: 'general' | 'models') => {
    setSettingsTab(tab);
    setIsSettingsOpen(true);
  };

  /* =========================
     Render Gates
  ========================= */

  // Backend loading
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  // First-time setup
  if (!state?.configured) {
    return <SetupScreen />;
  }

  /* =========================
     Main UI
  ========================= */

  return (
    <div className="flex h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-200 overflow-hidden">
      {/* Sidebar */}
      <div className="hidden md:block h-full">
        <Sidebar
          models={models}
          activeModelId={activeModelId}
          history={history}
          activeConversationId={conversationId}
          onNewChat={handleNewChat}
          onSelectConversation={handleOpenConversation}
          onDeleteConversation={handleDeleteConversation}
          onRequestModelSelect={handleSwitchModel}
          onDeleteModel={handleDeleteModel}
          onOpenSettings={() => openSettings('general')}
          onAddModel={() => openSettings('models')}
        />
      </div>

      {/* Main */}
      <main className="flex-1 flex flex-col h-full relative min-w-0">
        {/* Top Bar */}
        <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 flex items-center justify-between px-6 bg-white/80 dark:bg-zinc-950/80 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-zinc-100 dark:bg-zinc-900 rounded flex items-center justify-center border">
              <Terminal size={16} />
            </div>
            <div>
              <h1 className="text-sm font-semibold">
                {state.display_name ?? 'No model selected'}
              </h1>
              <span className="text-[10px] text-zinc-500 font-mono">
                v0.9.2-alpha
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <StatusIndicator usage={contextLoad} />
            <ThemeToggle />
          </div>
        </header>

        {/* Chat */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto relative"
        >
          <div
            className={cn(
              'max-w-4xl mx-auto px-6 py-8 transition-all',
              chatLocked && 'blur-md opacity-60 pointer-events-none select-none'
            )}
          >
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                streaming={
                  isStreaming && msg.id === messages[messages.length - 1]?.id
                }
              />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Lock Overlay */}
          {chatLocked && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="bg-white/90 dark:bg-zinc-900/90 backdrop-blur border rounded-xl px-6 py-5 shadow-xl text-center max-w-sm">
                <div className="text-3xl mb-3">🔒</div>
                <h3 className="text-sm font-semibold mb-1">Chat disabled</h3>
                <p className="text-xs text-zinc-500">{lockReason}</p>
                <p className="text-[11px] mt-2 text-zinc-400">
                  Open <strong>Settings</strong> to fix this.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="shrink-0 bg-white/95 dark:bg-zinc-950/95 pt-2">
          <InputArea
            onSendMessage={handleSendMessage}
            disabled={!chatEnabled || isStreaming}
          />
        </div>
      </main>

      {/* Settings */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        initialTab={settingsTab}
        currentModelId={activeModelId}
        models={models}
        onSave={updateConfig}
        onReset={resetConfig}
        onSwitchModel={handleSwitchModel}
        onAddModel={handleAddModel}
      />
    </div>
  );
}

export default App;
