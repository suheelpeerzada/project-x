import React from 'react';
import { cn } from '../lib/utils';
import { ContextStatus } from '../types';

interface StatusIndicatorProps {
  usage: number; // 0 to 100
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ usage }) => {
  let status: ContextStatus = 'safe';
  if (usage > 70) status = 'warning';
  if (usage > 90) status = 'critical';

  return (
    <div className="flex items-center gap-3 px-3 py-1.5 rounded-md bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 transition-colors duration-300">
      <div className="flex flex-col items-end">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">Ctx Load</span>
        <span className={cn("text-xs font-mono transition-colors", 
          status === 'safe' && "text-zinc-600 dark:text-zinc-400",
          status === 'warning' && "text-amber-600 dark:text-amber-400",
          status === 'critical' && "text-red-600 dark:text-red-400"
        )}>
          {usage}%
        </span>
      </div>
      <div className="h-2 w-2 rounded-full bg-zinc-200 dark:bg-zinc-800 relative overflow-hidden">
        <div 
          className={cn("absolute inset-0 rounded-full transition-colors duration-500",
            status === 'safe' && "bg-emerald-500/70",
            status === 'warning' && "bg-amber-500/70",
            status === 'critical' && "bg-red-500/70"
          )}
        />
      </div>
    </div>
  );
};
