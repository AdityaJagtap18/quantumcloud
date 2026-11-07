import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutGrid,
  FlaskConical,
  ListChecks,
  Server,
  Workflow,
  Waves,
  BookOpen,
  FileText,
  Settings as SettingsIcon,
  Moon,
  Sun,
  LogOut,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutGrid },
  { to: "/circuit-lab", label: "Circuit Lab", icon: FlaskConical },
  { to: "/jobs", label: "Jobs", icon: ListChecks },
  { to: "/backends", label: "Backends", icon: Server },
  { to: "/compilation", label: "Compilation", icon: Workflow },
  { to: "/experiments", label: "Experiments", icon: Waves },
  { to: "/algorithms", label: "Algorithms", icon: BookOpen },
  { to: "/docs", label: "Documentation", icon: FileText },
];

export function Layout() {
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <aside className="flex w-56 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] px-3 py-4">
        <div className="mb-5 px-2 text-sm font-semibold text-[var(--text)]">QuantumCloud</div>
        <nav className="flex flex-1 flex-col gap-0.5">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-[var(--radius-md)] px-2.5 py-1.5 text-sm transition-colors ${
                  isActive
                    ? "bg-[var(--surface-secondary)] font-medium text-[var(--text)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text)]"
                }`
              }
            >
              <item.icon size={15} strokeWidth={1.75} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex flex-col gap-0.5 border-t border-[var(--border)] pt-2">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-[var(--radius-md)] px-2.5 py-1.5 text-sm transition-colors ${
                isActive
                  ? "bg-[var(--surface-secondary)] font-medium text-[var(--text)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text)]"
              }`
            }
          >
            <SettingsIcon size={15} strokeWidth={1.75} />
            Settings
          </NavLink>
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2.5 rounded-[var(--radius-md)] px-2.5 py-1.5 text-left text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text)]"
          >
            {theme === "light" ? <Moon size={15} strokeWidth={1.75} /> : <Sun size={15} strokeWidth={1.75} />}
            {theme === "light" ? "Dark mode" : "Light mode"}
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-2.5 rounded-[var(--radius-md)] px-2.5 py-1.5 text-left text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text)]"
          >
            <LogOut size={15} strokeWidth={1.75} />
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto px-8 py-6">
        <Outlet />
      </main>
    </div>
  );
}
