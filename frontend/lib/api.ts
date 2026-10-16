const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8015";
const fetch: typeof globalThis.fetch = (input, init) =>
  globalThis.fetch(input, { credentials: "include", ...init });

export type Company = {
  id: string;
  name: string;
  industry: string;
  website: string | null;
  monitor_status: string;
  last_scanned_at: string | null;
  candidate_count: number;
  high_risk_count: number;
};

export type CompanyCreate = {
  name: string;
  industry: string;
  website?: string | null;
  monitor_status?: string;
};

export type CandidateListItem = {
  id: string;
  name: string;
  current_company_id: string;
  company_name: string;
  title: string;
  department: string | null;
  location: string | null;
  domain: string | null;
  follow_status: string;
  risk_level: string | null;
  risk_score: number | null;
  confidence_score: number | null;
};

export type CandidateCreate = {
  name: string;
  current_company_id: string;
  title: string;
  department?: string | null;
  location?: string | null;
  domain?: string | null;
  profile_summary?: string | null;
  source_type?: string;
  follow_status?: string;
};

export type CandidateImportResult = {
  created_count: number;
  duplicate_count: number;
  failed_count: number;
  created_candidate_ids: string[];
  errors: string[];
};

export type Evidence = {
  id: string;
  candidate_id: string;
  company_id: string | null;
  source: string;
  title: string;
  url: string | null;
  screenshot_path: string | null;
  observed_at: string;
  event_time: string | null;
  summary: string;
  confidence: number;
  confirmed_by_user: boolean;
};

export function evidenceDocumentUrl(evidenceId: string) {
  return `${API_BASE_URL}/api/evidence/${encodeURIComponent(evidenceId)}/document`;
}

export type EvidenceDocumentUploadResponse = {
  evidence: Evidence;
  filename: string;
  content_type: string | null;
  extracted_characters: number;
  confirmed: boolean;
};

export type ExtractedCandidateDraft = {
  name: string | null;
  company_name: string | null;
  title: string | null;
  department: string | null;
  location: string | null;
  domain: string | null;
  profile_summary: string;
  confidence: number;
  source_excerpt: string;
};

export type DocumentCandidateExtractionResponse = {
  filename: string;
  content_type: string | null;
  extracted_characters: number;
  candidate_count: number;
  candidates: ExtractedCandidateDraft[];
};

export type EvidenceCreate = {
  candidate_id: string;
  company_id?: string | null;
  source: string;
  title: string;
  url?: string | null;
  screenshot_path?: string | null;
  summary: string;
  raw_text?: string | null;
  confidence: number;
  confirmed_by_user?: boolean;
};

export type EvidenceDraftUpdate = Partial<Omit<EvidenceDraft, "candidate_id" | "company_id">> & {
  candidate_id?: string | null;
  company_id?: string | null;
};

export type CandidateScore = {
  id: string;
  candidate_id: string;
  risk_score: number;
  confidence_score: number;
  risk_level: string;
  recommended_window: string | null;
  reason_codes: string[];
  input_snapshot: {
    evidence_count?: number;
    confirmed_count?: number;
    unconfirmed_count?: number;
    fresh_count?: number;
    stale_count?: number;
    avg_confidence?: number;
    source_weight_total?: number;
    features?: Array<{
      code: string;
      weight: number;
      confidence_weight: number;
      summary: string;
      evidence_ids: string[];
    }>;
    evidence?: Array<{
      id: string;
      source: string;
      source_weight: number;
      confidence: number;
      confirmed_by_user: boolean;
      age_days: number;
      is_fresh: boolean;
      title: string;
    }>;
  };
  explanation: string | null;
  limitations: string[];
  model_version: string;
  created_at: string;
};

export type CandidateDetail = {
  id: string;
  name: string;
  current_company_id: string;
  company_name: string;
  title: string;
  department: string | null;
  location: string | null;
  domain: string | null;
  profile_summary: string | null;
  source_type: string;
  follow_status: string;
  created_at: string;
  updated_at: string;
  latest_score: CandidateScore | null;
  evidence: Evidence[];
};

