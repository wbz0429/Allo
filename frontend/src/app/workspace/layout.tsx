"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { Toaster, toast } from "sonner";

import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { WorkspaceSidebar } from "@/components/workspace/workspace-sidebar";
import { getSession } from "@/core/auth/api";
import { getLocalSettings, useLocalSettings } from "@/core/settings";

const queryClient = new QueryClient();

export default function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const [settings, setSettings] = useLocalSettings();
  const [authorized, setAuthorized] = useState(false);
  const [open, setOpen] = useState(false); // SSR default: open (matches server render)
  useLayoutEffect(() => {
    // Runs synchronously before first paint on the client — no visual flash
    setOpen(!getLocalSettings().layout.sidebar_collapsed);
  }, []);
  useEffect(() => {
    setOpen(!settings.layout.sidebar_collapsed);
  }, [settings.layout.sidebar_collapsed]);

  useEffect(() => {
    void getSession().then((res) => {
      if (!res.data?.user_id) {
        if (res.error) {
          toast.error(res.error.message ?? "Failed to verify session");
        }
        router.replace("/login?callbackUrl=" + encodeURIComponent(pathname));
        return;
      }
      setAuthorized(true);
    });
  }, [pathname, router]);
  const handleOpenChange = useCallback(
    (open: boolean) => {
      setOpen(open);
      setSettings("layout", { sidebar_collapsed: !open });
    },
    [setSettings],
  );
  if (!authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Checking session...</p>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <SidebarProvider
        className="h-screen"
        open={open}
        onOpenChange={handleOpenChange}
      >
        <WorkspaceSidebar />
        <SidebarInset className="min-w-0">{children}</SidebarInset>
      </SidebarProvider>
      <Toaster position="top-center" />
    </QueryClientProvider>
  );
}
