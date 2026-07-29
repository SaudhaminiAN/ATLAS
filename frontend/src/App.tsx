import { Dashboard } from "./Dashboard";
import { LoginPage } from "./components/auth/LoginPage";
import { useAuth } from "./context/AuthContext";

export default function App() {
  const { status, authRequired } = useAuth();

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center">
        <p className="text-sm text-zinc-500 animate-pulse">Loading ATLAS…</p>
      </div>
    );
  }

  if (authRequired && status === "unauthenticated") {
    return <LoginPage />;
  }

  return <Dashboard />;
}
