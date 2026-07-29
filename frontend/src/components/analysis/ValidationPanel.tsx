import { Check, X } from "lucide-react";
import type { ValidationResult } from "../../types/api";
import { Card } from "../ui/Card";

export function ValidationPanel({ data, bare }: { data: ValidationResult | null; bare?: boolean }) {
  if (!data) {
    return <p className="text-sm text-zinc-500 p-4">No validation data yet</p>;
  }

  const passed = data.rules.filter((r) => r.enabled && r.passed).length;
  const enabled = data.rules.filter((r) => r.enabled).length;

  const body = (
    <>
      <p className="text-xs text-zinc-500 mb-4">
        Safety checks before any trade. All must pass for a BUY/SELL signal.
      </p>
      <p className="text-sm font-mono mb-4">
        <span className={data.is_valid ? "text-emerald-400" : "text-red-400"}>
          {passed}/{enabled} rules passed
        </span>
      </p>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {data.rules
          .filter((r) => r.enabled)
          .map((rule) => (
            <div key={rule.rule_name} className="flex items-center gap-2 py-2 px-2 rounded-lg">
              {rule.passed ? (
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <X className="w-4 h-4 text-red-400 shrink-0" />
              )}
              <span className="text-sm text-zinc-300 flex-1">
                {rule.rule_name.replace(/_/g, " ")}
              </span>
            </div>
          ))}
      </div>
    </>
  );

  if (bare) return <div className="p-4">{body}</div>;

  return <Card title="Validation">{body}</Card>;
}
