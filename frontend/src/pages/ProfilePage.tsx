import React, { useMemo } from "react";
import { Header } from "../components/shared";
import { useAuth } from "../hooks/useAuth";
import { useProjects } from "../hooks/useProjects";
import {
  Mail,
  FolderOpen,
  FileText,
  Shield,
  KeyRound,
  Trash2,
  ChevronRight,
} from "lucide-react";

export const ProfilePage: React.FC = () => {
  const { userEmail, logout } = useAuth();
  const { data: projects } = useProjects();

  const userInitials = useMemo(() => {
    const email = userEmail ?? "";
    const parts = email.split("@")[0].split(".");
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return email ? email.substring(0, 2).toUpperCase() : "?";
  }, [userEmail]);

  const totalProjects = projects?.length ?? 0;
  const totalDocuments = projects?.reduce(
    (sum, p) => sum + (p.documents?.length ?? 0),
    0
  ) ?? 0;

  const stats = [
    { label: "Projects", value: totalProjects, icon: FolderOpen },
    { label: "Documents", value: totalDocuments, icon: FileText },
  ];

  const settingsItems = [
    {
      icon: KeyRound,
      title: "Change Password",
      desc: "Update your password to keep your account secure",
      disabled: true,
      badge: "Coming soon",
    },
    {
      icon: Shield,
      title: "Two-Factor Authentication",
      desc: "Add an extra layer of security to your account",
      disabled: true,
      badge: "Coming soon",
    },
  ];

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <Header />

      <div className="flex-1 overflow-auto">
        <div className="max-w-2xl mx-auto px-4 py-10 space-y-6">

          {/* Profile hero */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            {/* Banner */}
            <div className="h-24 bg-gradient-to-r from-blue-600 to-blue-500" />

            {/* Avatar + info */}
            <div className="px-6 pb-6">
              <div className="-mt-10 mb-4 flex items-end justify-between">
                <div className="w-20 h-20 rounded-2xl bg-blue-700 border-4 border-white flex items-center justify-center shadow-md">
                  <span className="text-2xl font-bold text-white">{userInitials}</span>
                </div>
              </div>

              <div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  {userEmail?.split("@")[0] ?? "User"}
                </h1>
                <p className="text-sm text-slate-500 mt-0.5">{userEmail}</p>
              </div>

              {/* Stats */}
              <div className="mt-5 grid grid-cols-2 gap-3">
                {stats.map(({ label, value, icon: Icon }) => (
                  <div
                    key={label}
                    className="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl border border-slate-100"
                  >
                    <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-xl font-bold text-slate-900 leading-none">{value}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Account information */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                Account Information
              </h2>
            </div>
            <div className="px-6 py-5">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                  <Mail className="w-4 h-4 text-slate-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-0.5">
                    Email Address
                  </p>
                  <p className="text-sm font-semibold text-slate-900 truncate">
                    {userEmail}
                  </p>
                </div>
                <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-full flex-shrink-0">
                  Read-only
                </span>
              </div>
            </div>
          </div>

          {/* Settings */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                Account Settings
              </h2>
            </div>
            <div className="divide-y divide-slate-100">
              {settingsItems.map(({ icon: Icon, title, desc, disabled, badge }) => (
                <div
                  key={title}
                  className={`flex items-center gap-4 px-6 py-4 ${
                    disabled ? "opacity-60" : "hover:bg-slate-50 cursor-pointer transition-colors"
                  }`}
                >
                  <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800">{title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                  </div>
                  {badge ? (
                    <span className="text-xs text-blue-600 bg-blue-50 border border-blue-100 px-2.5 py-1 rounded-full font-medium flex-shrink-0">
                      {badge}
                    </span>
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Danger zone */}
          <div className="bg-white rounded-2xl border border-red-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-red-100 bg-red-50/50">
              <h2 className="text-sm font-bold text-red-700 uppercase tracking-wider">
                Danger Zone
              </h2>
            </div>
            <div className="divide-y divide-red-100/60">
              <div className="flex items-center gap-4 px-6 py-4 hover:bg-red-50/40 cursor-pointer transition-colors group" onClick={logout}>
                <div className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-red-700">Sign Out</p>
                  <p className="text-xs text-red-400 mt-0.5">Sign out of your Canon account</p>
                </div>
                <ChevronRight className="w-4 h-4 text-red-300 flex-shrink-0 group-hover:text-red-400 transition-colors" />
              </div>

              <div className="flex items-center gap-4 px-6 py-4 opacity-60">
                <div className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0">
                  <Trash2 className="w-4 h-4 text-red-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-red-700">Delete Account</p>
                  <p className="text-xs text-red-400 mt-0.5">Permanently delete your account and all data</p>
                </div>
                <span className="text-xs text-red-500 bg-red-50 border border-red-100 px-2.5 py-1 rounded-full font-medium flex-shrink-0">
                  Coming soon
                </span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
