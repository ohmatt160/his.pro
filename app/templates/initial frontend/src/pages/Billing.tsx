import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Banknote,
  CalendarDays,
  CreditCard,
  Download,
  FileImage,
  Plus,
  Receipt,
  Search,
  Users,
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
import { getWorkspaceDashboardPath, getWorkspaceRoutePath } from "@/lib/facility-workspace";
import {
  addSettledError,
  hasResourceErrors,
  settledValue,
  type ResourceErrors,
} from "@/lib/resource-loading";

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
};

type PatientListResponse = {
  patients: Patient[];
  total: number;
};

type Invoice = {
  id: string;
  patient_id: string;
  invoice_number: string;
  amount: number;
  paid_amount: number;
  balance: number;
  status: "PENDING" | "PARTIAL" | "PAID" | "CANCELLED" | string;
  due_date: string;
  paid_date?: string | null;
  notes?: string | null;
  payments?: Payment[];
  created_at: string;
};

type Payment = {
  id: string;
  invoice_id: string;
  amount: number;
  payment_method: PaymentMethod | string;
  reference?: string | null;
  notes?: string | null;
  has_receipt: boolean;
  receipt_original_name?: string | null;
  receipt_content_type?: string | null;
  receipt_size?: number | null;
  receipt_uploaded_at?: string | null;
  receipt_url?: string | null;
  created_at: string;
};

type PaymentMethod = "CASH" | "CARD" | "TRANSFER" | "INSURANCE";

type BillingResource = "patients" | "invoices";

const emptyInvoiceForm = {
  patient_id: "",
  amount: "",
  due_date: "",
  notes: "",
};

const emptyPaymentForm = {
  amount: "",
  payment_method: "CASH" as PaymentMethod,
  reference: "",
  notes: "",
};

const paymentMethods: PaymentMethod[] = ["CASH", "CARD", "TRANSFER", "INSURANCE"];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value || 0);

