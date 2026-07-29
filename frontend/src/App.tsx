import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

interface HealthResponse {
  success: boolean;
  data: { status: string };
}

export default function App() {
  const [apiStatus, setApiStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    fetch(`${API_URL}/api/v1/health`)
      .then((res) => res.json())
      .then((body: HealthResponse) => {
        setApiStatus(body.success && body.data.status === "ok" ? "ok" : "error");
      })
      .catch(() => setApiStatus("error"));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="text-atlas-gold text-2xl font-bold tracking-wide">ATLAS</span>
          <span className="text-gray-500 text-sm">XAUUSD Analysis Platform</span>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center p-8">
        <div className="bg-atlas-panel rounded-xl p-8 max-w-lg w-full shadow-xl border border-gray-800">
          <h1 className="text-xl font-semibold mb-2">Project Setup Complete</h1>
          <p className="text-gray-400 mb-6">
            Foundation scaffold is running. Analysis modules will be added in subsequent specs.
          </p>

          <div className="space-y-3 text-sm">
            <StatusRow label="Frontend" status="ok" detail="React + TypeScript + Tailwind" />
            <StatusRow
              label="API"
              status={apiStatus}
              detail={
                apiStatus === "loading"
                  ? "Checking..."
                  : apiStatus === "ok"
                    ? "Connected to backend"
                    : "Backend unreachable"
              }
            />
            <StatusRow label="Instrument" status="ok" detail="XAUUSD (Gold)" />
            <StatusRow label="Default decision" status="ok" detail="WAIT" />
          </div>
        </div>
      </main>
    </div>
  );
}

function StatusRow({
  label,
  status,
  detail,
}: {
  label: string;
  status: "loading" | "ok" | "error";
  detail: string;
}) {
  const dot =
    status === "loading"
      ? "bg-yellow-500 animate-pulse"
      : status === "ok"
        ? "bg-green-500"
        : "bg-red-500";

  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        <span className="text-gray-300">{label}</span>
      </div>
      <span className="text-gray-500">{detail}</span>
    </div>
  );
}