export type TalentPoolItem = {
  id: string;
  candidate_id: string;
  candidate_name: string;
  owner_user_id: string | null;
  company_id: string;
  company_name: string;
  title: string;
  department: string | null;
  domain: string | null;
  location: string | null;
  priority: string;
  status: string;
  note: string | null;
  risk_level: string | null;
  risk_score: number | null;
  confidence_score: number | null;
  recommended_window: string | null;
  added_at: string;
};

export type TalentPoolUpdate = {
  priority?: string;
  status?: string;
  note?: string;
};

export type Feedback = {
  id: string;
  candidate_id: string;
  user_id: string | null;
  outcome: string;
  contact_channel: string | null;
  note: string | null;
  contacted_at: string | null;
  created_at: string;
};

export type FeedbackCreate = {
  candidate_id: string;
  outcome: string;
  contact_channel?: string;
  note?: string;
};

export type EvidenceDraft = {
  candidate_id: string | null;
  company_id: string | null;
  source: string;
  title: string;
  url: string | null;
  screenshot_path: string | null;
  summary: string;
  raw_text: string | null;
  confidence: number;
};

export type BrowserTask = {
  id: string;
  user_id: string | null;
  task_type: string;
  query: string;
  target_site: string;
  status: string;
  result_summary: string | null;
  evidence_draft: EvidenceDraft | null;
  execution_log: Array<{
    event: string;
    message: string;
    at: string;
  }>;
  page_title: string | null;
  page_url: string | null;
  screenshot_path: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type BrowserTaskCreate = {
  task_type: string;
  query: string;
  target_site: string;
  candidate_id?: string;
  company_id?: string;
};

export type SourceConnection = {
  provider: string;
  label: string;
  status: string;
  mode: string;
  requires_user_login: boolean;
  notes: string;
};

export type TalentSourcingResponse = {
  query_plan: Array<{
    target_site: string;
    query: string;
    mode: string;
    reason?: string;
  }>;
  tasks: BrowserTask[];
  extracted_candidates: Array<{
    full_name: string | null;
    current_company: string | null;
    title: string | null;
    education: string | null;
    profile_links: string[];
    source_snippet: string | null;
    evidence: string | null;
    query: string | null;
    confidence: number;
    task_id: string | null;
    candidate_id: string | null;
  }>;
  compliance_note: string;
  model_provider: string;
  model_name: string;
  llm_used: boolean;
  used_fallback_plan: boolean;
};

export type AISummary = {
  candidate_id: string;
  summary: string;
  risk_explanation: string;
  conflict_notes: string[];
  cited_evidence_ids: string[];
  limitations: string[];
  model_provider: string;
  model_name: string;
  used_fallback: boolean;
};

export type OutreachVariant = {
  tone: string;
  message: string;
  evidence_ids: string[];
};

export type OutreachResponse = {
  candidate_id: string;
  variants: OutreachVariant[];
  compliance_note: string;
  model_provider: string;
  model_name: string;
  used_fallback: boolean;
};

export type LLMStatus = {
  provider: string;
  model: string;
  configured: boolean;
  base_url: string | null;
  fallback_model: string;
};

export type MetricCard = {
  key: string;
  label: string;
  value: number;
  display_value: string;
  description: string;
};

export type FunnelStep = {
  key: string;
  label: string;
  count: number;
};

export type TrendPoint = {
  label: string;
  high_risk: number;
  in_pool: number;
  contacted: number;
};

export type AnalyticsSummary = {
  metrics: MetricCard[];
  funnel: FunnelStep[];
  trend: TrendPoint[];
};

export type OrgGraphNode = {
  id: string;
  label: string;
  type: string;
  status: string;
  meta: Record<string, unknown>;
};

export type OrgGraphEdge = {
  source: string;
  target: string;
  relation: string;
  confidence: number;
};

export type OrgGraphResponse = {
  company_id: string | null;
  nodes: OrgGraphNode[];
  edges: OrgGraphEdge[];
};

export type ManagerSummary = {
  seats: Array<{ user_id: string; name: string; role: string; active: boolean; activity_count: number; llm_run_count: number }>;
  audit_count: number;
  llm_run_count: number;
  metrics: MetricCard[];
  team_rows: Array<{
    owner_user_id: string;
    pool_count: number;
    contacted_count: number;
    feedback_count: number;
    success_count: number;
    feedback_rate: number;
    conversion_rate: number;
  }>;
  risk_distribution: Record<string, number>;
  recommended_actions: string[];
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${path}`);
  }

  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<{ ok: boolean; payload: unknown }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      cache: "no-store"
    });

    const payload = await response.json();
    return {
      ok: response.ok,
      payload
    };
  } catch (error) {
    return {
      ok: false,
      payload: {
        error: {
          code: "BACKEND_UNAVAILABLE",
          message: "Backend health endpoint is not reachable.",
          details: {
            message: error instanceof Error ? error.message : "Unknown error"
          }
        }
      }
    };
  }
}

export function getCompanies() {
  return getJson<Company[]>("/api/companies");
}

export async function createCompany(payload: CompanyCreate): Promise<Company> {
  const response = await fetch(`${API_BASE_URL}/api/companies`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} create company`);
  }
  return response.json() as Promise<Company>;
}

