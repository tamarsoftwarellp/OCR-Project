import { NavLink, useNavigate } from "react-router-dom";
import { useState } from "react";
import {
  UploadCloud,
  ScanLine,
  FolderOpen,
  Stamp,
  Settings,
  LogOut,
} from "lucide-react";
import SettingsModal from "./SettingsModal.jsx";
import { useAuth } from "../context/AuthContext.jsx";

const NAV_ITEMS = [
  { to: "/", label: "Upload", index: "01", icon: UploadCloud, end: true },
  { to: "/status", label: "Processing", index: "02", icon: ScanLine },
  { to: "/claims", label: "Case Register", index: "03", icon: FolderOpen },
];

export default function Layout({ children }) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen paper-texture flex">
      {/* Sidebar */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-ink/10 bg-paper sticky top-0 h-screen overflow-y-auto scroll-thin">
        <div className="px-5 pt-7 pb-6 border-b border-ink/10">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full bg-ink text-paper flex items-center justify-center rotate-[-6deg] shadow-sm">
              <Stamp size={18} strokeWidth={2} />
            </div>
            <div>
              <p className="font-display text-lg leading-tight text-ink">
                {/* Claim&nbsp;OCR */}
                OCR
              </p>
              <p className="text-[10px] tracking-[0.18em] uppercase text-ink-soft font-mono">
                Review Desk
              </p>
            </div>
          </div>
        </div>

        <nav className="flex-1 py-6 flex flex-col gap-1.5 px-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2.5 tab-stub transition-colors ${
                  isActive
                    ? "bg-ink text-paper"
                    : "text-ink-soft hover:bg-folder/25 hover:text-ink"
                }`
              }
            >
              <span className="font-mono text-[10px] opacity-60 w-4">
                {item.index}
              </span>
              <item.icon size={16} strokeWidth={2} />
              <span className="text-sm font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-ink/10 space-y-3">
          {user && (
            <p
              className="text-xs text-ink-soft font-mono truncate"
              title={user.name || user.email}
            >
              {user.name || user.name || user.email}
            </p>
          )}
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex items-center gap-2 text-xs text-ink-soft hover:text-ink transition-colors font-mono"
          >
            <Settings size={14} />
            API endpoint
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs text-ink-soft hover:text-stamp-red transition-colors font-mono"
          >
            <LogOut size={14} />
            Log out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 inset-x-0 z-30 bg-ink text-paper flex items-center justify-between px-4 py-3 shadow-md">
        <div className="flex items-center gap-2">
          <Stamp size={18} />
          <span className="font-display text-base">Claim OCR</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setSettingsOpen(true)}>
            <Settings size={18} />
          </button>
          <button onClick={handleLogout}>
            <LogOut size={18} />
          </button>
        </div>
      </div>
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-ink text-paper flex justify-around py-2 shadow-[0_-2px_10px_rgba(0,0,0,0.15)]">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 px-3 py-1 text-[10px] ${
                isActive ? "text-folder" : "text-paper/60"
              }`
            }
          >
            <item.icon size={17} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <main className="flex-1 min-w-0 pt-14 pb-16 md:pt-0 md:pb-0">
        {children}
      </main>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
