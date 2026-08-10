"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button
        size="icon"
        variant="outline"
        className="fixed bottom-5 z-50 h-11 w-11 rounded-full shadow-lg bg-white border border-stone-200 text-stone-700 opacity-0"
        style={{ right: "76px" }}
      />
    );
  }

  return (
    <Button
      size="icon"
      variant="outline"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="fixed bottom-5 z-50 h-11 w-11 rounded-full shadow-lg bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-850 transition-all hover:scale-105 active:scale-95"
      style={{ right: "76px" }}
      aria-label="Toggle theme"
    >
      {theme === "dark" ? (
        <Sun className="h-5 w-5 text-amber-500 animate-spin-once" />
      ) : (
        <Moon className="h-5 w-5 text-indigo-500" />
      )}
    </Button>
  );
}
