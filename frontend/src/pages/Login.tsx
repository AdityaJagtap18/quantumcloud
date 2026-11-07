import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Input, Label } from "../components/ui/Input";
import { ErrorState } from "../components/States";

export function Login() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      navigate("/");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] text-[var(--text)]">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-8"
      >
        <h1 className="mb-1 text-base font-semibold text-[var(--text)]">QuantumCloud</h1>
        <p className="mb-6 text-sm text-[var(--text-secondary)]">
          {isRegister ? "Create an account to submit quantum jobs." : "Sign in to your account."}
        </p>

        <div className="mb-3">
          <Label>Email</Label>
          <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>

        <div className="mb-4">
          <Label>Password</Label>
          <Input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>

        {error && (
          <div className="mb-4">
            <ErrorState message={error} />
          </div>
        )}

        <Button type="submit" variant="primary" disabled={loading} className="w-full">
          {loading ? "Please wait..." : isRegister ? "Create account" : "Sign in"}
        </Button>

        <button
          type="button"
          onClick={() => setIsRegister((v) => !v)}
          className="mt-4 w-full text-center text-sm text-[var(--text-secondary)] hover:text-[var(--accent)]"
        >
          {isRegister ? "Already have an account? Sign in" : "No account yet? Register"}
        </button>
      </form>
    </div>
  );
}
