export interface OrgSummary {
  id: string;
  name: string;
  slug: string;
  member_count: number;
  total_tokens: number;
  total_api_calls: number;
  created_at: string;
}

export interface OrgDetail extends OrgSummary {
  quotas: OrgQuotas;
  usage_by_day: DailyUsage[];
}

export interface OrgQuotas {
  max_rpm: number;
  max_tokens_per_day: number;
  max_storage_mb: number;
}

export interface DailyUsage {
  date: string;
  input_tokens: number;
  output_tokens: number;
  api_calls: number;
}

export interface UsageSummary {
  total_orgs: number;
  total_users: number;
  total_tokens: number;
  total_api_calls: number;
  tokens_today: number;
  api_calls_today: number;
}

export interface OrgUsageBreakdown {
  org_id: string;
  org_name: string;
  input_tokens: number;
  output_tokens: number;
  api_calls: number;
}
