import React from 'react';
import { Message } from '../types';
import { cn } from '../lib/utils';
import { Bot, User } from 'lucide-react';
import { Markdown } from './Markdown';

interface MessageBubbleProps {
  message: Message;
  /** True while this message is still receiving tokens */
  streaming?: boolean;
}

/* Three bouncing dots, shown before the first token arrives */
const ThinkingDots: React.FC = () => (
  <span className="flex items-center gap-1 py-1" aria-label="Thinking">
    {[0, 1, 2].map((i) => (
      <span
        key={i}
        className="h-1.5 w-1.5 rounded-full bg-zinc-400 dark:bg-zinc-500 animate-bounce"
        style={{ animationDelay: `${i * 150}ms` }}
      />
    ))}
  </span>
);

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  streaming = false,
}) => {
  const isUser = message.role === 'user';

  // Assistant bubble exists but no tokens have arrived yet (model is thinking)
  const isThinking = !isUser && message.content === '';

  return (
    <div className={cn("flex w-full mb-8", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("flex max-w-[85%] md:max-w-[75%] min-w-0 gap-4", isUser ? "flex-row-reverse" : "flex-row")}>
        
        {/* Avatar / Icon */}
        <div className={cn(
          "h-8 w-8 rounded flex items-center justify-center shrink-0 mt-1 transition-colors duration-300",
          isUser 
            ? "bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400" 
            : "bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-500"
        )}>
          {isUser ? <User size={16} /> : <Bot size={16} />}
        </div>

        {/* Content */}
        <div className={cn(
          "flex flex-col min-w-0",
          isUser ? "items-end" : "items-start"
        )}>
          <div className={cn(
            // w-fit: the bubble hugs its content and grows as text streams in
            "w-fit max-w-full px-5 py-3.5 rounded-2xl text-[0.93rem] leading-relaxed transition-colors duration-300",
            isUser 
              ? "whitespace-pre-wrap bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-200 rounded-tr-sm" 
              : cn(
                  "bg-zinc-100/80 dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800",
                  "text-zinc-800 dark:text-zinc-300 rounded-tl-sm min-w-0",
                  // no stray margin above the first / below the last block
                  "[&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
                  streaming && "border-zinc-300 dark:border-zinc-700"
                )
          )}>
            {isUser ? (
              message.content
            ) : isThinking ? (
              <ThinkingDots />
            ) : (
              <>
                <Markdown>{message.content}</Markdown>
                {streaming && (
                  <span className="inline-block h-4 w-1.5 -mb-0.5 rounded-sm bg-zinc-400 dark:bg-zinc-500 animate-pulse" />
                )}
              </>
            )}
          </div>
          <span className="text-[10px] text-zinc-400 dark:text-zinc-600 mt-1 px-1">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  );
};