const Billing = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [paymentsByInvoice, setPaymentsByInvoice] = useState<Record<string, Payment[]>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showInvoiceDialog, setShowInvoiceDialog] = useState(false);
  const [payingInvoice, setPayingInvoice] = useState<Invoice | null>(null);
  const [invoiceForm, setInvoiceForm] = useState(emptyInvoiceForm);
  const [paymentForm, setPaymentForm] = useState(emptyPaymentForm);
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<ResourceErrors<BillingResource>>({});

  const dashboardPath = getWorkspaceDashboardPath(facilitySlug, branchSlug || undefined);

  const patientNames = useMemo(() => {
    return patients.reduce<Record<string, string>>((acc, patient) => {
      acc[patient.id] =
        patient.full_name || `${patient.first_name} ${patient.last_name}`.trim();
      return acc;
    }, {});
  }, [patients]);

  const visibleInvoices = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return invoices;
    }

    return invoices.filter((invoice) => {
      const patientName = patientNames[invoice.patient_id] || "";
      return (
        invoice.invoice_number.toLowerCase().includes(query) ||
        invoice.status.toLowerCase().includes(query) ||
        patientName.toLowerCase().includes(query)
      );
    });
  }, [invoices, patientNames, search]);

  const totals = useMemo(() => {
    return invoices.reduce(
      (acc, invoice) => ({
        billed: acc.billed + invoice.amount,
        paid: acc.paid + invoice.paid_amount,
        outstanding: acc.outstanding + invoice.balance,
      }),
      { billed: 0, paid: 0, outstanding: 0 }
    );
  }, [invoices]);

  const loadBilling = async () => {
    setLoading(true);
    try {
      const [patientResponse, invoiceResponse] = await Promise.allSettled([
        apiClient.get<PatientListResponse>("/patients?page=1&per_page=100"),
        apiClient.get<Invoice[]>("/billing/invoices"),
      ]);

      const errors: ResourceErrors<BillingResource> = {};
      addSettledError(errors, "patients", patientResponse, "Patients could not be loaded.");
      addSettledError(errors, "invoices", invoiceResponse, "Invoices could not be loaded.");

      const nextPatients = settledValue(patientResponse, { patients: [], total: 0 }).patients;
      const nextInvoices = settledValue(invoiceResponse, []);

      setPatients(nextPatients);
      setInvoices(nextInvoices);
      setPaymentsByInvoice(
        Object.fromEntries(
          nextInvoices.map((invoice) => [invoice.id, invoice.payments ?? []])
        )
      );
      setDataErrors(errors);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBilling().catch(() => {
      setLoading(false);
    });
  }, []);

  const createInvoice = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    const amount = Number(invoiceForm.amount);
    if (!invoiceForm.patient_id || !invoiceForm.due_date || !amount || amount <= 0) {
      setError("Patient, due date, and a valid amount are required.");
      return;
    }

    try {
      await apiClient.post<Invoice>("/billing/invoices", {
        patient_id: invoiceForm.patient_id,
        amount,
        due_date: invoiceForm.due_date,
        notes: invoiceForm.notes.trim() || undefined,
      });
      setInvoiceForm(emptyInvoiceForm);
      setShowInvoiceDialog(false);
      await loadBilling();
    } catch (invoiceError) {
      setError(
        invoiceError instanceof Error
          ? invoiceError.message
          : "Invoice creation failed."
      );
    }
  };

  const recordPayment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!payingInvoice) {
      return;
    }

    setError("");
    const amount = Number(paymentForm.amount);
    if (!amount || amount <= 0) {
      setError("Enter a valid payment amount.");
      return;
    }
    if (amount > payingInvoice.balance) {
      setError("Payment cannot be greater than the invoice balance.");
      return;
    }

    try {
      const payment = await apiClient.post<Payment>(`/billing/invoices/${payingInvoice.id}/payments`, {
        amount,
        payment_method: paymentForm.payment_method,
        reference: paymentForm.reference.trim() || undefined,
        notes: paymentForm.notes.trim() || undefined,
      });
      if (receiptFile) {
        const formData = new FormData();
        formData.append("file", receiptFile);
        await apiClient.request(`/billing/payments/${payment.id}/receipt`, {
          method: "POST",
          body: formData,
        });
      }
      setPaymentForm(emptyPaymentForm);
      setReceiptFile(null);
      setPayingInvoice(null);
      await loadBilling();
    } catch (paymentError) {
      setError(
        paymentError instanceof Error ? paymentError.message : "Payment failed."
      );
    }
  };

  const downloadReceipt = async (payment: Payment) => {
    if (!payment.receipt_url) {
      return;
    }

    try {
      const blob = await apiClient.downloadBlob(payment.receipt_url);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = payment.receipt_original_name || `receipt-${payment.id}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (receiptError) {
      setError(receiptError instanceof Error ? receiptError.message : "Receipt download failed.");
    }
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
            <h1 className="text-2xl font-extrabold tracking-tight">
              Billing & Payments
            </h1>
            <p className="text-sm text-muted-foreground">
              Create patient invoices and record payments.
            </p>
          </div>
          <Button
            onClick={() => {
              setError("");
              setShowInvoiceDialog(true);
            }}
            className="gradient-cta gap-2 border-0 text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> New Invoice
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        {hasResourceErrors(dataErrors) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Some billing data could not be loaded. Available sections are still usable.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Invoices" value={String(invoices.length)} icon={Receipt} />
          <Metric label="Total Billed" value={formatCurrency(totals.billed)} icon={Banknote} />
          <Metric label="Collected" value={formatCurrency(totals.paid)} icon={CreditCard} />
          <Metric label="Outstanding" value={formatCurrency(totals.outstanding)} icon={CalendarDays} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-base">Invoices</CardTitle>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search invoice, patient, status"
                  className="w-full pl-9 sm:w-72"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading billing records...
              </p>
            ) : visibleInvoices.length === 0 ? (
              <div className="py-16 text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
                  <Receipt className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="font-semibold text-foreground">No invoices found</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Create an invoice after registering a patient.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {visibleInvoices.map((invoice, index) => (
                  <motion.div key={invoice.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.03 }} className="rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30">
                    <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr_.8fr_.8fr_auto]">
                      <div>
                        <p className="font-semibold text-foreground">{invoice.invoice_number}</p>
                        <p className="text-xs text-muted-foreground">{patientNames[invoice.patient_id] || "Unknown patient"}</p>
                      </div>
                      <Info icon={CalendarDays} value={`Due ${invoice.due_date || "not set"}`} />
                      <div>
                        <p className="text-sm font-semibold">{formatCurrency(invoice.amount)}</p>
                        <p className="text-xs text-muted-foreground">Paid {formatCurrency(invoice.paid_amount)}</p>
                      </div>
                      <div>
                        <StatusBadge status={invoice.status} />
                        <p className="mt-1 text-xs text-muted-foreground">Balance {formatCurrency(invoice.balance)}</p>
                      </div>
                      <Button
                        variant="outline"
                        disabled={invoice.balance <= 0 || invoice.status === "CANCELLED"}
                        onClick={() => {
                          setError("");
                          setReceiptFile(null);
                          setPaymentForm({ ...emptyPaymentForm, amount: String(invoice.balance) });
                          setPayingInvoice(invoice);
                        }}
                      >
                        Record Payment
                      </Button>
                    </div>
                    {Boolean(paymentsByInvoice[invoice.id]?.length) && (
                      <div className="mt-3 space-y-2 border-t border-border/60 pt-3">
                        {paymentsByInvoice[invoice.id].map((payment) => (
                          <div key={payment.id} className="flex flex-col gap-2 rounded-lg bg-muted/40 px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between">
                            <div>
                              <p className="font-medium text-foreground">
                                {formatCurrency(payment.amount)} · {payment.payment_method}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {payment.reference || "No reference"} · {new Date(payment.created_at).toLocaleString()}
                              </p>
                            </div>
                            {payment.has_receipt ? (
                              <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => downloadReceipt(payment)}>
                                <Download className="h-4 w-4" /> Receipt
                              </Button>
                            ) : (
                              <span className="text-xs text-muted-foreground">No receipt</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button asChild variant="outline" className="gap-2">
            <Link to={getWorkspaceRoutePath(facilitySlug, "patients", branchSlug || undefined)}>
              <Users className="h-4 w-4" /> Patient Registry
            </Link>
          </Button>
        </div>
      </main>

      <Dialog open={showInvoiceDialog} onOpenChange={setShowInvoiceDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Invoice</DialogTitle>
            <DialogDescription>
              Create an invoice for a registered patient.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={createInvoice} className="space-y-4 pt-2">
            <div>
              <Label>Patient *</Label>
              <Select
                value={invoiceForm.patient_id}
                onValueChange={(value) =>
                  setInvoiceForm((current) => ({ ...current, patient_id: value }))
                }
              >
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Select patient" />
                </SelectTrigger>
                <SelectContent>
                  {patients.map((patient) => (
                    <SelectItem key={patient.id} value={patient.id}>
                      {patientNames[patient.id]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field
              label="Amount"
              type="number"
              value={invoiceForm.amount}
              onChange={(value) =>
                setInvoiceForm((current) => ({ ...current, amount: value }))
              }
              required
            />
            <Field
              label="Due Date"
              type="date"
              value={invoiceForm.due_date}
              onChange={(value) =>
                setInvoiceForm((current) => ({ ...current, due_date: value }))
              }
              required
            />
            <Field
              label="Notes"
              value={invoiceForm.notes}
              onChange={(value) =>
                setInvoiceForm((current) => ({ ...current, notes: value }))
              }
            />
            <div>
              <Label>Receipt Image</Label>
              <Input
                className="mt-1.5"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(event) => setReceiptFile(event.target.files?.[0] || null)}
              />
              {receiptFile && (
                <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                  <FileImage className="h-3.5 w-3.5" /> {receiptFile.name}
                </p>
              )}
            </div>
            {error && <FormError message={error} />}
            <div className="flex gap-3">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setShowInvoiceDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
                Create Invoice
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(payingInvoice)} onOpenChange={(open) => !open && setPayingInvoice(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Payment</DialogTitle>
            <DialogDescription>
              {payingInvoice
                ? `${payingInvoice.invoice_number} balance is ${formatCurrency(payingInvoice.balance)}.`
                : "Record payment for this invoice."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={recordPayment} className="space-y-4 pt-2">
            <Field
              label="Amount"
              type="number"
              value={paymentForm.amount}
              onChange={(value) =>
                setPaymentForm((current) => ({ ...current, amount: value }))
              }
              required
            />
            <div>
              <Label>Payment Method</Label>
              <Select
                value={paymentForm.payment_method}
                onValueChange={(value) =>
                  setPaymentForm((current) => ({
                    ...current,
                    payment_method: value as PaymentMethod,
                  }))
                }
              >
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {paymentMethods.map((method) => (
                    <SelectItem key={method} value={method}>
                      {method}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field
              label="Reference"
              value={paymentForm.reference}
              onChange={(value) =>
                setPaymentForm((current) => ({ ...current, reference: value }))
              }
            />
            <Field
              label="Notes"
              value={paymentForm.notes}
              onChange={(value) =>
                setPaymentForm((current) => ({ ...current, notes: value }))
              }
            />
            {error && <FormError message={error} />}
            <div className="flex gap-3">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setPayingInvoice(null)}>
                Cancel
              </Button>
              <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
                Save Payment
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

const Info = ({ icon: Icon, value }: { icon: React.ElementType; value: string }) => (
  <span className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
    <Icon className="h-4 w-4 shrink-0" />
    <span className="truncate">{value}</span>
  </span>
);

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
      min={type === "number" ? "0" : undefined}
      step={type === "number" ? "0.01" : undefined}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      required={required}
    />
  </div>
);

const StatusBadge = ({ status }: { status: string }) => {
  const variant =
    status === "PAID"
      ? "bg-emerald-500/10 text-emerald-700"
      : status === "PARTIAL"
        ? "bg-amber-500/10 text-amber-700"
        : status === "CANCELLED"
          ? "bg-destructive/10 text-destructive"
          : "bg-primary/10 text-primary";

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${variant}`}>
      {status}
    </span>
  );
};

const FormError = ({ message }: { message: string }) => (
  <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
    {message}
  </p>
);

export default Billing;
