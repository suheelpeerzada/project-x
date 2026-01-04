import React from 'react';
import { Message } from '../types';
import { cn } from '../lib/utils';
import { Bot, User } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={cn("flex w-full mb-8", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("flex max-w-[85%] md:max-w-[75%] gap-4", isUser ? "flex-row-reverse" : "flex-row")}>
        
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
          "flex flex-col",
          isUser ? "items-end" : "items-start"
        )}>
          <div className={cn(
            "px-5 py-3.5 rounded-2xl text-[0.93rem] leading-relaxed whitespace-pre-wrap transition-colors duration-300",
            isUser 
              ? "bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-200 rounded-tr-sm" 
              : "bg-transparent text-zinc-800 dark:text-zinc-300 -ml-2"
          )}>
            {message.content}
          </div>
          <span className="text-[10px] text-zinc-400 dark:text-zinc-600 mt-1 px-1">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  );
};
