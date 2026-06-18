import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { FaHeartbeat, FaExclamationTriangle, FaBolt, FaChartLine, FaExternalLinkAlt, FaServer, FaCogs, FaDownload, FaBug, FaNetworkWired, FaLock, FaGlobe } from "react-icons/fa"
import { fetchAlerts, fetchAlertStats, fetchSystemStatus, fetchAlertTrends, connectAlertStream, type Alert } from "@/lib/api"
import { Link } from "react-router-dom"

function severityColor(confidence: number) {
  if (confidence >= 0.90) return "text-red-400 border-red-400/30 bg-red-400/10"
  if (confidence >= 0.70) return "text-amber-400 border-amber-400/30 bg-amber-400/10"
  return "text-blue-400 border-blue-400/30 bg-blue-400/10"
}

function severityLabel(confidence: number) {
  if (confidence >= 0.90) return "Critical"
  if (confidence >= 0.70) return "High"
  return "Medium"
}

export default function Dashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [stats, setStats] = useState<Record<string, unknown>>({})
  const [systemStatus, setSystemStatus] = useState<Record<string, unknown>>({})
  const [chartData, setChartData] = useState<any[]>([])
  const [live, setLive] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const [alertRes, statsRes, sysRes, trendsRes] = await Promise.allSettled([
        fetchAlerts(5),
        fetchAlertStats(),
        fetchSystemStatus(),
        fetchAlertTrends(),
      ])
      if (alertRes.status === "fulfilled") setAlerts(alertRes.value.alerts)
      if (statsRes.status === "fulfilled") setStats(statsRes.value)
      if (sysRes.status === "fulfilled") setSystemStatus(sysRes.value)
      if (trendsRes.status === "fulfilled") setChartData(trendsRes.value)
    } catch {
      // Ignore
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  useEffect(() => {
    const ws = connectAlertStream((alert) => {
      setAlerts(prev => [alert, ...prev].slice(0, 10))
      setLive(true)
    })
    return () => { ws?.close() }
  }, [])

  const totalAlerts = (stats as { total_alerts?: number }).total_alerts ?? 0
  const avgConf = ((stats as { average_confidence?: number }).average_confidence ?? 0) * 100
  const confirmedAnchors = (stats as { confirmed_anchors?: number }).confirmed_anchors ?? 0

  const criticalCount = alerts.filter(a => a.confidence >= 0.90).length
  const warningCount = alerts.filter(a => a.confidence < 0.90).length

  const daemon = (systemStatus as { daemon?: { running?: boolean } }).daemon
  const captureState = daemon ? (daemon.running ? "running" : "stopped") : "unknown"

  return (
    <div className="space-y-6">
      {/* Top KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* System Status */}
        <Card className="glass-panel border-border relative overflow-hidden">
          <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl"></div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">System Status</CardTitle>
            <FaHeartbeat className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight capitalize">{captureState === "running" ? "Active" : captureState}</div>
            <div className="flex items-center gap-2 mt-3">
              <span className={`w-2 h-2 rounded-full ${captureState === "running" ? "bg-emerald-400" : "bg-red-400"}`}></span>
              <span className="text-xs text-muted-foreground">Packet Capture Daemon</span>
            </div>
            <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Anchored Blocks</span>
              <span className="font-mono text-sm font-medium">{confirmedAnchors}</span>
            </div>
          </CardContent>
        </Card>

        {/* ML Confidence */}
        <Card className="glass-panel border-border relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-2xl -mr-16 -mt-16"></div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Average ML Confidence</CardTitle>
            <FaBolt className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{avgConf.toFixed(1)}%</div>
            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-muted-foreground">Confidence Score</span>
              <Badge variant="outline" className={`text-[10px] ${avgConf >= 90 ? "text-emerald-400 border-emerald-400/30" : "text-amber-400 border-amber-400/30"}`}>
                {avgConf >= 90 ? "High" : avgConf >= 70 ? "Medium" : "Low"}
              </Badge>
            </div>
            <div className="w-full bg-secondary h-2 mt-2 rounded-full overflow-hidden">
              <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full transition-all duration-1000" style={{ width: `${avgConf}%` }}></div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">Overall detection reliability</p>
          </CardContent>
        </Card>

        {/* Active Alerts */}
        <Card className="glass-panel border-border relative overflow-hidden">
          <div className="absolute bottom-0 right-0 w-24 h-24 bg-red-500/10 rounded-full blur-2xl"></div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Alerts</CardTitle>
            <FaExclamationTriangle className="h-4 w-4 text-red-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{totalAlerts}</div>
            <div className="flex gap-3 mt-3">
              <div className="flex-1 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2 text-center">
                <div className="text-lg font-bold text-red-400">{criticalCount}</div>
                <div className="text-[10px] font-semibold text-red-400/70 uppercase tracking-wider">Critical</div>
              </div>
              <div className="flex-1 bg-amber-500/10 border border-amber-500/20 rounded-md px-3 py-2 text-center">
                <div className="text-lg font-bold text-amber-400">{warningCount}</div>
                <div className="text-[10px] font-semibold text-amber-400/70 uppercase tracking-wider">Warning</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chart + Blockchain Logs */}
      <div className="grid gap-4 lg:grid-cols-7">
        {/* 24h Attack Trends */}
        <Card className="lg:col-span-5 glass-panel border-border">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg text-foreground">24h Attack Trends</CardTitle>
              <CardDescription className="text-muted-foreground">Frequency of blocked intrusion attempts</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => alert("Date picker functionality coming soon!")}>Last 24 Hours</Button>
            </div>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorAttacks" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 28% 17%)" vertical={false} />
                <XAxis dataKey="time" stroke="hsl(215 20.2% 65.1%)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(215 20.2% 65.1%)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'hsl(215 28% 12%)', border: '1px solid hsl(215 28% 17%)', borderRadius: '8px', color: '#f8fafc' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area type="monotone" dataKey="attacks" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorAttacks)" dot={{ r: 3, fill: '#3b82f6', strokeWidth: 0 }} activeDot={{ r: 5, fill: '#ef4444', stroke: '#fff', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Verified Blockchain Logs */}
        <Card className="lg:col-span-2 glass-panel border-border">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400">✓</span>
              <CardTitle className="text-lg text-foreground">Verified Blockchain Logs</CardTitle>
            </div>
            <CardDescription className="text-muted-foreground">Immutable audit trail via Smart Contracts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0">
            {alerts.length === 0 ? (
              <div className="text-center text-muted-foreground py-8 text-sm">No verified logs yet.</div>
            ) : (
              alerts.slice(0, 5).map((alert, i) => (
              <div key={alert.alert_id} className="flex gap-3 py-3 border-b border-border last:border-0">
                <div className="flex flex-col items-center">
                  <div className={`w-2.5 h-2.5 rounded-full ${alert.confidence >= 0.90 ? 'bg-red-400' : alert.confidence >= 0.70 ? 'bg-amber-400' : 'bg-purple-400'} mt-1`}></div>
                  {i < Math.min(alerts.length, 5) - 1 && <div className="w-px flex-1 bg-border mt-1"></div>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    {alert.tx_hash ? (
                      <a href={`https://polygonscan.com/tx/${alert.tx_hash}`} target="_blank" rel="noreferrer" className="text-xs font-mono text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
                        {alert.tx_hash.substring(0, 16)}... <FaExternalLinkAlt className="h-2 w-2" />
                      </a>
                    ) : (
                      <span className="text-[11px] font-mono text-muted-foreground">Pending...</span>
                    )}
                    <span className="text-[10px] text-muted-foreground">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="text-sm font-medium">{alert.attack_type || 'Anomaly'} Detected</div>
                  <div className="text-[11px] font-mono text-muted-foreground mt-0.5 truncate">From: {alert.src_ip || 'Unknown'}</div>
                </div>
              </div>
            )))}
            <div className="pt-3">
              <Link to="/ledger" className="flex items-center justify-center gap-1 text-sm text-primary hover:underline font-medium">
                View All Transactions <FaExternalLinkAlt className="h-3 w-3" />
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Threat Feed */}
      <Card className="glass-panel border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg text-foreground">Active Threat Feed</CardTitle>
          <div className="flex items-center gap-2">
            {live && <span className="flex items-center gap-1 text-xs text-emerald-400"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>Live</span>}
            <Link to="/alerts">
              <Button variant="link" size="sm" className="text-primary">View All</Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs uppercase tracking-wider">Source IP</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Target</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Severity</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">ML Confidence</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    No active threats detected.
                  </TableCell>
                </TableRow>
              ) : (
                alerts.slice(0, 5).map((a) => (
                <TableRow key={a.alert_id}>
                  <TableCell className="font-mono text-sm">{a.src_ip}</TableCell>
                  <TableCell className="text-muted-foreground">{a.dst_ip}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={severityColor(a.confidence)}>
                      {severityLabel(a.confidence)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${a.confidence >= 0.90 ? "bg-red-500" : a.confidence >= 0.70 ? "bg-amber-500" : "bg-blue-500"}`} style={{ width: `${a.confidence * 100}%` }}></div>
                      </div>
                      <span className="text-xs text-muted-foreground font-mono">{Math.round(a.confidence * 100)}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" className="h-8 text-xs font-medium" onClick={() => alert("Action triggered for " + a.src_ip)}>Action</Button>
                  </TableCell>
                </TableRow>
              )))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
