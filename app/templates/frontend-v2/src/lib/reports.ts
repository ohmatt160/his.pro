export type ReportSection = {
  total: number;
  by_status: Record<string, number>;
};

export type FacilityReportSummary = {
  facility_slug: string;
  date_from: string;
  date_to: string;
  patients: ReportSection;
  appointments: ReportSection;
  consultations: ReportSection;
  admissions: ReportSection;
  queue: ReportSection;
  laboratory: ReportSection;
  radiology: ReportSection;
  billing: {
    invoice_count: number;
    outstanding_invoice_count: number;
    invoiced_total: number;
    payments_total: number;
    outstanding_total: number;
  };
  inventory: {
    active_items: number;
    low_stock_items: number;
    stock_value: number;
  };
  alerts: ReportSection;
  generated_at: string;
};

export type ReportMetricRow = {
  label: string;
  value: number;
  metadata: Record<string, unknown>;
};

export type RevenueDetailReport = {
  facility_slug: string;
  date_from: string;
  date_to: string;
  invoice_count: number;
  paid_invoice_count: number;
  outstanding_invoice_count: number;
  invoiced_total: number;
  collected_total: number;
  outstanding_total: number;
  receipt_count: number;
  payment_methods: ReportMetricRow[];
  invoice_statuses: ReportMetricRow[];
  recent_payments: ReportMetricRow[];
  generated_at: string;
};

export type DepartmentActivityRow = {
  department: string;
  module: string;
  total: number;
  completed: number;
  pending: number;
  by_status: Record<string, number>;
};

export type DepartmentActivityReport = {
  facility_slug: string;
  date_from: string;
  date_to: string;
  departments: DepartmentActivityRow[];
  generated_at: string;
};

export type OperationsReport = {
  facility_slug: string;
  date_from: string;
  date_to: string;
  queue: ReportSection;
  appointments: ReportSection;
  active_tasks_by_role: ReportMetricRow[];
  high_priority_tasks: ReportMetricRow[];
  generated_at: string;
};

export type InventoryDetailItem = {
  id: string;
  name: string;
  sku: string;
  category: string;
  current_stock: number;
  reorder_level: number;
  reorder_quantity: number;
  unit: string;
  stock_value: number;
  supplier_name?: string | null;
};

export type InventoryDetailReport = {
  facility_slug: string;
  active_items: number;
  low_stock_items: number;
  stock_value: number;
  reorder_items: InventoryDetailItem[];
  by_category: ReportMetricRow[];
  generated_at: string;
};

export const defaultReportRange = (today = new Date()) => {
  const end = new Date(today);
  const start = new Date(today);
  start.setDate(start.getDate() - 30);

  return {
    date_from: start.toISOString().slice(0, 10),
    date_to: end.toISOString().slice(0, 10),
  };
};

export const formatMoney = (value: number) =>
  new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(value);

export const statusSummary = (section: ReportSection) =>
  Object.entries(section.by_status)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([status, count]) => `${status.replaceAll("_", " ")}: ${count}`)
    .join(" · ");

export const completionRate = (completed: number, total: number) =>
  total > 0 ? Math.round((completed / total) * 100) : 0;
