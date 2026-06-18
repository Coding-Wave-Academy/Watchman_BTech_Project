import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { FaCube, FaClock, FaCheckCircle, FaChevronLeft, FaChevronRight, FaFilter } from "react-icons/fa"
import { useState, useEffect, useCallback } from "react"
import { fetchSystemLedger } from "@/lib/api"

export default function Ledger() {
  const [page, setPage] = useState(0)
  const pageSize = 7
  const [blocks, setBlocks] = useState<any[]>([])
  const [totalBlocks, setTotalBlocks] = useState(0)
  
  const loadLedger = useCallback(async () => {
    try {
      const data = await fetchSystemLedger(pageSize, page * pageSize)
      setBlocks(data.blocks)
      setTotalBlocks(data.total)
    } catch {
      // Ignore
    }
  }, [page])

  useEffect(() => { loadLedger() }, [loadLedger])
  
  const totalPages = Math.ceil(totalBlocks / pageSize) || 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Blockchain Ledger</h1>
          <p className="text-muted-foreground mt-1">Immutable security event tracking & verification</p>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => alert("Filter options coming soon")}>
          <FaFilter className="h-4 w-4" /> Filter
        </Button>
      </div>

      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">TOTAL BLOCKS</CardTitle>
            <FaCube className="h-5 w-5 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold">{totalBlocks.toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">LAST BLOCK TIME</CardTitle>
            <FaClock className="h-5 w-5 text-blue-400" />
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">
              {blocks.length > 0 ? new Date(blocks[0].timestamp).toLocaleTimeString() : "N/A"}
            </span>
          </CardContent>
        </Card>
        <Card className="glass-panel border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">NODE SYNC STATUS</CardTitle>
            <FaCheckCircle className="h-5 w-5 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold">100%</span>
              <Badge variant="outline" className="mb-1 border-emerald-400/30 text-emerald-400 text-[10px]">Synced</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chronological Ledger Table */}
      <Card className="glass-panel border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Chronological Ledger</CardTitle>
            <CardDescription>Showing verified alerts and policy updates</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent border-border">
                <TableHead className="text-xs uppercase tracking-wider pl-6">Block Height</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Timestamp</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Event Type</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Transaction Hash</TableHead>
                <TableHead className="text-xs uppercase tracking-wider">Verification Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {blocks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    No verified blocks found.
                  </TableCell>
                </TableRow>
              ) : (
              blocks.map((block) => (
                <TableRow key={block.height} className="border-border h-14">
                  <TableCell className="pl-6">
                    <span className="font-mono font-semibold text-primary">#{block.height}</span>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">{new Date(block.timestamp).toLocaleString()}</TableCell>
                  <TableCell>
                    <Badge
                      variant={block.eventType === "Alert Logged" ? "destructive" : block.eventType === "Policy Updated" ? "default" : "secondary"}
                      className={`text-xs ${block.eventType === "Policy Updated" ? "bg-blue-600" : block.eventType === "Model Retrained" ? "bg-purple-600" : ""}`}
                    >
                      {block.eventType}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <code className="text-xs text-muted-foreground bg-secondary/50 px-2 py-1 rounded">
                      {block.txHash.length > 20 ? `${block.txHash.slice(0, 8)}...${block.txHash.slice(-8)}` : block.txHash}
                    </code>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5 text-sm">
                      <span className={`w-2 h-2 rounded-full ${block.nodes >= 12 ? "bg-emerald-400" : "bg-amber-400"}`}></span>
                      Validated by {block.nodes} nodes
                    </div>
                  </TableCell>
                </TableRow>
              )))}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="flex items-center justify-between px-6 py-3 border-t border-border">
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
                <FaChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}>
                <FaChevronRight className="h-4 w-4" />
              </Button>
            </div>
            <span className="text-sm text-muted-foreground">Page {page + 1} of {totalPages.toLocaleString()}</span>
          </div>
        </CardContent>
      </Card>

      {/* Bottom Status Bar */}
      <div className="fixed bottom-0 left-64 right-0 border-t border-border bg-card/80 backdrop-blur-md px-6 py-2 flex items-center justify-center gap-4 text-[11px] font-mono text-muted-foreground tracking-wider z-10">
        <span>NODE_HASH_A823B</span>
        <span>·</span>
        <span>SECURITY_PROTOCOL_V4.2</span>
        <span>·</span>
        <span>WATCHMAN_CORE_LEDGER</span>
      </div>
    </div>
  )
}
