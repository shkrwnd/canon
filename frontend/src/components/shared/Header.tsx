import React, { useState, useRef, useEffect, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { 
  LayoutDashboard, 
  User, 
  LogOut, 
  Settings, 
  Menu,
  X,
  ChevronDown,
  Search,
  FileText,
  Clock,
  Sparkles,
  HelpCircle
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useProjects } from "../../hooks/useProjects";
import { useDocuments } from "../../hooks/useDocuments";
import { Project, Document } from "../../types";
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

  // Get user initials for avatar
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

  // Filter projects based on search query
  // Note: For now, we'll only search projects. Document search can be added later
  // when we have a better way to fetch all documents across projects
  const filteredProjects = useMemo(() => {
    if (!projects || !searchQuery.trim()) return [];
    const query = searchQuery.toLowerCase();
    return projects.filter((project) =>
      project.name.toLowerCase().includes(query) ||
      project.description?.toLowerCase().includes(query)
    );
  }, [projects, searchQuery]);

  // Get recent projects (last 5 accessed/modified)
  const recentProjects = useMemo(() => {
    if (!projects) return [];
    return [...projects]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 5);
  }, [projects]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
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

  // Keyboard shortcut for search (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
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

  // Focus input when search opens
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
      // Select the project
      window.dispatchEvent(new CustomEvent("selectProject", { 
        detail: { projectId: project.id } 
      }));
    }, 100);
  };

  // Highlight search query in text
  const highlightText = (text: string, query: string) => {
    if (!query.trim()) return text;
    const parts = text.split(new RegExp(`(${query})`, "gi"));
    return parts.map((part, i) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-yellow-200 text-gray-900 px-0.5 rounded">
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
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/95 backdrop-blur-md supports-[backdrop-filter]:bg-white/90 shadow-soft">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo and Brand */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/workspace")}
              className="flex items-center gap-2 hover:opacity-90 transition-all duration-200 group"
            >
              <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-blue-600 via-blue-600 to-blue-700 rounded-xl shadow-md group-hover:shadow-lg group-hover:scale-105 transition-all duration-200">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-xl font-bold text-gray-900 hidden sm:inline-block leading-tight">
                  Canon
                </span>
                <span className="text-xs text-gray-500 hidden lg:inline-block leading-tight">
                  Living Documents
                </span>
              </div>
            </button>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
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
                    "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 relative",
                    item.isActive
                      ? "bg-gradient-to-r from-blue-50 to-blue-100 text-blue-700 shadow-sm"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                  {item.isActive && (
                    <span className="absolute bottom-0 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-blue-600 rounded-full" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Side - Search and User Menu */}
          <div className="flex items-center gap-2">
            {/* Search Button */}
            <div className="relative" ref={searchRef}>
              <button
                onClick={() => {
                  setSearchOpen(!searchOpen);
                  if (!searchOpen) {
                    setTimeout(() => searchInputRef.current?.focus(), 0);
                  }
                }}
                className="hidden md:flex items-center gap-2 px-4 py-2.5 rounded-lg border-2 border-gray-200 bg-white hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 shadow-sm hover:shadow"
                title="Search projects and documents (⌘K)"
              >
                <Search className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-500 min-w-[140px] text-left">
                  {searchQuery || "Search projects..."}
                </span>
                <kbd className="hidden lg:inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-semibold text-gray-500 bg-gray-100 border border-gray-200 rounded">
                  <span className="text-xs">⌘</span>K
                </kbd>
              </button>

              {/* Mobile Search Button */}
              <button
                onClick={() => {
                  setSearchOpen(!searchOpen);
                  if (!searchOpen) {
                    setTimeout(() => searchInputRef.current?.focus(), 0);
                  }
                }}
                className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors relative"
                aria-label="Search"
              >
                <Search className="w-5 h-5 text-gray-700" />
                {searchOpen && (
                  <span className="absolute top-0 right-0 w-2 h-2 bg-blue-600 rounded-full" />
                )}
              </button>

              {/* Search Dropdown */}
              {searchOpen && (
                <div className="absolute right-0 top-full mt-2 w-96 max-w-[calc(100vw-2rem)] rounded-xl bg-white border-2 border-gray-200 shadow-large z-50 overflow-hidden animate-slide-down">
                  <div className="p-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 via-blue-50/50 to-white">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <Input
                        ref={searchInputRef}
                        type="text"
                        placeholder="Search projects and documents..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10 pr-10"
                      />
                      {searchQuery && (
                        <button
                          onClick={() => setSearchQuery("")}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                  
                  <div className="max-h-96 overflow-y-auto">
                    {searchQuery.trim() === "" ? (
                      <div>
                        {recentProjects.length > 0 && (
                          <div className="p-3 border-b border-gray-100 bg-gray-50">
                            <div className="flex items-center gap-2 text-xs font-medium text-gray-500 mb-2">
                              <Clock className="w-3.5 h-3.5" />
                              Recent Projects
                            </div>
                            <div className="space-y-1">
                              {recentProjects.map((project) => (
                                <button
                                  key={project.id}
                                  onClick={() => handleProjectSelect(project)}
                                  className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-gray-700 hover:bg-white rounded transition-colors"
                                >
                                  <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                  <span className="truncate">{project.name}</span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="p-4 text-center">
                          <Search className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                          <p className="text-sm text-gray-500">Start typing to search projects and documents...</p>
                          <p className="text-xs text-gray-400 mt-1">Press ⌘K to search anytime</p>
                        </div>
                      </div>
                    ) : filteredProjects.length === 0 ? (
                      <div className="p-8 text-center">
                        <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-sm font-medium text-gray-900 mb-1">No projects found</p>
                        <p className="text-xs text-gray-500">
                          No projects match "{searchQuery}"
                        </p>
                      </div>
                    ) : (
                      <div className="py-2">
                        <div className="px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b border-gray-100">
                          {filteredProjects.length} {filteredProjects.length === 1 ? "result" : "results"}
                        </div>
                        {filteredProjects.map((project) => (
                          <button
                            key={project.id}
                            onClick={() => handleProjectSelect(project)}
                            className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0 group"
                          >
                            <div className="flex-shrink-0 mt-0.5">
                              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-100 to-purple-200 flex items-center justify-center group-hover:from-purple-200 group-hover:to-purple-300 transition-colors">
                                <FileText className="w-5 h-5 text-purple-600" />
                              </div>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {highlightText(project.name, searchQuery)}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                                {project.description || "Project"}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {searchQuery.trim() !== "" && filteredProjects.length > 0 && (
                    <div className="p-2 border-t border-gray-200 bg-gray-50">
                      <p className="text-xs text-gray-500 text-center">
                        Press <kbd className="px-1.5 py-0.5 bg-white border border-gray-200 rounded text-xs">Enter</kbd> to select first result
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* User Dropdown */}
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 group"
              >
                <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-blue-500 via-blue-600 to-blue-700 rounded-full shadow-md group-hover:shadow-lg group-hover:scale-105 transition-all duration-200">
                  <span className="text-sm font-semibold text-white">
                    {userInitials}
                  </span>
                </div>
                <ChevronDown
                  className={cn(
                    "w-4 h-4 text-gray-600 transition-transform hidden md:block",
                    userMenuOpen && "rotate-180"
                  )}
                />
              </button>

              {/* Dropdown Menu */}
              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white border-2 border-gray-200 shadow-large z-50 overflow-hidden animate-slide-down">
                  <div className="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-blue-50 via-blue-50/50 to-white">
                    <p className="text-sm font-semibold text-gray-900">User Account</p>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{userEmail ?? "—"}</p>
                  </div>
                  
                  <div className="py-1">
                    <button
                      onClick={() => {
                        navigate("/profile");
                        setUserMenuOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      <User className="w-4 h-4" />
                      <span>Profile Settings</span>
                    </button>

                    <button
                      onClick={() => {
                        navigate("/profile");
                        setUserMenuOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      <Settings className="w-4 h-4" />
                      <span>Settings</span>
                    </button>

                    <div className="border-t border-gray-100 my-1" />

                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors relative"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 text-gray-700" />
              ) : (
                <Menu className="w-5 h-5 text-gray-700" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 py-4 bg-white">
            <nav className="flex flex-col gap-1">
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
                      "flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-all",
                      item.isActive
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-600 hover:bg-gray-100"
                    )}
                  >
                    <Icon className="w-5 h-5" />
                    {item.label}
                  </button>
                );
              })}
              <div className="border-t border-gray-200 my-2" />
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <LogOut className="w-5 h-5" />
                Logout
              </button>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};
