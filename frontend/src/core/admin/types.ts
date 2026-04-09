export interface OrgSummary {
  id: string;
  name: string;
  slug: string;
  member_count: number;
  created_at: string;
}

export interface OrgDetail extends OrgSummary {
  quotas?: OrgQuotas;
  usage_by_day?: DailyUsage[];
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
  total_api_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_sandbox_seconds: number;
  total_usage_records: number;
}

export interface UserUsageBreakdown {
  user_id: string;
  display_name: string | null;
  email: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  api_calls: number;
}

export interface UserUsageRanking {
  metric: "total_tokens" | "api_calls" | "input_tokens" | "output_tokens";
  items: UserUsageBreakdown[];
}
