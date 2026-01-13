import { useEffect, useRef, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { MessageBubble } from './components/MessageBubble';
import { InputArea } from './components/InputArea';
import { StatusIndicator } from './components/StatusIndicator';
import { ThemeToggle } from './components/ThemeToggle';
import { SetupScreen } from './components/SetupScreen';
import { SettingsModal } from './components/SettingsModal';
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
  name: string;
}

/* =========================
   App
========================= */

function App() {
  const {
    state,
    loading,
    setup,
    updateConfig,
    reset: resetConfig,
  } = useAppConfig();

  const models: Model[] = state?.model
  ? [
      {
        id: 'active',
        name: state.display_name ?? state.model,
      },
    ]
  : [];

  const [messages, setMessages] = useState<Message[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ✅ SINGLE SOURCE OF TRUTH
  const chatEnabled =
  state?.configured === true &&
  state?.auth_ok === true;

  const chatLocked = !chatEnabled;



  const contextLoad = 0;

  /* =========================
     Effects
  ========================= */

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);



  /* =========================
     Handlers
  ========================= */

  const handleSendMessage = async (content: string) => {
    if (!state?.model || !chatEnabled) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      const res = await api.chat({
        messages: [{ role: 'user', content }],
      });

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: res.content,
          timestamp: new Date(),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '⚠️ Chat disabled due to authentication error.',
          timestamp: new Date(),
        },
      ]);
    }
  };

  const handleRequestModelSelect = (modelId: string) => {
    // reserved for future backend support
    console.log('Requested model:', modelId);
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
        activeModelId="active"
        history={[]}
        onRequestModelSelect={handleRequestModelSelect}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onAddModel={() => setIsSettingsOpen(true)}   // ✅ for now
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
        <div className="flex-1 overflow-y-auto relative">
          <div
            className={cn(
              'max-w-4xl mx-auto px-6 py-8 transition-all',
              chatLocked && 'blur-md opacity-60 pointer-events-none select-none'
            )}
          >
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Lock Overlay */}
          {chatLocked && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="bg-white/90 dark:bg-zinc-900/90 backdrop-blur border rounded-xl px-6 py-5 shadow-xl text-center max-w-sm">
                <div className="text-3xl mb-3">🔒</div>
                <h3 className="text-sm font-semibold mb-1">Chat disabled</h3>
                <p className="text-xs text-zinc-500">
                  Chat is temporarily disable due to an authentication error. Try checking your API key.
                </p>
                <p className="text-[11px] mt-2 text-zinc-400">
                  Open <strong>Settings</strong> to update your API key.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="shrink-0 bg-white/95 dark:bg-zinc-950/95 pt-2">
          <InputArea
            onSendMessage={handleSendMessage}
            disabled={!chatEnabled}
          />
        </div>
      </main>

      {/* Settings */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentModelId={state.model}
        models={models}
        onSave={updateConfig}
        onReset={resetConfig}
      />
    </div>
  );
}

export default App;
