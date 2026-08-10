"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div 
        className="fixed top-4 z-50 w-16 h-8 bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-full opacity-50"
        style={{ right: "16px" }}
      />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="fixed top-4 z-50 flex items-center justify-between w-16 h-8 p-1 bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-full cursor-pointer relative transition-colors duration-300 focus:outline-none shadow-sm hover:shadow active:scale-95 hover:scale-102 transition-transform"
      style={{ right: "16px" }}
      aria-label="Toggle theme"
    >
      {/* Sliding indicator knob */}
      <div
        className={`absolute top-0.5 left-0.5 w-6.5 h-6.5 bg-white dark:bg-stone-900 rounded-full shadow-md transform transition-transform duration-300 flex items-center justify-center ${
          isDark ? "translate-x-8" : "translate-x-0"
        }`}
      >
        {isDark ? (
          <Moon className="w-3.5 h-3.5 text-indigo-400 fill-indigo-400" />
        ) : (
          <Sun className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
        )}
      </div>
      {/* Background Icons */}
      <div className="w-full flex justify-between px-1.5 pointer-events-none select-none">
        <Sun className="w-3.5 h-3.5 text-stone-400 dark:text-stone-500" />
        <Moon className="w-3.5 h-3.5 text-stone-400 dark:text-stone-500" />
      </div>
    </button>
  );
}