export function getCandidates(params?: { company_id?: string }) {
  const search = new URLSearchParams();
  if (params?.company_id) search.set("company_id", params.company_id);
  const query = search.toString();
  return getJson<CandidateListItem[]>(`/api/candidates${query ? `?${query}` : ""}`);
}

export async function createCandidate(payload: CandidateCreate): Promise<CandidateDetail> {
  const response = await fetch(`${API_BASE_URL}/api/candidates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} create candidate`);
  }
  return response.json() as Promise<CandidateDetail>;
}

export async function updateCandidate(id: string, payload: Partial<CandidateCreate>): Promise<CandidateDetail> {
  const response = await fetch(`${API_BASE_URL}/api/candidates/${encodeURIComponent(id)}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`更新资料失败：${response.status}`);
  return response.json();
}

export async function updateCompany(id: string, payload: Partial<CompanyCreate>): Promise<Company> {
  const response = await fetch(`${API_BASE_URL}/api/companies/${encodeURIComponent(id)}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`更新公司失败：${response.status}`);
  return response.json();
}

export async function importCandidatesCsv(file: File): Promise<CandidateImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/candidates/import-csv`, {
    method: "POST",
    body: formData,
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} import candidates`);
  }
  return response.json() as Promise<CandidateImportResult>;
}

export function getCandidate(id: string) {
  return getJson<CandidateDetail>(`/api/candidates/${id}`);
}

export function getCandidateScore(id: string) {
  return getJson<CandidateScore>(`/api/candidates/${id}/score`);
}

export async function refreshCandidateScore(id: string): Promise<CandidateScore> {
  const response = await fetch(`${API_BASE_URL}/api/candidates/${id}/refresh-score`, {
    method: "POST",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} refresh-score`);
  }

  return response.json() as Promise<CandidateScore>;
}

export function getEvidence(candidateId: string) {
  return getJson<Evidence[]>(`/api/evidence?candidate_id=${candidateId}`);
}

export async function createEvidence(payload: EvidenceCreate): Promise<Evidence> {
  const response = await fetch(`${API_BASE_URL}/api/evidence`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} create evidence`);
  }
  return response.json() as Promise<Evidence>;
}

export async function confirmEvidence(evidenceId: string): Promise<Evidence> {
  const response = await fetch(`${API_BASE_URL}/api/evidence/${evidenceId}/confirm`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} confirm evidence`);
  }
  return response.json() as Promise<Evidence>;
}

export async function uploadEvidenceDocument(payload: {
  candidateId: string;
  companyId?: string | null;
  file: File;
  confirmedByUser?: boolean;
}): Promise<EvidenceDocumentUploadResponse> {
  const formData = new FormData();
  formData.append("candidate_id", payload.candidateId);
  if (payload.companyId) formData.append("company_id", payload.companyId);
  formData.append("confirmed_by_user", payload.confirmedByUser ? "true" : "false");
  formData.append("file", payload.file);
  const response = await fetch(`${API_BASE_URL}/api/evidence/upload-document`, {
    method: "POST",
    body: formData,
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} upload evidence document`);
  }
  return response.json() as Promise<EvidenceDocumentUploadResponse>;
}

export async function extractCandidatesDocument(file: File): Promise<DocumentCandidateExtractionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/evidence/extract-candidates-document`, {
    method: "POST",
    body: formData,
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} extract candidates document`);
  }
  return response.json() as Promise<DocumentCandidateExtractionResponse>;
}

