import { Package, Truck, Database } from "lucide-react";

import type { ShipmentPreview } from "../../types/shipment";

interface ShipmentPreviewCardProps {
  preview: ShipmentPreview;
}

export function ShipmentPreviewCard({ preview }: ShipmentPreviewCardProps) {
  const items = preview.warehouse_report?.items ?? [];
  const events = preview.supplier_events ?? [];
  const metadata = preview.product_metadata ?? [];

  return (
    <div className="rounded-md border border-border bg-surface-sunken p-3 text-sm">
      <p className="font-medium text-text-primary">{preview.return_id ?? "Untitled return"}</p>
      <dl className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <div className="flex items-center gap-2">
          <Package size={14} className="text-text-muted" aria-hidden="true" />
          <span>
            <dt className="text-xs text-text-muted">Warehouse items</dt>
            <dd className="font-mono-tabular text-text-primary">{items.length}</dd>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Truck size={14} className="text-text-muted" aria-hidden="true" />
          <span>
            <dt className="text-xs text-text-muted">Supplier events</dt>
            <dd className="font-mono-tabular text-text-primary">{events.length}</dd>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Database size={14} className="text-text-muted" aria-hidden="true" />
          <span>
            <dt className="text-xs text-text-muted">Product metadata entries</dt>
            <dd className="font-mono-tabular text-text-primary">{metadata.length}</dd>
          </span>
        </div>
      </dl>
      {items.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1 border-t border-border pt-2">
          {items.map((item, index) => (
            <li key={item.item_id ?? index} className="flex items-center justify-between text-xs">
              <span className="text-text-secondary">
                {item.item_id ?? "?"} · {item.sku ?? "?"}
              </span>
              <span className="font-mono-tabular text-text-muted">
                {item.quantity_received ?? "?"} units, {item.condition ?? "?"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
