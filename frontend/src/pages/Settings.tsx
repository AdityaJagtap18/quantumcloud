import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";

export function Settings() {
  const { email, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div>
      <PageHeader title="Settings" description="Account and appearance preferences." />

      <Card className="mb-4">
        <h2 className="mb-3 text-sm font-semibold text-[var(--text)]">Account</h2>
        <div className="flex items-center justify-between border-b border-[var(--border)] py-2.5">
          <span className="text-sm text-[var(--text-secondary)]">Email</span>
          <span className="font-mono-tech text-sm text-[var(--text)]">{email ?? "—"}</span>
        </div>
        <div className="flex items-center justify-between py-2.5">
          <span className="text-sm text-[var(--text-secondary)]">Session</span>
          <Button variant="destructive" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text)]">Appearance</h2>
        <div className="flex items-center justify-between">
          <span className="text-sm text-[var(--text-secondary)]">Theme</span>
          <Button size="sm" onClick={toggleTheme}>
            {theme === "light" ? "Switch to dark" : "Switch to light"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
