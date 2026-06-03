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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  completionRate,
  defaultReportRange,
  formatMoney,
  statusSummary,
  type DepartmentActivityReport,
  type DepartmentActivityRow,
  type FacilityReportSummary,
  type InventoryDetailReport,
  type OperationsReport,
  type ReportMetricRow,
  type ReportSection,
  type RevenueDetailReport,
} from "@/lib/reports";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";

type ReportBundle = {
  summary: FacilityReportSummary;
  revenue: RevenueDetailReport | null;
  departments: DepartmentActivityReport;
  operations: OperationsReport;
  inventory: InventoryDetailReport | null;
};

const Reports = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [range, setRange] = useState(() => defaultReportRange());
  const [reports, setReports] = useState<ReportBundle | null>(null);
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

  const loadReports = async () => {
    setLoading(true);
    setError("");
    try {
      const query = new URLSearchParams(range).toString();
      const [summary, revenue, departments, operations, inventory] =
        await Promise.all([
          apiClient.get<FacilityReportSummary>(`/reports/summary?${query}`),
          apiClient.get<RevenueDetailReport>(`/reports/revenue?${query}`).catch(() => null),
          apiClient.get<DepartmentActivityReport>(`/reports/departments?${query}`),
          apiClient.get<OperationsReport>(`/reports/operations?${query}`),
          apiClient.get<InventoryDetailReport>("/reports/inventory").catch(() => null),
        ]);
      setReports({ summary, revenue, departments, operations, inventory });
    } catch (reportError) {
      setError(reportError instanceof Error ? reportError.message : "Reports could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const sections = useMemo(
    () =>
      reports
        ? [
            { label: "Patients", section: reports.summary.patients, icon: Users, to: paths.patients },
            { label: "Appointments", section: reports.summary.appointments, icon: CalendarDays, to: paths.appointments },
            { label: "Queue", section: reports.summary.queue, icon: Activity, to: paths.queue },
            { label: "Consultations", section: reports.summary.consultations, icon: FileHeart, to: paths.consultations },
            { label: "Admissions", section: reports.summary.admissions, icon: BedDouble, to: paths.wards },
            { label: "Laboratory", section: reports.summary.laboratory, icon: FlaskConical, to: paths.laboratory },
            { label: "Radiology", section: reports.summary.radiology, icon: ScanLine, to: paths.radiology },
            { label: "Alerts", section: reports.summary.alerts, icon: Bell, to: paths.audit },
          ]
        : [],
    [paths, reports]
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
              Revenue, department activity, operations, and inventory performance.
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
                    : reports?.summary.generated_at
                      ? `Generated ${new Date(reports.summary.generated_at).toLocaleString()}`
                      : "Choose a date range"}
                </p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
              <DateField label="From" value={range.date_from} onChange={(value) => setRange((current) => ({ ...current, date_from: value }))} />
              <DateField label="To" value={range.date_to} onChange={(value) => setRange((current) => ({ ...current, date_to: value }))} />
              <Button onClick={loadReports} disabled={loading} className="gradient-cta gap-2 border-0 text-primary-foreground">
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

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 md:grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="revenue">Revenue</TabsTrigger>
            <TabsTrigger value="departments">Departments</TabsTrigger>
            <TabsTrigger value="operations">Operations</TabsTrigger>
            <TabsTrigger value="inventory">Inventory</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {sections.map((item) => (
                <ReportMetric key={item.label} {...item} />
              ))}
            </div>
            {reports && (
              <div className="grid gap-6 lg:grid-cols-3">
                {reports.revenue ? (
                  <RevenueCard revenue={reports.revenue} billingPath={paths.billing} />
                ) : (
                  <UnavailableCard title="Revenue" message="Revenue reporting is limited to billing users and admins." />
                )}
                {reports.inventory ? (
                  <InventoryCard inventory={reports.inventory} inventoryPath={paths.inventory} />
                ) : (
                  <UnavailableCard title="Inventory" message="Inventory reporting is limited to inventory users and admins." />
                )}
                <ClinicalCard departments={reports.departments.departments} consultationsPath={paths.consultations} />
              </div>
            )}
          </TabsContent>

          <TabsContent value="revenue">
            {reports && (
              reports.revenue ? (
                <RevenuePanel revenue={reports.revenue} billingPath={paths.billing} />
              ) : (
                <UnavailablePanel title="Revenue reporting" message="Your current role cannot access revenue detail reports." />
              )
            )}
          </TabsContent>

          <TabsContent value="departments">
            {reports && <DepartmentPanel rows={reports.departments.departments} />}
          </TabsContent>

          <TabsContent value="operations">
            {reports && <OperationsPanel operations={reports.operations} />}
          </TabsContent>

          <TabsContent value="inventory">
            {reports && (
              reports.inventory ? (
                <InventoryPanel inventory={reports.inventory} inventoryPath={paths.inventory} />
              ) : (
                <UnavailablePanel title="Inventory reporting" message="Your current role cannot access inventory detail reports." />
              )
            )}
          </TabsContent>
        </Tabs>
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

const RevenueCard = ({ revenue, billingPath }: { revenue: RevenueDetailReport; billingPath: string }) => (
  <Card className="border-border/60">
    <CardHeader>
      <CardTitle className="text-base">Revenue</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      <MoneyRow label="Invoiced" value={revenue.invoiced_total} />
      <MoneyRow label="Collected" value={revenue.collected_total} />
      <MoneyRow label="Outstanding" value={revenue.outstanding_total} strong />
      <InfoRow label="Receipts" value={String(revenue.receipt_count)} />
      <Button asChild variant="outline" className="w-full gap-2">
        <Link to={billingPath}>
          <Receipt className="h-4 w-4" /> Billing
        </Link>
      </Button>
    </CardContent>
  </Card>
);

const InventoryCard = ({ inventory, inventoryPath }: { inventory: InventoryDetailReport; inventoryPath: string }) => (
  <Card className="border-border/60">
    <CardHeader>
      <CardTitle className="text-base">Inventory</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      <InfoRow label="Active Items" value={String(inventory.active_items)} />
      <InfoRow label="Low Stock" value={String(inventory.low_stock_items)} />
      <MoneyRow label="Stock Value" value={inventory.stock_value} strong />
      <Button asChild variant="outline" className="w-full gap-2">
        <Link to={inventoryPath}>
          <Package className="h-4 w-4" /> Inventory
        </Link>
      </Button>
    </CardContent>
  </Card>
);

const ClinicalCard = ({ departments, consultationsPath }: { departments: DepartmentActivityRow[]; consultationsPath: string }) => (
  <Card className="border-border/60">
    <CardHeader>
      <CardTitle className="text-base">Clinical Throughput</CardTitle>
    </CardHeader>
    <CardContent className="space-y-3">
      {departments.slice(0, 4).map((row) => (
        <InfoRow key={row.department} label={row.department} value={String(row.total)} />
      ))}
      <Button asChild variant="outline" className="w-full gap-2">
        <Link to={consultationsPath}>
          <FileHeart className="h-4 w-4" /> Consultations
        </Link>
      </Button>
    </CardContent>
  </Card>
);

const UnavailableCard = ({ title, message }: { title: string; message: string }) => (
  <Card className="border-border/60">
    <CardHeader>
      <CardTitle className="text-base">{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-muted-foreground">{message}</p>
    </CardContent>
  </Card>
);

const UnavailablePanel = ({ title, message }: { title: string; message: string }) => (
  <Card className="border-border/60">
    <CardHeader>
      <CardTitle className="text-base">{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <p className="py-8 text-center text-sm text-muted-foreground">{message}</p>
    </CardContent>
  </Card>
);

const RevenuePanel = ({ revenue, billingPath }: { revenue: RevenueDetailReport; billingPath: string }) => (
  <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-base">Revenue Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <MoneyRow label="Invoiced" value={revenue.invoiced_total} />
        <MoneyRow label="Collected" value={revenue.collected_total} />
        <MoneyRow label="Outstanding" value={revenue.outstanding_total} strong />
        <InfoRow label="Invoices" value={String(revenue.invoice_count)} />
        <InfoRow label="Paid Invoices" value={String(revenue.paid_invoice_count)} />
        <InfoRow label="Receipts Uploaded" value={String(revenue.receipt_count)} />
        <Button asChild variant="outline" className="w-full gap-2">
          <Link to={billingPath}>
            <Receipt className="h-4 w-4" /> Open Billing
          </Link>
        </Button>
      </CardContent>
    </Card>
    <div className="space-y-6">
      <MetricTable title="Payment Methods" rows={revenue.payment_methods} money />
      <MetricTable title="Invoice Statuses" rows={revenue.invoice_statuses} />
      <MetricTable title="Recent Payments" rows={revenue.recent_payments} money />
    </div>
  </div>
);

const DepartmentPanel = ({ rows }: { rows: DepartmentActivityRow[] }) => (
  <Card className="border-border/60">
    <CardHeader>
      <CardTitle className="text-base">Department Activity</CardTitle>
    </CardHeader>
    <CardContent className="space-y-2">
      {rows.map((row) => (
        <div key={row.department} className="grid gap-3 rounded-xl border border-border/60 p-4 md:grid-cols-[1fr_.6fr_.6fr_.6fr_.8fr]">
          <div>
            <p className="font-semibold text-foreground">{row.department}</p>
            <p className="text-xs text-muted-foreground">{statusSummary({ total: row.total, by_status: row.by_status }) || "No activity"}</p>
          </div>
          <InfoRow label="Total" value={String(row.total)} />
          <InfoRow label="Done" value={String(row.completed)} />
          <InfoRow label="Open" value={String(row.pending)} />
          <InfoRow label="Rate" value={`${completionRate(row.completed, row.total)}%`} />
        </div>
      ))}
    </CardContent>
  </Card>
);

const OperationsPanel = ({ operations }: { operations: OperationsReport }) => (
  <div className="grid gap-6 lg:grid-cols-2">
    <MetricTable title="Active Tasks By Role" rows={operations.active_tasks_by_role} />
    <MetricTable title="High Priority Tasks" rows={operations.high_priority_tasks} />
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-base">Queue</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-extrabold">{operations.queue.total}</p>
        <p className="text-sm capitalize text-muted-foreground">{statusSummary(operations.queue) || "No queue activity"}</p>
      </CardContent>
    </Card>
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-base">Appointments</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-extrabold">{operations.appointments.total}</p>
        <p className="text-sm capitalize text-muted-foreground">{statusSummary(operations.appointments) || "No appointment activity"}</p>
      </CardContent>
    </Card>
  </div>
);

const InventoryPanel = ({ inventory, inventoryPath }: { inventory: InventoryDetailReport; inventoryPath: string }) => (
  <div className="grid gap-6 lg:grid-cols-[.8fr_1.2fr]">
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-base">Inventory Value</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <InfoRow label="Active Items" value={String(inventory.active_items)} />
        <InfoRow label="Low Stock" value={String(inventory.low_stock_items)} />
        <MoneyRow label="Stock Value" value={inventory.stock_value} strong />
        <MetricTable title="By Category" rows={inventory.by_category} money />
        <Button asChild variant="outline" className="w-full gap-2">
          <Link to={inventoryPath}>
            <Package className="h-4 w-4" /> Open Inventory
          </Link>
        </Button>
      </CardContent>
    </Card>
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-base">Reorder List</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {inventory.reorder_items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No low-stock items.</p>
        ) : (
          inventory.reorder_items.map((item) => (
            <div key={item.id} className="grid gap-2 rounded-xl border border-border/60 p-3 md:grid-cols-[1fr_.5fr_.5fr_.7fr]">
              <div>
                <p className="font-semibold text-foreground">{item.name}</p>
                <p className="text-xs text-muted-foreground">{item.sku} · {item.supplier_name || "No supplier"}</p>
              </div>
              <InfoRow label="Stock" value={`${item.current_stock} ${item.unit}`} />
              <InfoRow label="Reorder" value={String(item.reorder_quantity)} />
              <MoneyRow label="Value" value={item.stock_value} />
            </div>
          ))
        )}
      </CardContent>
    </Card>
  </div>
);

const MetricTable = ({ title, rows, money }: { title: string; rows: ReportMetricRow[]; money?: boolean }) => (
  <Card className="border-border/60">
    <CardHeader>
      <CardTitle className="text-base">{title}</CardTitle>
    </CardHeader>
    <CardContent className="space-y-2">
      {rows.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">No rows for this period.</p>
      ) : (
        rows.map((row, index) => (
          <div key={`${row.label}-${index}`} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 px-3 py-2 text-sm">
            <div>
              <p className="font-medium text-foreground">{row.label}</p>
              {row.metadata && Object.keys(row.metadata).length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {Object.entries(row.metadata)
                    .filter(([, value]) => value !== null && value !== undefined && value !== false)
                    .slice(0, 3)
                    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`)
                    .join(" · ")}
                </p>
              )}
            </div>
            <span className="font-bold text-foreground">{money ? formatMoney(row.value) : row.value}</span>
          </div>
        ))
      )}
    </CardContent>
  </Card>
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
