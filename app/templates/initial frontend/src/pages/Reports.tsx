import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  BarChart3,
  BedDouble,
  Bell,
  CalendarDays,
  ClipboardList,
  FileHeart,
  FlaskConical,
  Package,
  Receipt,
  ScanLine,
  TrendingUp,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  defaultReportRange,
  formatMoney,
  statusSummary,
  type FacilityReportSummary,
  type ReportSection,
} from "@/lib/reports";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";

const Reports = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [range, setRange] = useState(() => defaultReportRange());
  const [summary, setSummary] = useState<FacilityReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const paths = {
    patients: `/dashboard/${facilitySlug}/patients`,
    appointments: `/dashboard/${facilitySlug}/appointments`,
    queue: `/dashboard/${facilitySlug}/queue`,
    consultations: `/dashboard/${facilitySlug}/consultations`,
    wards: `/dashboard/${facilitySlug}/wards`,
    laboratory: `/dashboard/${facilitySlug}/laboratory`,
    radiology: `/dashboard/${facilitySlug}/radiology`,
    inventory: `/dashboard/${facilitySlug}/inventory`,
    billing: `/dashboard/${facilitySlug}/billing`,
    audit: `/dashboard/${facilitySlug}/audit-logs`,
  };

  const loadSummary = async () => {
    setLoading(true);
    setError("");
    try {
      const query = new URLSearchParams(range).toString();
      setSummary(await apiClient.get<FacilityReportSummary>(`/reports/summary?${query}`));
    } catch (reportError) {
      setError(reportError instanceof Error ? reportError.message : "Reports could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const sections = useMemo(
    () =>
      summary
        ? [
            { label: "Patients", section: summary.patients, icon: Users, to: paths.patients },
            { label: "Appointments", section: summary.appointments, icon: CalendarDays, to: paths.appointments },
            { label: "Queue", section: summary.queue, icon: Activity, to: paths.queue },
            { label: "Consultations", section: summary.consultations, icon: FileHeart, to: paths.consultations },
            { label: "Admissions", section: summary.admissions, icon: BedDouble, to: paths.wards },
            { label: "Laboratory", section: summary.laboratory, icon: FlaskConical, to: paths.laboratory },
            { label: "Radiology", section: summary.radiology, icon: ScanLine, to: paths.radiology },
            { label: "Alerts", section: summary.alerts, icon: Bell, to: paths.audit },
          ]
        : [],
    [paths, summary]
  );

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
            <h1 className="text-2xl font-extrabold tracking-tight">Reports & Analytics</h1>
            <p className="text-sm text-muted-foreground">
              Review operational, clinical, billing, and inventory performance.
            </p>
          </div>
          <Button asChild variant="outline" className="gap-2">
            <Link to={paths.audit}>
              <ClipboardList className="h-4 w-4" /> Audit Logs
            </Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <Card className="border-border/60">
          <CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
                <BarChart3 className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-semibold text-foreground">Facility Report</p>
                <p className="text-sm text-muted-foreground">
                  {loading
                    ? "Loading report..."
                    : summary?.generated_at
                      ? `Generated ${new Date(summary.generated_at).toLocaleString()}`
                      : "Choose a date range"}
                </p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
              <DateField label="From" value={range.date_from} onChange={(value) => setRange((current) => ({ ...current, date_from: value }))} />
              <DateField label="To" value={range.date_to} onChange={(value) => setRange((current) => ({ ...current, date_to: value }))} />
              <Button onClick={loadSummary} disabled={loading} className="gradient-cta gap-2 border-0 text-primary-foreground">
                <TrendingUp className="h-4 w-4" /> Run
              </Button>
            </div>
          </CardContent>
        </Card>

        {error && (
          <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {sections.map((item) => (
            <ReportMetric key={item.label} {...item} />
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Revenue</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <MoneyRow label="Invoiced" value={summary?.billing.invoiced_total || 0} />
              <MoneyRow label="Payments" value={summary?.billing.payments_total || 0} />
              <MoneyRow label="Outstanding" value={summary?.billing.outstanding_total || 0} strong />
              <div className="rounded-xl border border-border/60 p-3 text-sm text-muted-foreground">
                {summary?.billing.invoice_count || 0} invoices ·{" "}
                {summary?.billing.outstanding_invoice_count || 0} outstanding
              </div>
              <Button asChild variant="outline" className="w-full gap-2">
                <Link to={paths.billing}>
                  <Receipt className="h-4 w-4" /> Billing
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Inventory</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <InfoRow label="Active Items" value={String(summary?.inventory.active_items || 0)} />
              <InfoRow label="Low Stock" value={String(summary?.inventory.low_stock_items || 0)} />
              <MoneyRow label="Stock Value" value={summary?.inventory.stock_value || 0} strong />
              <Button asChild variant="outline" className="w-full gap-2">
                <Link to={paths.inventory}>
                  <Package className="h-4 w-4" /> Inventory
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Clinical Throughput</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow label="Consultations" value={String(summary?.consultations.total || 0)} />
              <InfoRow label="Admissions" value={String(summary?.admissions.total || 0)} />
              <InfoRow label="Lab Orders" value={String(summary?.laboratory.total || 0)} />
              <InfoRow label="Radiology Orders" value={String(summary?.radiology.total || 0)} />
              <Button asChild variant="outline" className="w-full gap-2">
                <Link to={paths.consultations}>
                  <FileHeart className="h-4 w-4" /> Consultations
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

const ReportMetric = ({
  label,
  section,
  icon: Icon,
  to,
}: {
  label: string;
  section: ReportSection;
  icon: React.ElementType;
  to: string;
}) => (
  <Link to={to}>
    <Card className="h-full border-border/60 transition-all hover:border-primary/30 hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <span className="text-[11px] font-medium text-muted-foreground">Open</span>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-extrabold text-foreground">{section.total}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-2 line-clamp-2 text-xs capitalize text-muted-foreground">
          {statusSummary(section) || "No activity"}
        </p>
      </CardContent>
    </Card>
  </Link>
);

const DateField = ({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) => (
  <div>
    <Label>{label}</Label>
    <Input className="mt-1.5" type="date" value={value} onChange={(event) => onChange(event.target.value)} />
  </div>
);

const MoneyRow = ({ label, value, strong }: { label: string; value: number; strong?: boolean }) => (
  <div className="flex items-center justify-between gap-3">
    <span className="text-sm text-muted-foreground">{label}</span>
    <span className={strong ? "font-extrabold text-foreground" : "font-semibold text-foreground"}>
      {formatMoney(value)}
    </span>
  </div>
);

const InfoRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-center justify-between gap-3">
    <span className="text-sm text-muted-foreground">{label}</span>
    <span className="font-semibold text-foreground">{value}</span>
  </div>
);

export default Reports;
