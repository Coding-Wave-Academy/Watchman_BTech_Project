import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import MainLayout from "@/components/layout/MainLayout"
import Dashboard from "@/pages/Dashboard"
import Alerts from "@/pages/Alerts"
import Topology from "@/pages/Topology"
import Ledger from "@/pages/Ledger"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="topology" element={<Topology />} />
          <Route path="ledger" element={<Ledger />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
