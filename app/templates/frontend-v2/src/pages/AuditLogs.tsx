import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ClipboardList,
  FileSearch,
  History,
  MonitorSmartphone,
  Search,
  ShieldCheck,
  Wifi,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";

type AuditLog = {
  id: string;
  user_id?: string | null;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  details?: Record<string, unknown> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  facility_slug?: string | null;
  created_at: string;
};

const parseClient = (userAgent?: string | null) => {
  if (!userAgent) {
    return "Unknown client";
  }

  const browser =
    /Edg\//.test(userAgent)
      ? "Edge"
      : /Chrome\//.test(userAgent) && !/Chromium\//.test(userAgent)
        ? "Chrome"
        : /Safari\//.test(userAgent) && /Version\//.test(userAgent)
          ? "Safari"
          : /Firefox\//.test(userAgent)
            ? "Firefox"
            : "Browser";

  const device =
    /iPhone/i.test(userAgent)
      ? "iPhone"
      : /iPad/i.test(userAgent)
        ? "iPad"
        : /Android/i.test(userAgent)
          ? "Android"
          : /Windows/i.test(userAgent)
            ? "Windows"
            : /Macintosh|Mac OS X/i.test(userAgent)
              ? "Mac"
              : "Device";

  return `${browser} on ${device}`;
};

const AuditLogs = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useTenantParams();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [resourceType, setResourceType] = useState("all");

  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const visibleLogs = useMemo(() => {
    const query = search.trim().toLowerCase();
    return logs.filter((log) => {
      const details = JSON.stringify(log.details || {}).toLowerCase();
      const matchesResource =
        resourceType === "all" || log.resource_type === resourceType;
      const matchesSearch =
        !query ||
        log.action.toLowerCase().includes(query) ||
        (log.resource_type || "").toLowerCase().includes(query) ||
        (log.resource_id || "").toLowerCase().includes(query) ||
        (log.ip_address || "").toLowerCase().includes(query) ||
        parseClient(log.user_agent).toLowerCase().includes(query) ||
        (log.user_agent || "").toLowerCase().includes(query) ||
        details.includes(query);
      return matchesResource && matchesSearch;
    });
  }, [logs, resourceType, search]);

  const resources = useMemo(() => {
    const unique = Array.from(
      new Set(logs.map((log) => log.resource_type).filter(Boolean))
    ) as string[];
    return unique.sort();
  }, [logs]);

  const summary = useMemo(
    () => ({
      users: new Set(logs.map((log) => log.user_id).filter(Boolean)).size,
      resources: resources.length,
      actions: new Set(logs.map((log) => log.action)).size,
    }),
    [logs, resources.length]
  );

  const loadLogs = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<AuditLog[]>("/audit-logs?limit=200");
      setLogs(response);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs().catch(() => {
      setLogs([]);
      setLoading(false);
    });
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 px-6 py-4 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Button
              variant="ghost"
              className="mb-2 -ml-3 gap-2 text-muted-foreground"
              onClick={() => navigate(dashboardPath)}
            >
              <ArrowLeft className="h-4 w-4" /> Dashboard
            </Button>
            <h1 className="text-2xl font-extrabold tracking-tight">Audit Logs</h1>
            <p className="text-sm text-muted-foreground">
              Review security and operational events for this facility.
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Events" value={String(logs.length)} icon={History} />
          <Metric label="Users" value={String(summary.users)} icon={ShieldCheck} />
          <Metric label="Resources" value={String(summary.resources)} icon={FileSearch} />
          <Metric label="Actions" value={String(summary.actions)} icon={ClipboardList} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <CardTitle className="text-base">Events</CardTitle>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Select value={resourceType} onValueChange={setResourceType}>
                  <SelectTrigger className="w-full sm:w-44">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All resources</SelectItem>
                    {resources.map((resource) => (
                      <SelectItem key={resource} value={resource}>
                        {resource}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search audit events"
                    className="w-full pl-9 sm:w-80"
                  />
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading audit logs...
              </p>
            ) : visibleLogs.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-2">
                {visibleLogs.map((log, index) => (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.02 }}
                    className="grid gap-3 rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30 xl:grid-cols-[1fr_.8fr_1fr_1fr]"
                  >
                    <div>
                      <p className="font-semibold text-foreground">{log.action}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(log.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium capitalize text-foreground">
                        {log.resource_type || "system"}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {log.resource_id || "No resource id"}
                      </p>
                    </div>
                    <div className="space-y-2 text-xs text-muted-foreground">
                      <p className="flex min-w-0 items-center gap-2">
                        <Wifi className="h-3.5 w-3.5 shrink-0 text-primary" />
                        <span className="truncate">{log.ip_address || "No IP captured"}</span>
                      </p>
                      <p className="flex min-w-0 items-center gap-2">
                        <MonitorSmartphone className="h-3.5 w-3.5 shrink-0 text-primary" />
                        <span className="truncate" title={log.user_agent || undefined}>
                          {parseClient(log.user_agent)}
                        </span>
                      </p>
                    </div>
                    <pre className="max-h-20 overflow-hidden whitespace-pre-wrap rounded-lg bg-muted/50 p-2 text-xs text-muted-foreground">
                      {JSON.stringify(log.details || {}, null, 2)}
                    </pre>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

const Metric = ({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
}) => (
  <Card className="border-border/60">
    <CardContent className="flex items-center gap-4 p-5">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div>
        <p className="text-2xl font-extrabold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </CardContent>
  </Card>
);

const EmptyState = () => (
  <div className="py-16 text-center">
    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
      <History className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No audit logs found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Security events will appear here as staff use the system.
    </p>
  </div>
);

export default AuditLogs;
