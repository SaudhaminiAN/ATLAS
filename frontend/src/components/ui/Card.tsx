import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, action, children, className = "" }: CardProps) {
  return (
    <section className={`glass-panel rounded-2xl overflow-hidden ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between px-5 py-3.5 border-b border-border/60">
          {title && (
            <h3 className="font-display text-xs font-semibold tracking-[0.2em] uppercase text-muted">
              {title}
            </h3>
          )}
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}