export function getTalentPool(params?: {
  company_id?: string;
  risk_level?: string;
  status?: string;
  pending_feedback?: boolean;
}) {
  const search = new URLSearchParams();
  if (params?.company_id) search.set("company_id", params.company_id);
  if (params?.risk_level) search.set("risk_level", params.risk_level);
  if (params?.status) search.set("status", params.status);
  if (params?.pending_feedback) search.set("pending_feedback", "true");
  const query = search.toString();
  return getJson<TalentPoolItem[]>(`/api/talent-pool${query ? `?${query}` : ""}`);
}

export async function addCandidateToPool(candidateId: string): Promise<TalentPoolItem> {
  const response = await fetch(`${API_BASE_URL}/api/candidates/${candidateId}/add-to-pool`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} add-to-pool`);
  }
  return response.json() as Promise<TalentPoolItem>;
}

export async function updateTalentPoolItem(
  itemId: string,
  payload: TalentPoolUpdate
): Promise<TalentPoolItem> {
  const response = await fetch(`${API_BASE_URL}/api/talent-pool/${itemId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} update talent pool`);
  }
  return response.json() as Promise<TalentPoolItem>;
}

export async function deleteTalentPoolItem(itemId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/talent-pool/${itemId}`, {
    method: "DELETE",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} delete talent pool`);
  }
}

export function getFeedback(candidateId: string) {
  return getJson<Feedback[]>(`/api/feedback?candidate_id=${candidateId}`);
}

export async function createFeedback(payload: FeedbackCreate): Promise<Feedback> {
  const response = await fetch(`${API_BASE_URL}/api/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} create feedback`);
  }
  return response.json() as Promise<Feedback>;
}

export function getBrowserTasks() {
  return getJson<BrowserTask[]>("/api/browser-tasks");
}

export async function createBrowserTask(payload: BrowserTaskCreate): Promise<BrowserTask> {
  const response = await fetch(`${API_BASE_URL}/api/browser-tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} create browser task`);
  }
  return response.json() as Promise<BrowserTask>;
}

export function getSourceConnections() {
  return getJson<SourceConnection[]>("/api/source-connections");
}

export async function updateSourceConnection(provider: string, status: string): Promise<SourceConnection> {
  const response = await fetch(`${API_BASE_URL}/api/source-connections/${provider}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ status }),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} update source connection`);
  }
  return response.json() as Promise<SourceConnection>;
}

export async function runTalentSourcing(payload: {
  talent_profile: string;
  company_id?: string | null;
  candidate_id?: string | null;
  target_count?: number;
  public_site_scope?: string | null;
  max_tasks?: number;
}): Promise<TalentSourcingResponse> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 90000);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/sourcing/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ max_tasks: 2, ...payload }),
      cache: "no-store",
      signal: controller.signal
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("AI 检索耗时过长。建议先搜索 3-5 人，或限定 linkedin.com/in 后重试。");
    }
    throw new Error("无法连接后端服务，请确认 127.0.0.1:8015 正在运行。");
  } finally {
    window.clearTimeout(timeout);
  }
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text || `API request failed: ${response.status} run sourcing`);
  }
  return response.json() as Promise<TalentSourcingResponse>;
}

export async function saveCandidateLead(payload: {
  full_name: string;
  current_company?: string | null;
  title?: string | null;
  education?: string | null;
  profile_links?: string[];
  source_snippet?: string | null;
  confidence?: number;
}): Promise<{ candidate_id: string; company_id: string }> {
  const response = await fetch(`${API_BASE_URL}/api/sourcing/leads/save`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} save candidate lead`);
  }
  return response.json() as Promise<{ candidate_id: string; company_id: string }>;
}

export async function cancelBrowserTask(taskId: string): Promise<BrowserTask> {
  const response = await fetch(`${API_BASE_URL}/api/browser-tasks/${taskId}/cancel`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} cancel browser task`);
  }
  return response.json() as Promise<BrowserTask>;
}

export async function retryBrowserTask(taskId: string): Promise<BrowserTask> {
  const response = await fetch(`${API_BASE_URL}/api/browser-tasks/${taskId}/retry`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} retry browser task`);
  }
  return response.json() as Promise<BrowserTask>;
}

