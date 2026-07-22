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

export interface ComponentCandidate {
  id: number;
  part_number: string;
  material_code: string | null;
  description: string | null;
  manufacturer: string | null;
}

export interface OverviewData {
  product_count: number;
  component_count: number;
  bom_item_count: number;
  recent_products: Array<{
    product_code: string;
    product_name: string;
    component_count: number;
    updated_at: string;
  }>;
}

export interface NaturalQueryResult {
  question: string;
  interpreted_as: {
    intent: string;
    manufacturer: string | null;
    part_number: string | null;
    product_code: string | null;
    keywords: string[];
    lifecycle_status: string | null;
    critical_only: boolean;
  };
  results: Array<{
    product_code: string;
    product_name: string;
    part_number: string;
    manufacturer: string | null;
    description: string | null;
    lifecycle_status: string;
    quantity: number;
    reference: string | null;
    is_critical: boolean;
  }>;
  total: number;
  mode: "llm-structured" | "structured-rules" | "rules-fallback";
  answer: string;
  warning: string | null;
}

export interface LlmStatus {
  enabled: boolean;
  available: boolean;
  provider: string;
  model: string | null;
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

export function getImpactById(componentId: number): Promise<ImpactResult> {
  return request(`/api/impact/component/${componentId}`);
}

export function searchComponents(query: string): Promise<ComponentCandidate[]> {
  return request(`/api/impact/search?q=${encodeURIComponent(query)}`);
}

export function getOverview(): Promise<OverviewData> {
  return request("/api/overview");
}

export function askNaturalQuestion(question: string): Promise<NaturalQueryResult> {
  return request("/api/query/natural", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export function getLlmStatus(): Promise<LlmStatus> {
  return request("/api/query/status");
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
