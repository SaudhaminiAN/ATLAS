import { LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useAuth } from "../../context/AuthContext";
import { ApiClientError } from "../../lib/api";

export function LoginPage() {
  const { login, register, registrationEnabled } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : "Something went wrong. Please try again.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center px-4 bg-radial-gold">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-white">ATLAS</h1>
          <p className="mt-2 text-sm text-zinc-500">Sign in to access your trading dashboard</p>
        </div>

        <form
          onSubmit={(event) => void handleSubmit(event)}
          className="glass-panel rounded-2xl p-8 space-y-5 shadow-glow"
        >
          <div className="flex items-center gap-2 text-gold">
            <LogIn className="w-5 h-5" />
            <h2 className="font-display text-sm font-semibold tracking-[0.2em] uppercase">
              {mode === "login" ? "Sign in" : "Create account"}
            </h2>
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <label className="block space-y-1.5">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Email</span>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-lg border border-border bg-elevated px-3 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-gold/40"
              placeholder="you@example.com"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
              Password
            </span>
            <input
              type="password"
              required
              minLength={8}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-border bg-elevated px-3 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-gold/40"
              placeholder="At least 8 characters"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-gold px-4 py-2.5 text-sm font-semibold text-zinc-950 hover:bg-gold-glow transition disabled:opacity-50"
          >
            {submitting ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>

          {registrationEnabled && (
            <p className="text-center text-sm text-zinc-500">
              {mode === "login" ? (
                <>
                  No account?{" "}
                  <button
                    type="button"
                    className="text-gold hover:underline"
                    onClick={() => {
                      setMode("register");
                      setError(null);
                    }}
                  >
                    Register
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    className="text-gold hover:underline"
                    onClick={() => {
                      setMode("login");
                      setError(null);
                    }}
                  >
                    Sign in
                  </button>
                </>
              )}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
