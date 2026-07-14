import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  Bell,
  CheckCircle2,
  Info,
  Megaphone,
  Plus,
  Search,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useRealtimeRefresh } from "@/hooks/useRealtimeRefresh";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";
import { getFacilityStaff, type FacilityStaffAccount } from "@/lib/facility-staff";
import {
  addSettledError,
  hasResourceErrors,
  settledValue,
  type ResourceErrors,
} from "@/lib/resource-loading";

type Alert = {
  id: string;
  facility_slug: string;
  alert_type: "info" | "warning" | "critical" | string;
  title: string;
  message: string;
  recipient_id?: string | null;
  recipient_name?: string | null;
  is_read: boolean;
  read_at?: string | null;
  expires_at?: string | null;
  created_at: string;
};

const emptyForm = {
  alert_type: "info",
  title: "",
  message: "",
  recipient_mode: "facility",
  recipient_id: "",
  recipient_role: "NURSE",
  expires_at: "",
};

type AlertResource = "alerts" | "staff";

const Alerts = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [staff, setStaff] = useState<FacilityStaffAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<ResourceErrors<AlertResource>>({});

  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const visibleAlerts = useMemo(() => {
    const query = search.trim().toLowerCase();
    return alerts.filter((alert) => {
      const matchesFilter =
        filter === "all" ||
        (filter === "unread" && !alert.is_read) ||
        alert.alert_type === filter;
      const matchesSearch =
        !query ||
        alert.title.toLowerCase().includes(query) ||
        alert.message.toLowerCase().includes(query) ||
        (alert.recipient_name || "").toLowerCase().includes(query);
      return matchesFilter && matchesSearch;
    });
  }, [alerts, filter, search]);

  const summary = useMemo(
    () => ({
      unread: alerts.filter((alert) => !alert.is_read).length,
      critical: alerts.filter((alert) => alert.alert_type === "critical").length,
      warning: alerts.filter((alert) => alert.alert_type === "warning").length,
    }),
    [alerts]
  );

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const [alertResponse, staffResponse] = await Promise.allSettled([
        apiClient.get<Alert[]>("/alerts?per_page=100"),
        facilitySlug ? getFacilityStaff(facilitySlug) : Promise.resolve([]),
      ]);

      const errors: ResourceErrors<AlertResource> = {};
      addSettledError(errors, "alerts", alertResponse, "Alerts could not be loaded.");
      addSettledError(errors, "staff", staffResponse, "Staff could not be loaded.");

      setAlerts(settledValue(alertResponse, []));
      setStaff(settledValue(staffResponse, []));
      setDataErrors(errors);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts().catch(() => {
      setLoading(false);
    });
  }, []);

  useRealtimeRefresh({
    eventTypes: ["alert.*", "staff.*"],
    onRefresh: () => loadAlerts().catch(() => undefined),
  });

  const createAlert = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!form.title.trim() || !form.message.trim()) {
      setError("Title and message are required.");
      return;
    }

    try {
      const payload = {
        alert_type: form.alert_type,
        title: form.title.trim(),
        message: form.message.trim(),
        expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : undefined,
      };
      if (form.recipient_mode === "role") {
        await apiClient.post<Alert[]>("/alerts/role", {
          ...payload,
          recipient_role: form.recipient_role,
        });
      } else {
        const staffRecipientId = form.recipient_id || staff[0]?.staffRecordId;
        await apiClient.post<Alert>("/alerts", {
          ...payload,
          recipient_id: form.recipient_mode === "staff" ? staffRecipientId : undefined,
        });
      }
      setForm(emptyForm);
      setShowCreate(false);
      await loadAlerts();
    } catch (alertError) {
      setError(alertError instanceof Error ? alertError.message : "Alert creation failed.");
    }
  };

  const toggleRead = async (alert: Alert) => {
    await apiClient.put<Alert>(`/alerts/${alert.id}/${alert.is_read ? "unread" : "read"}`);
    await loadAlerts();
  };

  const markAllRead = async () => {
    await apiClient.put("/alerts/actions/mark-all-read");
    await loadAlerts();
  };

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
            <h1 className="text-2xl font-extrabold tracking-tight">Alerts</h1>
            <p className="text-sm text-muted-foreground">
              Manage facility alerts and staff notifications.
            </p>
          </div>
          <Button
            onClick={() => setShowCreate(true)}
            className="gradient-cta gap-2 border-0 text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> New Alert
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        {hasResourceErrors(dataErrors) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Some alert data could not be loaded. Available sections are still usable.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Alerts" value={String(alerts.length)} icon={Bell} />
          <Metric label="Unread" value={String(summary.unread)} icon={Megaphone} />
          <Metric label="Warnings" value={String(summary.warning)} icon={AlertTriangle} />
          <Metric label="Critical" value={String(summary.critical)} icon={Info} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <CardTitle className="text-base">Notifications</CardTitle>
              <div className="flex flex-col gap-2 sm:flex-row">
                {summary.unread > 0 && (
                  <Button variant="outline" onClick={markAllRead}>
                    Mark all read
                  </Button>
                )}
                <Select value={filter} onValueChange={setFilter}>
                  <SelectTrigger className="w-full sm:w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="unread">Unread</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search alerts"
                    className="w-full pl-9 sm:w-72"
                  />
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading alerts...
              </p>
            ) : visibleAlerts.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-2">
                {visibleAlerts.map((alert, index) => (
                  <motion.div
                    key={alert.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className={`grid gap-3 rounded-xl border p-4 transition-colors hover:border-primary/30 lg:grid-cols-[1fr_.8fr_auto] ${
                      alert.is_read ? "border-border/60" : "border-primary/30 bg-primary/5"
                    }`}
                  >
                    <div>
                      <div className="mb-1 flex flex-wrap items-center gap-2">
                        <SeverityBadge type={alert.alert_type} />
                        {!alert.is_read && (
                          <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground">
                            UNREAD
                          </span>
                        )}
                      </div>
                      <p className="font-semibold text-foreground">{alert.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{alert.message}</p>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <p>{alert.recipient_name || "Facility-wide"}</p>
                      <p className="mt-1 text-xs">
                        {alert.expires_at ? `Expires ${alert.expires_at.slice(0, 10)}` : "No expiry"}
                      </p>
                    </div>
                    <Button variant="outline" onClick={() => toggleRead(alert)}>
                      {alert.is_read ? "Mark Unread" : "Mark Read"}
                    </Button>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Alert</DialogTitle>
            <DialogDescription>Create a facility-wide or staff-specific alert.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createAlert} className="space-y-4 pt-2">
            <SelectField
              label="Severity"
              value={form.alert_type}
              options={[
                { value: "info", label: "Info" },
                { value: "warning", label: "Warning" },
                { value: "critical", label: "Critical" },
              ]}
              onChange={(value) => setForm((current) => ({ ...current, alert_type: value }))}
            />
            <SelectField
              label="Recipient Type"
              value={form.recipient_mode}
              options={[
                { value: "facility", label: "Facility-wide" },
                { value: "role", label: "Role" },
                { value: "staff", label: "Staff member" },
              ]}
              onChange={(value) => setForm((current) => ({ ...current, recipient_mode: value }))}
            />
            {form.recipient_mode === "role" && (
              <SelectField
                label="Role"
                value={form.recipient_role}
                options={[
                  { value: "ADMIN", label: "Admins" },
                  { value: "DOCTOR", label: "Doctors" },
                  { value: "NURSE", label: "Nurses" },
                  { value: "LAB_TECH", label: "Lab staff" },
                  { value: "PHARMACIST", label: "Pharmacists" },
                  { value: "RECEPTIONIST", label: "Receptionists" },
                ]}
                onChange={(value) => setForm((current) => ({ ...current, recipient_role: value }))}
              />
            )}
            {form.recipient_mode === "staff" && (
              <SelectField
                label="Staff Member"
                value={form.recipient_id || staff[0]?.staffRecordId || ""}
                options={staff.map((member) => ({
                  value: member.staffRecordId,
                  label: `${member.fullName} (${member.role})`,
                }))}
                onChange={(value) => setForm((current) => ({ ...current, recipient_id: value }))}
              />
            )}
            <Field label="Title" value={form.title} onChange={(value) => setForm((current) => ({ ...current, title: value }))} required />
            <div>
              <Label>Message *</Label>
              <Textarea
                className="mt-1.5"
                value={form.message}
                onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
                required
              />
            </div>
            <Field label="Expires At" type="datetime-local" value={form.expires_at} onChange={(value) => setForm((current) => ({ ...current, expires_at: value }))} />
            {error && <FormError message={error} />}
            <div className="flex gap-3">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
                Create Alert
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
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
      <Bell className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No alerts found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Create an alert for operational updates.
    </p>
  </div>
);

const SeverityBadge = ({ type }: { type: string }) => {
  const className =
    type === "critical"
      ? "bg-destructive/10 text-destructive"
      : type === "warning"
        ? "bg-amber-500/10 text-amber-700"
        : "bg-primary/10 text-primary";

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${className}`}>
      {type}
    </span>
  );
};

const Field = ({
  label,
  value,
  onChange,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) => (
  <div>
    <Label>
      {label}
      {required ? " *" : ""}
    </Label>
    <Input
      className="mt-1.5"
      type={type}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      required={required}
    />
  </div>
);

const SelectField = ({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) => (
  <div>
    <Label>{label}</Label>
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="mt-1.5">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
);

const FormError = ({ message }: { message: string }) => (
  <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
    {message}
  </p>
);

export default Alerts;
