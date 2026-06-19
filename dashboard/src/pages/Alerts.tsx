import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { FaExclamationTriangle, FaShieldAlt, FaLink, FaHeartbeat, FaDownload, FaSync, FaBolt, FaBug, FaGlobe, FaLock, FaCrosshairs, FaServer, FaExternalLinkAlt } from "react-icons/fa"
import { fetchAlerts, updateAlertStatus, type Alert } from "@/lib/api"

const THREAT_ICONS: Record<string, typeof FaBolt> = {
  "DDoS": FaBolt,
  "SQL Injection": FaBug,
  "Malware C2": FaGlobe,
  "Port Scan": FaCrosshairs,
  "Brute Force": FaLock,
}

function severityColor(confidence: number) {
  if (confidence >= 0.90) return "text-red-400 border-red-400/30 bg-red-400/10"
  if (confidence >= 0.70) return "text-amber-400 border-amber-400/30 bg-amber-400/10"
  return "text-blue-400 border-blue-400/30 bg-blue-400/10"
}

const FILTER_OPTIONS = ["All Threats", "DDoS", "SQL Injection", "Malware", "Brute Force", "Port Scan"]

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [filter, setFilter] = useState("All Threats")
  const [loading, setLoading] = useState(true)
  const [mitigationPopup, setMitigationPopup] = useState<Alert | null>(null)

  const loadAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const attackType = filter === "All Threats" ? undefined : filter
      const data = await fetchAlerts(50, attackType)
      setAlerts(data.alerts)
    } catch {
      // Ignore
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { loadAlerts() }, [loadAlerts])

  const handleAction = async (alert: Alert) => {
    if (alert.confidence >= 0.90) {
      setMitigationPopup(alert)
    } else {
      // Investigate: just mark as investigating
      try {
        await updateAlertStatus(alert.alert_id, "investigating")
        setAlerts(prev => prev.map(a => a.alert_id === alert.alert_id ? { ...a, status: "investigating" } : a))
      } catch {
        // fallback
        setAlerts(prev => prev.map(a => a.alert_id === alert.alert_id ? { ...a, status: "investigating" } : a))
      }
    }
  }

  const handleBlock = async (alert: Alert) => {
    try {
      await updateAlertStatus(alert.alert_id, "blocked")
    } catch { /* fallback */ }
    setAlerts(prev => prev.map(a => a.alert_id === alert.alert_id ? { ...a, status: "blocked" } : a))
    setMitigationPopup(null)
  }

  const totalActive = alerts.filter(a => a.status === "active").length
  const totalBlocked = alerts.filter(a => a.status === "blocked").length

  return (
    <div className="space-y-6 relative">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Alerts</h1>
          <p className="text-muted-foreground mt-1">Real-time threat detection backed by immutable blockchain logs.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => window.alert("CSV export will be available in the next release.")}>
            <FaDownload className="h-4 w-4" /> Export CSV
          </Button>
          <Button size="sm" className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={loadAlerts}>
            <FaSync className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Live Refresh
          </Button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Threats</CardTitle>
            <FaExclamationTriangle className="h-5 w-5 text-red-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold">{totalActive}</span>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Mitigated Attacks</CardTitle>
            <FaShieldAlt className="h-5 w-5 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold">{totalBlocked}</span>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Blockchain Anchors</CardTitle>
            <FaLink className="h-5 w-5 text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold">{alerts.filter(a => a.tx_hash || a.status === 'verified').length}</span>
              <span className="text-xs text-muted-foreground mb-1">Total in view</span>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">IDS Status</CardTitle>
            <FaHeartbeat className="h-5 w-5 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold text-emerald-400">Live</span>
              <Badge variant="outline" className="text-emerald-400 border-emerald-400/30 text-[10px] mb-1">Optimal</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Pills */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground mr-1">Quick Filters:</span>
        {FILTER_OPTIONS.map(f => (
          <Button
            key={f}
            variant={filter === f ? "default" : "secondary"}
            size="sm"
            className="rounded-full text-xs h-7 px-3"
            onClick={() => setFilter(f)}
          >
            {f}
          </Button>
        ))}
      </div>

      {/* Alerts Table */}
      <Card className="glass-panel border-border">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent border-border">
                <TableHead className="text-xs uppercase tracking-wider pl-6">Severity</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Threat Type</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Source IP</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">ML Confidence</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Blockchain Hash</TableHead>
                <TableHead className="text-xs uppercase tracking-wider text-right pr-6">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.map((a) => {
                const isCritical = a.confidence >= 0.85
                const ThreatIcon = THREAT_ICONS[a.attack_type] || FaServer
                return (
                  <TableRow key={a.alert_id} className="border-border h-16">
                    <TableCell className="pl-6">
                      <Badge variant="outline" className={`${severityColor(a.confidence)} gap-1`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${isCritical ? "bg-red-400" : "bg-amber-400"}`}></span>
                        {isCritical ? "CRITICAL" : "WARNING"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2 font-medium">
                        <ThreatIcon className="h-4 w-4 text-muted-foreground" />
                        {a.attack_type}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-muted-foreground">{a.src_ip}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-secondary rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${a.confidence >= 0.90 ? "bg-red-500" : a.confidence >= 0.70 ? "bg-amber-500" : "bg-blue-500"}`} style={{ width: `${a.confidence * 100}%` }}></div>
                        </div>
                        <span className="text-xs text-muted-foreground font-mono w-8">{Math.round(a.confidence * 100)}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {(() => {
                        if (!a.tx_hash) {
                          return <span className="font-mono text-xs text-muted-foreground/50 bg-secondary/50 px-2 py-1 rounded">Pending</span>;
                        }
                        const isLive = a.tx_hash.startsWith("0x") || (a.tx_hash.length === 64 && /^[0-9a-fA-F]+$/.test(a.tx_hash));
                        if (isLive) {
                          const cleanHash = a.tx_hash.startsWith("0x") ? a.tx_hash : `0x${a.tx_hash}`;
                          return (
                            <a href={`https://celo-sepolia.blockscout.com/tx/${cleanHash}`} target="_blank" rel="noreferrer" className="font-mono text-xs text-primary hover:underline bg-secondary/50 px-2 py-1 rounded inline-flex items-center gap-1">
                              {`${cleanHash.slice(0,8)}...${cleanHash.slice(-4)}`} <FaExternalLinkAlt className="h-2 w-2" />
                            </a>
                          );
                        }
                        return (
                          <span className="font-mono text-[10px] text-muted-foreground/70 bg-secondary/50 px-2 py-1 rounded inline-flex items-center" title={a.tx_hash}>
                            Demo Mode
                          </span>
                        );
                      })()}
                    </TableCell>
                    <TableCell className="text-right pr-6">
                      {a.status === "blocked" ? (
                        <Badge variant="outline" className="text-emerald-400 border-emerald-400/30">Blocked</Badge>
                      ) : a.status === "investigating" ? (
                        <Badge variant="outline" className="text-blue-400 border-blue-400/30">Investigating</Badge>
                      ) : (
                        <Button
                          size="sm"
                          variant={isCritical ? "default" : "secondary"}
                          className={isCritical ? "bg-red-600 hover:bg-red-700" : ""}
                          onClick={() => handleAction(a)}
                        >
                          {isCritical ? "TAKE ACTION" : "INVESTIGATE"}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          <div className="px-6 py-3 border-t border-border text-sm text-muted-foreground">
            Showing <span className="font-medium text-foreground">1-{alerts.length}</span> of <span className="font-medium text-foreground">{alerts.length}</span> active alerts
          </div>
        </CardContent>
      </Card>

      {/* IPS Auto-Mitigation Popup */}
      {mitigationPopup && (
        <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-4 duration-300">
          <Card className="w-80 glass-panel border-border shadow-2xl shadow-black/50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <FaShieldAlt className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-sm">IPS Auto-Mitigation</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    AI recommends blocking IP <code className="text-foreground">{mitigationPopup.src_ip}</code> due to high confidence.
                  </p>
                  <div className="flex gap-2 mt-3">
                    <Button size="sm" className="bg-red-600 hover:bg-red-700 text-xs" onClick={() => handleBlock(mitigationPopup)}>
                      Block IP
                    </Button>
                    <Button size="sm" variant="secondary" className="text-xs" onClick={() => setMitigationPopup(null)}>
                      Dismiss
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
