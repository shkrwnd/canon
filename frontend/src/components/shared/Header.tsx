import React, { useState, useRef, useEffect, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  User,
  LogOut,
  Settings,
  Menu,
  X,
  Search,
  FileText,
  Clock,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useProjects } from "../../hooks/useProjects";
import { Project } from "../../types";
import { cn } from "../../utils/cn";
import { Input } from "../ui";

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, userEmail } = useAuth();
  const { data: projects } = useProjects();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const userMenuRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const userInitials = useMemo(() => {
    const email = userEmail ?? "";
    const parts = email.split("@")[0].split(".");
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return email ? email.substring(0, 2).toUpperCase() : "?";
  }, [userEmail]);

  const handleLogout = () => {
    logout();
    navigate("/login");
    setUserMenuOpen(false);
  };

  const isWorkspace = location.pathname === "/workspace";
  const isProfile = location.pathname === "/profile";

  const filteredProjects = useMemo(() => {
    if (!projects || !searchQuery.trim()) return [];
    const query = searchQuery.toLowerCase();
    return projects.filter(
      (project) =>
        project.name.toLowerCase().includes(query) ||
        project.description?.toLowerCase().includes(query)
    );
  }, [projects, searchQuery]);

  const recentProjects = useMemo(() => {
    if (!projects) return [];
    return [...projects]
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      .slice(0, 5);
  }, [projects]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setUserMenuOpen(false);
      }
      if (
        searchRef.current &&
        !searchRef.current.contains(event.target as Node)
      ) {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };

    if (userMenuOpen || searchOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [userMenuOpen, searchOpen]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        if ((event.metaKey || event.ctrlKey) && event.key === "k") {
          event.preventDefault();
          setSearchOpen(true);
          setTimeout(() => searchInputRef.current?.focus(), 0);
        }
        return;
      }

      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchInputRef.current?.focus(), 0);
      }
      if (event.key === "Escape" && searchOpen) {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [searchOpen]);

  useEffect(() => {
    if (searchOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 0);
    }
  }, [searchOpen]);

  const handleProjectSelect = (project: Project) => {
    setSearchOpen(false);
    setSearchQuery("");
    navigate("/workspace");
    setTimeout(() => {
      window.dispatchEvent(
        new CustomEvent("selectProject", {
          detail: { projectId: project.id },
        })
      );
    }, 100);
  };

  const highlightText = (text: string, query: string) => {
    if (!query.trim()) return text;
    const parts = text.split(new RegExp(`(${query})`, "gi"));
    return parts.map((part, i) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-blue-100 text-blue-900 px-0.5 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const navItems = [
    {
      path: "/workspace",
      label: "Workspace",
      icon: LayoutDashboard,
      isActive: isWorkspace,
    },
    {
      path: "/profile",
      label: "Profile",
      icon: User,
      isActive: isProfile,
    },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white">
      <div className="px-4 sm:px-6">
        <div className="flex h-12 items-center justify-between">
          {/* Logo */}
          <button
            onClick={() => navigate("/workspace")}
            className="flex items-center gap-2.5 group"
          >
            <div className="w-7 h-7 rounded-lg bg-blue-700 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-600 transition-colors shadow-sm">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 2h3.5v3.5H2V2zM6.5 2H10v3.5H6.5V2zM2 6.5h3.5V10H2V6.5zM6.5 6.5H10V10H6.5V6.5z" fill="white" fillOpacity="0.9"/>
              </svg>
            </div>
            <span className="text-sm font-bold text-slate-900 tracking-tight hidden sm:block">
              Canon
            </span>
          </button>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.path}
                  onClick={() => {
                    navigate(item.path);
                    setMobileMenuOpen(false);
                  }}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-all duration-150",
                    item.isActive
                      ? "text-blue-700 bg-blue-50 font-semibold"
                      : "text-slate-500 hover:text-slate-800 hover:bg-slate-50 font-medium"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Right: Search + User */}
          <div className="flex items-center gap-2">
            {/* Search */}
            <div className="relative" ref={searchRef}>
              <button
                onClick={() => {
                  setSearchOpen(!searchOpen);
                  if (!searchOpen) {
                    setTimeout(() => searchInputRef.current?.focus(), 0);
                  }
                }}
                className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 transition-all text-slate-500 text-sm"
                title="Search (⌘K)"
              >
                <Search className="w-3.5 h-3.5" />
                <span className="min-w-[120px] text-left text-slate-400">
                  Search...
                </span>
                <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs text-slate-400 bg-white border border-slate-200 rounded-md font-mono">
                  ⌘K
                </kbd>
              </button>

              <button
                onClick={() => {
                  setSearchOpen(!searchOpen);
                  if (!searchOpen) {
                    setTimeout(() => searchInputRef.current?.focus(), 0);
                  }
                }}
                className="md:hidden p-1.5 rounded-md hover:bg-slate-100 transition-colors text-slate-500"
                aria-label="Search"
              >
                <Search className="w-4 h-4" />
              </button>

              {/* Search dropdown */}
              {searchOpen && (
                <div className="absolute right-0 top-full mt-1.5 w-80 rounded-xl bg-white border border-slate-200 shadow-lg z-50 overflow-hidden animate-slide-down">
                  <div className="p-2 border-b border-slate-100">
                    <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                      <Input
                        ref={searchInputRef}
                        type="text"
                        placeholder="Search projects..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-8 pr-8 h-8 text-sm border-0 bg-slate-50 focus:bg-white"
                      />
                      {searchQuery && (
                        <button
                          onClick={() => setSearchQuery("")}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="max-h-72 overflow-y-auto">
                    {searchQuery.trim() === "" ? (
                      <div>
                        {recentProjects.length > 0 && (
                          <div className="py-1">
                            <div className="px-3 py-1.5 flex items-center gap-1.5">
                              <Clock className="w-3 h-3 text-slate-400" />
                              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Recent</span>
                            </div>
                            {recentProjects.map((project) => (
                              <button
                                key={project.id}
                                onClick={() => handleProjectSelect(project)}
                                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                              >
                                <FileText className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                                <span className="truncate">{project.name}</span>
                              </button>
                            ))}
                          </div>
                        )}
                        {recentProjects.length === 0 && (
                          <div className="px-3 py-6 text-center text-sm text-slate-400">
                            Type to search projects
                          </div>
                        )}
                      </div>
                    ) : filteredProjects.length === 0 ? (
                      <div className="px-3 py-6 text-center">
                        <p className="text-sm text-slate-500">No results for "{searchQuery}"</p>
                      </div>
                    ) : (
                      <div className="py-1">
                        {filteredProjects.map((project) => (
                          <button
                            key={project.id}
                            onClick={() => handleProjectSelect(project)}
                            className="w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-b-0"
                          >
                            <FileText className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-slate-800 truncate">
                                {highlightText(project.name, searchQuery)}
                              </p>
                              {project.description && (
                                <p className="text-xs text-slate-400 mt-0.5 truncate">
                                  {project.description}
                                </p>
                              )}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* User menu */}
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-blue-700 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-semibold text-white leading-none">
                    {userInitials}
                  </span>
                </div>
                <svg
                  className={cn(
                    "w-3 h-3 text-slate-400 transition-transform hidden md:block",
                    userMenuOpen && "rotate-180"
                  )}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-1.5 w-56 rounded-xl bg-white border border-slate-200 shadow-lg z-50 overflow-hidden animate-slide-down">
                  <div className="px-3.5 py-3 border-b border-slate-100">
                    <p className="text-xs font-bold text-slate-900">Account</p>
                    <p className="text-xs text-slate-400 mt-0.5 truncate">
                      {userEmail ?? "—"}
                    </p>
                  </div>

                  <div className="py-1.5 px-1.5">
                    <button
                      onClick={() => { navigate("/profile"); setUserMenuOpen(false); }}
                      className="w-full flex items-center gap-2.5 px-2.5 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 rounded-lg transition-colors"
                    >
                      <User className="w-3.5 h-3.5" />
                      Profile Settings
                    </button>
                    <button
                      onClick={() => { navigate("/profile"); setUserMenuOpen(false); }}
                      className="w-full flex items-center gap-2.5 px-2.5 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 rounded-lg transition-colors"
                    >
                      <Settings className="w-3.5 h-3.5" />
                      Settings
                    </button>
                    <div className="border-t border-slate-100 my-1.5" />
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-2.5 py-2 text-sm text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Mobile menu */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 rounded-md hover:bg-slate-100 transition-colors text-slate-500"
              aria-label="Menu"
            >
              {mobileMenuOpen ? (
                <X className="w-4 h-4" />
              ) : (
                <Menu className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-100 py-2">
            <nav className="flex flex-col gap-0.5">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.path}
                    onClick={() => {
                      navigate(item.path);
                      setMobileMenuOpen(false);
                    }}
                    className={cn(
                      "flex items-center gap-2.5 px-3 py-2 text-sm rounded-md transition-colors",
                      item.isActive
                        ? "bg-blue-50 text-blue-700 font-medium"
                        : "text-slate-600 hover:bg-slate-50"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </button>
                );
              })}
              <div className="border-t border-slate-100 my-1" />
              <button
                onClick={handleLogout}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-red-500 hover:bg-red-50 rounded-md transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};
