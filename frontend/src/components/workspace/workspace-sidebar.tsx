"use client";

import { LogOutIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { logout } from "@/core/auth/api";

import { RecentChatList } from "./recent-chat-list";
import { WorkspaceHeader } from "./workspace-header";
import { WorkspaceNavChatList } from "./workspace-nav-chat-list";
import { WorkspaceNavMenu } from "./workspace-nav-menu";

export function WorkspaceSidebar({
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const { open: isSidebarOpen } = useSidebar();
  const router = useRouter();

  async function handleLogout() {
    const result = await logout();

    if (result.error) {
      toast.error(result.error.message ?? "Sign out failed");
      return;
    }

    router.push("/login");
  }

  return (
    <>
      <Sidebar variant="sidebar" collapsible="icon" {...props}>
        <SidebarHeader className="py-0">
          <WorkspaceHeader />
        </SidebarHeader>
        <SidebarContent>
          <WorkspaceNavChatList />
          {isSidebarOpen && <RecentChatList />}
        </SidebarContent>
        <SidebarFooter>
          <WorkspaceNavMenu />
          <Button
            variant="ghost"
            size={isSidebarOpen ? "default" : "icon"}
            className="w-full justify-start gap-2 text-muted-foreground"
            onClick={handleLogout}
          >
            <LogOutIcon className="size-4" />
            {isSidebarOpen && <span>Sign out</span>}
          </Button>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
    </>
  );
}