export async function confirmBrowserTaskEvidence(taskId: string): Promise<Evidence> {
  const response = await fetch(`${API_BASE_URL}/api/browser-tasks/${taskId}/confirm-evidence`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} confirm evidence`);
  }
  return response.json() as Promise<Evidence>;
}

export async function addBrowserTaskResultToPool(taskId: string): Promise<{
  candidate_id: string;
  evidence_id: string;
  pool_item_id: string;
}> {
  const response = await fetch(`${API_BASE_URL}/api/browser-tasks/${taskId}/add-to-pool`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} add search result to pool`);
  }
  return response.json() as Promise<{
    candidate_id: string;
    evidence_id: string;
    pool_item_id: string;
  }>;
}

export async function updateBrowserTaskEvidenceDraft(
  taskId: string,
  payload: EvidenceDraftUpdate
): Promise<BrowserTask> {
  const response = await fetch(`${API_BASE_URL}/api/browser-tasks/${taskId}/evidence-draft`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} update evidence draft`);
  }
  return response.json() as Promise<BrowserTask>;
}

export async function generateSummary(candidateId: string): Promise<AISummary> {
  const response = await fetch(`${API_BASE_URL}/api/candidates/${candidateId}/generate-summary`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} generate summary`);
  }
  return response.json() as Promise<AISummary>;
}

export function getLLMStatus() {
  return getJson<LLMStatus>("/api/llm/status");
}

export async function generateOutreach(candidateId: string): Promise<OutreachResponse> {
  const response = await fetch(`${API_BASE_URL}/api/candidates/${candidateId}/generate-outreach`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} generate outreach`);
  }
  return response.json() as Promise<OutreachResponse>;
}

export function getAnalyticsSummary() {
  return getJson<AnalyticsSummary>("/api/analytics/summary");
}

export function getOrgGraph(companyId?: string) {
  return getJson<OrgGraphResponse>(`/api/org-graph${companyId ? `?company_id=${companyId}` : ""}`);
}

export async function getManagerSummary(cookie = "") {
  const response = await fetch(`${API_BASE_URL}/api/manager/summary`, { cache: "no-store", headers: { Cookie: cookie } });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json() as Promise<ManagerSummary>;
}

export type DemoSession = { user_id: string; role: string; mode: string; users: Array<{ id: string; name: string; role: string }> };

export async function getDemoSession(cookie = ""): Promise<DemoSession> {
  const response = await fetch(`${API_BASE_URL}/api/session`, { cache: "no-store", credentials: "include", headers: cookie ? { Cookie: cookie } : {} });
  if (!response.ok) throw new Error(`Session unavailable: ${response.status}`);
  return response.json();
}

export async function switchDemoUser(userId: string) {
  const response = await fetch(`${API_BASE_URL}/api/session`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: userId }) });
  if (!response.ok) throw new Error("无法切换演示用户");
}

export async function recordUsageEvent(candidateId: string, kind: "candidate_view" | "outreach_copy") {
  const response = await fetch(`${API_BASE_URL}/api/usage-events`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id: candidateId, kind })
  });
  if (!response.ok) throw new Error("使用事件记录失败");
}

export function getWorkspaceSettings() { return getJson<{ mode: string; notice: string; database: string; llm: { configured: boolean; provider: string; model: string; base_url: string; fallback_model: string } }>("/api/workspace/settings"); }

export type Relationship = { id: string; company_id: string; source_candidate_id: string; target_candidate_id: string; source_name: string; target_name: string; relation: string; confidence: number; evidence_ids: string[]; evidence: Array<{ id: string; title: string; candidate_id: string }>; status: string; explanation: string };
export function getRelationships() { return getJson<Relationship[]>("/api/relationships"); }
export async function rebuildRelationships() {
  const response = await fetch(`${API_BASE_URL}/api/relationship-graph/rebuild`, { method: "POST", credentials: "include" });
  if (!response.ok) throw new Error("关系生成失败");
  return response.json() as Promise<Relationship[]>;
}
export async function decideRelationship(id: string, status: string) {
  const response = await fetch(`${API_BASE_URL}/api/relationships/${id}`, { method: "PATCH", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
  if (!response.ok) throw new Error("关系审核失败");
  return response.json() as Promise<Relationship>;
}
