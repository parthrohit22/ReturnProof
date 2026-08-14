import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { ReturnsQueue } from "./routes/ReturnsQueue";
import { NewReconciliation } from "./routes/NewReconciliation";
import { ReturnWorkspace } from "./routes/ReturnWorkspace";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/returns" replace />} />
        <Route path="/returns" element={<ReturnsQueue />} />
        <Route path="/returns/new" element={<NewReconciliation />} />
        <Route path="/returns/:id" element={<ReturnWorkspace />} />
        <Route path="*" element={<Navigate to="/returns" replace />} />
      </Routes>
    </AppShell>
  );
}
