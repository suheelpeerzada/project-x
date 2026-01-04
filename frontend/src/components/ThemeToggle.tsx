import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import { cn } from '../lib/utils';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        "p-2 rounded-md transition-all duration-200 ease-in-out border",
        "hover:bg-zinc-200 dark:hover:bg-zinc-800",
        "border-transparent hover:border-zinc-300 dark:hover:border-zinc-700",
        "text-zinc-500 dark:text-zinc-400"
      )}
      aria-label="Toggle theme"
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'dark' ? (
        <Sun size={18} className="animate-in spin-in-90 duration-300" />
      ) : (
        <Moon size={18} className="animate-in spin-in-90 duration-300" />
      )}
    </button>
  );
};
