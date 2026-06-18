import { useEffect, useRef, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FaPlus, FaMinus, FaCrosshairs } from "react-icons/fa"

interface Node {
  id: string
  label: string
  hostname: string
  ip: string
  os: string
  type: "server" | "workstation" | "iot"
  status: "secure" | "suspicious" | "threat" | "verified"
  riskScore: number
  x: number
  y: number
}

interface Edge {
  from: string
  to: string
}

const STATUS_COLORS: Record<string, string> = {
  secure: "#10b981",
  suspicious: "#f59e0b",
  threat: "#ef4444",
  verified: "#3b82f6",
}

const TYPE_FILTER = ["All Devices", "Servers", "Workstations", "IoT"] as const

export default function Topology() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [filter, setFilter] = useState<typeof TYPE_FILTER[number]>("All Devices")
  const [zoom, setZoom] = useState(1)

  const loadTopology = useCallback(async () => {
    try {
      const { fetchSystemTopology } = await import("@/lib/api")
      const data = await fetchSystemTopology()
      setNodes(data.nodes)
      setEdges(data.edges)
      if (data.nodes.length > 0 && !selectedNode) {
        setSelectedNode(data.nodes[0])
      }
    } catch {
      // Ignore
    }
  }, [])

  useEffect(() => { loadTopology() }, [loadTopology])

  const filteredNodes = nodes.filter(n => {
    if (filter === "All Devices") return true
    if (filter === "Servers") return n.type === "server"
    if (filter === "Workstations") return n.type === "workstation"
    if (filter === "IoT") return n.type === "iot"
    return true
  })
  const filteredIds = new Set(filteredNodes.map(n => n.id))
  const filteredEdges = edges.filter(e => filteredIds.has(e.from) && filteredIds.has(e.to))

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr * zoom, dpr * zoom)

    // Clear
    ctx.clearRect(0, 0, canvas.width / zoom, canvas.height / zoom)

    // Edges
    filteredEdges.forEach(edge => {
      const fromNode = filteredNodes.find(n => n.id === edge.from)
      const toNode = filteredNodes.find(n => n.id === edge.to)
      if (!fromNode || !toNode) return

      const isThreated = fromNode.status === "threat" || toNode.status === "threat"
      ctx.strokeStyle = isThreated ? "rgba(239, 68, 68, 0.3)" : "rgba(59, 130, 246, 0.15)"
      ctx.lineWidth = isThreated ? 1.5 : 1
      ctx.setLineDash(isThreated ? [4, 4] : [])
      ctx.beginPath()
      ctx.moveTo(fromNode.x, fromNode.y)
      ctx.lineTo(toNode.x, toNode.y)
      ctx.stroke()
      ctx.setLineDash([])
    })

    // Nodes
    filteredNodes.forEach(node => {
      const color = STATUS_COLORS[node.status]
      const isSelected = selectedNode?.id === node.id

      // Glow
      if (node.status === "threat" || node.status === "suspicious") {
        ctx.beginPath()
        ctx.arc(node.x, node.y, 20, 0, Math.PI * 2)
        ctx.fillStyle = `${color}15`
        ctx.fill()
      }

      // Node shape
      const size = 14
      if (node.type === "server") {
        ctx.fillStyle = `${color}30`
        ctx.strokeStyle = color
        ctx.lineWidth = isSelected ? 2.5 : 1.5
        ctx.beginPath()
        ctx.roundRect(node.x - size, node.y - size, size * 2, size * 2, 4)
        ctx.fill()
        ctx.stroke()
        // Server icon
        ctx.fillStyle = color
        ctx.fillRect(node.x - 6, node.y - 6, 12, 4)
        ctx.fillRect(node.x - 6, node.y + 1, 12, 4)
      } else if (node.type === "workstation") {
        ctx.fillStyle = `${color}30`
        ctx.strokeStyle = color
        ctx.lineWidth = isSelected ? 2.5 : 1.5
        ctx.beginPath()
        ctx.arc(node.x, node.y, size - 2, 0, Math.PI * 2)
        ctx.fill()
        ctx.stroke()
      } else {
        // IoT - diamond
        ctx.fillStyle = `${color}30`
        ctx.strokeStyle = color
        ctx.lineWidth = isSelected ? 2.5 : 1.5
        ctx.beginPath()
        ctx.moveTo(node.x, node.y - size)
        ctx.lineTo(node.x + size, node.y)
        ctx.lineTo(node.x, node.y + size)
        ctx.lineTo(node.x - size, node.y)
        ctx.closePath()
        ctx.fill()
        ctx.stroke()
      }

      // Threat indicator triangle
      if (node.status === "threat") {
        ctx.fillStyle = "#ef4444"
        ctx.beginPath()
        ctx.moveTo(node.x + 10, node.y - 18)
        ctx.lineTo(node.x + 18, node.y - 6)
        ctx.lineTo(node.x + 2, node.y - 6)
        ctx.closePath()
        ctx.fill()
        ctx.fillStyle = "#1a1f2e"
        ctx.font = "bold 8px sans-serif"
        ctx.textAlign = "center"
        ctx.fillText("!", node.x + 10, node.y - 9)
      }

      // Verified checkmark
      if (node.status === "verified") {
        ctx.fillStyle = "#3b82f6"
        ctx.beginPath()
        ctx.arc(node.x + 12, node.y - 12, 6, 0, Math.PI * 2)
        ctx.fill()
        ctx.strokeStyle = "#fff"
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.moveTo(node.x + 9, node.y - 12)
        ctx.lineTo(node.x + 11.5, node.y - 10)
        ctx.lineTo(node.x + 15, node.y - 14)
        ctx.stroke()
      }
    })
  }, [filteredNodes, filteredEdges, selectedNode, zoom])

  useEffect(() => { draw() }, [draw])

  useEffect(() => {
    const handleResize = () => draw()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [draw])

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) / zoom
    const y = (e.clientY - rect.top) / zoom
    
    const clicked = filteredNodes.find(n => Math.hypot(n.x - x, n.y - y) < 18)
    setSelectedNode(clicked || null)
  }

  const vulnerableCount = filteredNodes.filter(n => n.status === "threat" || n.status === "suspicious").length

  return (
    <div className="flex gap-4 h-[calc(100vh-8rem)]">
      {/* Left Panel */}
      <div className="w-56 flex-shrink-0 space-y-4">
        {/* Selected Node Details */}
        {selectedNode && (
          <Card className={`glass-panel ${selectedNode.status === "threat" ? "border-red-500/30" : "border-border"}`}>
            <CardHeader className="pb-2">
              <CardTitle className={`text-xs font-bold uppercase tracking-wider ${selectedNode.status === "threat" ? "text-red-400" : selectedNode.status === "suspicious" ? "text-amber-400" : "text-emerald-400"}`}>
                {selectedNode.status === "threat" ? "THREAT DETECTED" : selectedNode.status === "suspicious" ? "SUSPICIOUS" : "SECURE"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Hostname</span><span className="font-medium">{selectedNode.hostname}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">IP Address</span><span className="font-mono font-medium">{selectedNode.ip}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">OS</span><span className="font-medium">{selectedNode.os}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">ML Risk Score</span><span className={`font-bold ${selectedNode.riskScore >= 0.7 ? "text-red-400" : selectedNode.riskScore >= 0.4 ? "text-amber-400" : "text-emerald-400"}`}>{selectedNode.riskScore.toFixed(2)} ({selectedNode.riskScore >= 0.7 ? "High" : selectedNode.riskScore >= 0.4 ? "Medium" : "Low"})</span></div>
              <div className="pt-1 border-t border-border">
                <span className="text-xs font-mono text-muted-foreground">{selectedNode.status === 'verified' ? 'Verified on Polygon' : 'Local Detection'}</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Legend */}
        <Card className="glass-panel">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold">Map Legend</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Secure Node</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Suspicious Activity</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-red-400"></span> Active Threat</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-blue-400"></span> Blockchain Verified</div>
          </CardContent>
        </Card>

        <Button variant="destructive" className="w-full" size="sm">Export Network Report</Button>
      </div>

      {/* Canvas Area */}
      <div className="flex-1 relative">
        {/* Filter Tabs */}
        <div className="absolute top-4 left-4 z-10 flex gap-2">
          {TYPE_FILTER.map(f => (
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

        {/* Zoom Controls */}
          <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
            <Button variant="secondary" size="icon" className="h-8 w-8 bg-card/80 backdrop-blur" onClick={() => setZoom(z => Math.min(z + 0.2, 3))}>
              <FaPlus className="h-4 w-4" />
            </Button>
            <Button variant="secondary" size="icon" className="h-8 w-8 bg-card/80 backdrop-blur" onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))}>
              <FaMinus className="h-4 w-4" />
            </Button>
            <Button variant="secondary" size="icon" className="h-8 w-8 bg-card/80 backdrop-blur" onClick={() => setZoom(1)}>
              <FaCrosshairs className="h-4 w-4" />
            </Button>
          </div>

        {/* Canvas */}
        <Card className="glass-panel h-full overflow-hidden">
          <canvas
            ref={canvasRef}
            className="w-full h-full cursor-pointer"
            onClick={handleCanvasClick}
            style={{ display: "block" }}
          />
        </Card>

        {/* Bottom Status */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-6 bg-background/80 backdrop-blur border border-border px-6 py-3 rounded-lg">
          <div>
            <div className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Network Status</div>
            <div className={`font-semibold flex items-center gap-1.5 ${vulnerableCount > 0 ? "text-red-400" : "text-emerald-400"}`}>
              <span className={`w-2 h-2 rounded-full ${vulnerableCount > 0 ? "bg-red-400" : "bg-emerald-400"}`}></span>
              {vulnerableCount > 0 ? "Vulnerable" : "Secure"}
            </div>
          </div>
          <div className="w-px h-8 bg-border"></div>
          <div>
            <div className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Total Nodes</div>
            <div className="text-lg font-bold">{filteredNodes.length}</div>
          </div>
          <div className="w-px h-8 bg-border"></div>
          <div>
            <div className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Ledger Sync</div>
            <div className="font-semibold text-emerald-400 flex items-center gap-1">100%</div>
          </div>
        </div>
      </div>
    </div>
  )
}
