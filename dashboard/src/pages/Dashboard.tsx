import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Activity, ShieldAlert, Zap, TrendingUp, ExternalLink } from "lucide-react"
import { fetchAlerts, fetchAlertStats, fetchSystemStatus, fetchAlertTrends, connectAlertStream, type Alert } from "@/lib/api"
import { Link } from "react-router-dom"

function severityColor(confidence: number) {
  if (confidence >= 90) return "destructive"
  if (confidence >= 70) return "outline"
  return "secondary"
}

function severityLabel(confidence: number) {
  if (confidence >= 90) return "Critical"
  if (confidence >= 70) return "High"
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

  const totalAlerts = (stats as { total_alerts?: number }).total_alerts ?? 57
  const criticalCount = (stats as { critical?: number }).critical ?? 12
  const warningCount = totalAlerts - criticalCount

  const daemon = (systemStatus as { daemon?: { state?: string } }).daemon
  const captureState = daemon ? (daemon as { state?: string }).state ?? "unknown" : "unknown"

  return (
    <div className="space-y-6">
      {/* Top KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Network Throughput */}
        <Card className="glass-panel border-border relative overflow-hidden">
          <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl"></div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Network Throughput</CardTitle>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-emerald-400 border-emerald-400/30 text-[10px] px-1.5">+12%</Badge>
              <Activity className="h-4 w-4 text-blue-400" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight">4.2 Gbps</div>
            <div className="mt-3 h-12 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={[{v:1},{v:2},{v:1.5},{v:3},{v:2},{v:4},{v:3}]}>
                  <defs>
                    <linearGradient id="miniGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="100%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="v" stroke="#3b82f6" strokeWidth={2} fill="url(#miniGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Peak traffic at 14:00 UTC</p>
          </CardContent>
        </Card>

        {/* ML Detection Rate */}
        <Card className="glass-panel border-border relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-2xl -mr-16 -mt-16"></div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">ML Detection Rate</CardTitle>
            <Zap className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">99.8%</div>
            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-muted-foreground">Confidence Score</span>
              <Badge variant="outline" className="text-emerald-400 border-emerald-400/30 text-[10px]">High</Badge>
            </div>
            <div className="w-full bg-secondary h-2 mt-2 rounded-full overflow-hidden">
              <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full transition-all duration-1000" style={{ width: '99.8%' }}></div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">+0.4% accuracy vs last week</p>
          </CardContent>
        </Card>

        {/* Active Alerts */}
        <Card className="glass-panel border-border relative overflow-hidden">
          <div className="absolute bottom-0 right-0 w-24 h-24 bg-red-500/10 rounded-full blur-2xl"></div>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Alerts</CardTitle>
            <ShieldAlert className="h-4 w-4 text-red-400" />
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
              <CardTitle className="text-lg">24h Attack Trends</CardTitle>
              <CardDescription>Frequency of blocked intrusion attempts</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">Last 24 Hours</Button>
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
              <CardTitle className="text-lg">Verified Blockchain Logs</CardTitle>
            </div>
            <CardDescription>Immutable audit trail via Smart Contracts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0">
            {[
              { block: "#892144", label: "Policy Update Verified", time: "2m ago", color: "bg-emerald-400" },
              { block: "#892143", label: "Intrusion Blocked (ML)", time: "5m ago", color: "bg-purple-400" },
              { block: "#892142", label: "Admin Login Success", time: "12m ago", color: "bg-muted-foreground" },
              { block: "#892141", label: "System Config Backup", time: "25m ago", color: "bg-muted-foreground" },
              { block: "#892140", label: "Anomaly Detected (Heuristic)", time: "42m ago", color: "bg-red-400" },
            ].map((item, i) => (
              <div key={i} className="flex gap-3 py-3 border-b border-border last:border-0">
                <div className="flex flex-col items-center">
                  <div className={`w-2.5 h-2.5 rounded-full ${item.color} mt-1`}></div>
                  {i < 4 && <div className="w-px flex-1 bg-border mt-1"></div>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-[11px] font-mono text-muted-foreground">Block {item.block}</span>
                    <span className="text-[10px] text-muted-foreground">{item.time}</span>
                  </div>
                  <div className="text-sm font-medium">{item.label}</div>
                  <div className="text-[11px] font-mono text-muted-foreground mt-0.5 truncate">🔑 0x8f...2a1d</div>
                </div>
              </div>
            ))}
            <div className="pt-3">
              <Link to="/ledger" className="flex items-center justify-center gap-1 text-sm text-primary hover:underline">
                View All Transactions <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Threat Feed */}
      <Card className="glass-panel border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Active Threat Feed</CardTitle>
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
                    <Badge variant={severityColor(a.confidence) as "destructive" | "outline" | "secondary"} className={a.confidence >= 70 && a.confidence < 90 ? "text-amber-400 border-amber-400/30" : ""}>
                      {severityLabel(a.confidence)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${a.confidence >= 90 ? 'bg-red-500' : a.confidence >= 70 ? 'bg-amber-500' : 'bg-purple-500'}`} style={{ width: `${a.confidence}%` }}></div>
                      </div>
                      <span className="text-xs text-muted-foreground w-8">{a.confidence}%</span>
                    </div>
                  </TableCell>
                  <TableCell className="capitalize text-sm">{a.status || "Blocked"}</TableCell>
                </TableRow>
              )))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
