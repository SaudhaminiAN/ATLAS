import type { Direction } from "../../types/api";

const styles: Record<Direction, string> = {
  BUY: "bg-buy/15 text-buy border-buy/30",
  SELL: "bg-sell/15 text-sell border-sell/30",
  WAIT: "bg-wait/15 text-wait border-wait/30",
};

export function DirectionBadge({ direction }: { direction: Direction }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-md border text-xs font-mono font-semibold tracking-wider ${styles[direction]}`}
    >
      {direction}
    </span>
  );
}
