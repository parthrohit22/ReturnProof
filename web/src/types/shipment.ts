/**
 * A loose, permissive shape for previewing a return shipment payload before
 * submission. Deliberately not a strict mirror of ReturnShipment, that
 * validation belongs to the server (parse_shipment), this is only for
 * showing the operator what they're about to submit.
 */

export interface ShipmentPreview {
  return_id?: string;
  warehouse_report?: {
    items?: Array<{
      item_id?: string;
      sku?: string;
      quantity_received?: number;
      condition?: string;
      damaged_quantity?: number;
      batch_code?: string | null;
    }>;
  };
  supplier_events?: Array<{
    event_id?: string;
    item_id?: string;
    instruction?: string;
  }>;
  product_metadata?: Array<{
    sku?: string;
    known_batches?: unknown[];
  }>;
}

export function parseShipmentPreview(raw: unknown): ShipmentPreview | null {
  if (typeof raw !== "object" || raw === null) {
    return null;
  }
  return raw as ShipmentPreview;
}
