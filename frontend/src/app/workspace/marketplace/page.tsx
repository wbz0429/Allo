"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { InstallDialog } from "@/components/workspace/marketplace/install-dialog";
import { SkillCard } from "@/components/workspace/marketplace/skill-card";
import { ToolCard } from "@/components/workspace/marketplace/tool-card";
import {
  installSkill,
  installTool,
  listMarketplaceSkills,
  listMarketplaceTools,
  listOrgSkills,
  listOrgTools,
  uninstallSkill,
  uninstallTool,
} from "@/core/marketplace/api";
import type {
  MarketplaceSkill,
  MarketplaceTool,
  OrgInstalledSkill,
  OrgInstalledTool,
} from "@/core/marketplace/types";

export default function MarketplacePage() {
  const [tools, setTools] = useState<MarketplaceTool[]>([]);
  const [skills, setSkills] = useState<MarketplaceSkill[]>([]);
  const [installedTools, setInstalledTools] = useState<OrgInstalledTool[]>([]);
  const [installedSkills, setInstalledSkills] = useState<OrgInstalledSkill[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [installDialogOpen, setInstallDialogOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState<MarketplaceTool | null>(
    null,
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [toolsData, skillsData, orgTools, orgSkills] = await Promise.all([
        listMarketplaceTools(),
        listMarketplaceSkills(),
        listOrgTools().catch(() => [] as OrgInstalledTool[]),
        listOrgSkills().catch(() => [] as OrgInstalledSkill[]),
      ]);
      setTools(toolsData);
      setSkills(skillsData);
      setInstalledTools(orgTools);
      setInstalledSkills(orgSkills);
    } catch {
      toast.error("Failed to load marketplace data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const isToolInstalled = useCallback(
    (toolId: string) => installedTools.some((t) => t.tool.id === toolId),
    [installedTools],
  );

  const isSkillInstalled = useCallback(
    (skillId: string) => installedSkills.some((s) => s.skill.id === skillId),
    [installedSkills],
  );

  const handleToolInstall = useCallback((tool: MarketplaceTool) => {
    setSelectedTool(tool);
    setInstallDialogOpen(true);
  }, []);

  const handleToolInstallConfirm = useCallback(
    async (toolId: string, config: Record<string, string>) => {
      setActionLoading(toolId);
      try {
        const installed = await installTool(toolId, config);
        setInstalledTools((prev) => [...prev, installed]);
        setInstallDialogOpen(false);
        setSelectedTool(null);
        toast.success("Tool installed successfully");
      } catch {
        toast.error("Failed to install tool");
      } finally {
        setActionLoading(null);
      }
    },
    [],
  );

  const handleToolUninstall = useCallback(async (tool: MarketplaceTool) => {
    setActionLoading(tool.id);
    try {
      await uninstallTool(tool.id);
      setInstalledTools((prev) => prev.filter((t) => t.tool.id !== tool.id));
      toast.success("Tool uninstalled");
    } catch {
      toast.error("Failed to uninstall tool");
    } finally {
      setActionLoading(null);
    }
  }, []);

  const handleSkillInstall = useCallback(async (skill: MarketplaceSkill) => {
    setActionLoading(skill.id);
    try {
      const installed = await installSkill(skill.id);
      setInstalledSkills((prev) => [...prev, installed]);
      toast.success("Skill installed successfully");
    } catch {
      toast.error("Failed to install skill");
    } finally {
      setActionLoading(null);
    }
  }, []);

  const handleSkillUninstall = useCallback(async (skill: MarketplaceSkill) => {
    setActionLoading(skill.id);
    try {
      await uninstallSkill(skill.id);
      setInstalledSkills((prev) =>
        prev.filter((s) => s.skill.id !== skill.id),
      );
      toast.success("Skill uninstalled");
    } catch {
      toast.error("Failed to uninstall skill");
    } finally {
      setActionLoading(null);
    }
  }, []);

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-8">
      <h1 className="mb-1 text-2xl font-semibold">Marketplace</h1>
      <p className="text-muted-foreground mb-6 text-sm">
        Browse and install MCP tools and skills for your organization.
      </p>

      <Tabs defaultValue="tools">
        <TabsList>
          <TabsTrigger value="tools">Tools</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
        </TabsList>

        <TabsContent value="tools" className="mt-4">
          {loading ? (
            <div className="text-muted-foreground py-12 text-center text-sm">
              Loading tools…
            </div>
          ) : tools.length === 0 ? (
            <div className="text-muted-foreground py-12 text-center text-sm">
              No tools available yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {tools.map((tool) => (
                <ToolCard
                  key={tool.id}
                  tool={tool}
                  installed={isToolInstalled(tool.id)}
                  onInstall={handleToolInstall}
                  onUninstall={handleToolUninstall}
                  loading={actionLoading === tool.id}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="skills" className="mt-4">
          {loading ? (
            <div className="text-muted-foreground py-12 text-center text-sm">
              Loading skills…
            </div>
          ) : skills.length === 0 ? (
            <div className="text-muted-foreground py-12 text-center text-sm">
              No skills available yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {skills.map((skill) => (
                <SkillCard
                  key={skill.id}
                  skill={skill}
                  installed={isSkillInstalled(skill.id)}
                  onInstall={handleSkillInstall}
                  onUninstall={handleSkillUninstall}
                  loading={actionLoading === skill.id}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <InstallDialog
        open={installDialogOpen}
        onOpenChange={setInstallDialogOpen}
        tool={selectedTool}
        onConfirm={handleToolInstallConfirm}
        loading={actionLoading === selectedTool?.id}
      />
    </div>
  );
}
