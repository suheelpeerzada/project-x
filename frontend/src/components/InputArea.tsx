import React, { useState, useRef, useEffect } from 'react';
import { SendHorizontal } from 'lucide-react';

interface InputAreaProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, disabled }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-6 pt-2">
      <div className="relative bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm transition-all duration-300 focus-within:border-zinc-300 dark:focus-within:border-zinc-700 focus-within:bg-zinc-50 dark:focus-within:bg-zinc-800/50">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={disabled}
          rows={1}
          className="w-full bg-transparent text-zinc-900 dark:text-zinc-200 placeholder:text-zinc-400 dark:placeholder:text-zinc-600 px-4 py-4 pr-12 rounded-xl resize-none focus:outline-none text-sm leading-relaxed max-h-[200px]"
          style={{ minHeight: '56px' }}
        />
        
        <div className="absolute bottom-3 right-3 flex items-center gap-2">
           <button 
             onClick={() => handleSubmit()}
             disabled={!input.trim() || disabled}
             className="p-2 bg-zinc-900 dark:bg-zinc-800 hover:bg-zinc-700 dark:hover:bg-zinc-700 text-zinc-50 dark:text-zinc-200 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-all"
           >
             <SendHorizontal size={18} />
           </button>
        </div>
      </div>
      <div className="text-center mt-3">
        <p className="text-[10px] text-zinc-400 dark:text-zinc-600 transition-colors duration-300">
          AI generated content may be inaccurate. Verify important information.
        </p>
      </div>
    </div>
  );
};
