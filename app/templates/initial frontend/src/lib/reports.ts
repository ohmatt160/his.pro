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
