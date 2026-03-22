import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/core/config", () => ({
  getBackendBaseURL: () => "http://localhost:8001",
}));

describe("admin API types", () => {
  it("OrgSummary has required fields", () => {
    const org: import("./types").OrgSummary = {
      id: "org-1",
      name: "Acme",
      slug: "acme",
      member_count: 5,
      total_tokens: 10000,
      total_api_calls: 200,
      created_at: "2024-01-01",
    };
    expect(org.id).toBe("org-1");
    expect(org.member_count).toBe(5);
    expect(org.total_tokens).toBe(10000);
  });

  it("UsageSummary has required fields", () => {
    const usage: import("./types").UsageSummary = {
      total_orgs: 3,
      total_users: 50,
      total_tokens: 100000,
      total_api_calls: 500,
      tokens_today: 5000,
      api_calls_today: 20,
    };
    expect(usage.total_api_calls).toBe(500);
    expect(usage.total_orgs).toBe(3);
  });

  it("OrgQuotas has required fields", () => {
    const quotas: import("./types").OrgQuotas = {
      max_rpm: 60,
      max_tokens_per_day: 100000,
      max_storage_mb: 1024,
    };
    expect(quotas.max_rpm).toBe(60);
  });

  it("DailyUsage has required fields", () => {
    const daily: import("./types").DailyUsage = {
      date: "2024-01-15",
      input_tokens: 3000,
      output_tokens: 2000,
      api_calls: 50,
    };
    expect(daily.api_calls).toBe(50);
  });
});
