export interface OrgMember {
  user_id: string;
  name: string;
  email: string;
  role: "admin" | "member";
  joined_at: string;
}

export interface OrgUsageStats {
  total_tokens: number;
  total_api_calls: number;
  tokens_today: number;
  api_calls_today: number;
  usage_by_day: OrgDailyUsage[];
}

export interface OrgDailyUsage {
  date: string;
  input_tokens: number;
  output_tokens: number;
  api_calls: number;
}

export interface UserUsageBreakdown {
  user_id: string;
  user_name: string;
  user_email: string;
  input_tokens: number;
  output_tokens: number;
  api_calls: number;
}
