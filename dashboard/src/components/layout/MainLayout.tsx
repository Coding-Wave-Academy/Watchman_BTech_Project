import { Link, Outlet, useLocation } from "react-router-dom"
import { FaShieldAlt, FaTachometerAlt, FaExclamationTriangle, FaProjectDiagram, FaCube, FaCog, FaBell } from "react-icons/fa"

export default function MainLayout() {
  const location = useLocation()
  
  const navItems = [
    { name: "Dashboard", path: "/dashboard", icon: FaTachometerAlt },
    { name: "Security Alerts", path: "/alerts", icon: FaExclamationTriangle },
    { name: "Topology Map", path: "/topology", icon: FaProjectDiagram },
    { name: "Blockchain Ledger", path: "/ledger", icon: FaCube },
  ]

  return (
    <div className="flex h-screen bg-background overflow-hidden dark">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border">
          <img src="/watchman-logo-dark.png" alt="WatchMan Logo" className="h-8" />
          <span className="font-bold text-xl tracking-tight ml-3 text-white">WatchMan</span>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto">
          <div className="text-xs font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Navigation</div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = location.pathname.startsWith(item.path)
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    active 
                      ? "bg-primary/10 text-primary" 
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }`}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-16 border-b border-border bg-card/50 backdrop-blur-md flex items-center justify-between px-6 z-10">
          <div className="flex-1"></div>
          <div className="flex items-center space-x-4">
            <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-xs font-semibold border border-emerald-500/20">
              SYSTEM SECURE
            </span>
            <button className="p-2 text-muted-foreground hover:text-foreground rounded-full hover:bg-secondary transition-colors" onClick={() => alert("Notifications coming soon")}>
              <FaBell className="h-5 w-5" />
            </button>
            <button className="p-2 text-muted-foreground hover:text-foreground rounded-full hover:bg-secondary transition-colors" onClick={() => alert("Settings coming soon")}>
              <FaCog className="h-5 w-5" />
            </button>
            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-primary to-purple-500"></div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6 bg-background">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
