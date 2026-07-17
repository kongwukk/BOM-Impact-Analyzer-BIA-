export interface AffectedProduct {
  product_code: string;
  product_name: string;
  quantity: number;
  reference: string | null;
  is_critical: boolean;
}

export interface ImpactResult {
  part_number: string;
  manufacturer: string | null;
  lifecycle_status: "Active" | "NRND" | "EOL";
  affected_products: AffectedProduct[];
  total_affected: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function getImpact(partNumber: string): Promise<ImpactResult> {
  return request(`/api/impact/${encodeURIComponent(partNumber)}`);
}

export function uploadBom(file: File, productCode?: string): Promise<{
  product_id: number;
  components_imported: number;
  duplicates_skipped: number;
}> {
  const body = new FormData();
  body.append("file", file);
  if (productCode) body.append("product_code", productCode);
  return request("/api/bom/upload", { method: "POST", body });
}

