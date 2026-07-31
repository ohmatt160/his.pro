import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Building2,
  Mail,
  Phone,
  Plus,
  Search,
  Truck,
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
import { Textarea } from "@/components/ui/textarea";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";

type Supplier = {
  id: string;
  facility_slug: string;
  name: string;
  contact_person?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  is_active: boolean;
  created_at: string;
};

const emptyForm = {
  name: "",
  contact_person: "",
  email: "",
  phone: "",
  address: "",
};

const Suppliers = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useTenantParams();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");

  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const visibleSuppliers = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return suppliers;
    }
    return suppliers.filter((supplier) =>
      [
        supplier.name,
        supplier.contact_person || "",
        supplier.email || "",
        supplier.phone || "",
      ]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [search, suppliers]);

  const loadSuppliers = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<Supplier[]>("/suppliers");
      setSuppliers(response);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuppliers().catch(() => {
      setSuppliers([]);
      setLoading(false);
    });
  }, []);

  const createSupplier = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!form.name.trim()) {
      setError("Supplier name is required.");
      return;
    }

    try {
      await apiClient.post<Supplier>("/suppliers", {
        name: form.name.trim(),
        contact_person: form.contact_person.trim() || undefined,
        email: form.email.trim() || undefined,
        phone: form.phone.trim() || undefined,
        address: form.address.trim() || undefined,
      });
      setForm(emptyForm);
      setShowCreate(false);
      await loadSuppliers();
    } catch (supplierError) {
      setError(
        supplierError instanceof Error
          ? supplierError.message
          : "Supplier creation failed."
      );
    }
  };

  const deactivateSupplier = async (supplier: Supplier) => {
    await apiClient.del(`/suppliers/${supplier.id}`);
    await loadSuppliers();
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
            <h1 className="text-2xl font-extrabold tracking-tight">Suppliers</h1>
            <p className="text-sm text-muted-foreground">
              Manage vendors used by inventory and procurement.
            </p>
          </div>
          <Button
            onClick={() => setShowCreate(true)}
            className="gradient-cta gap-2 border-0 text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> New Supplier
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <Metric label="Active Suppliers" value={String(suppliers.length)} icon={Truck} />
          <Metric label="Contacts" value={String(suppliers.filter((supplier) => supplier.contact_person).length)} icon={Users} />
          <Metric label="Email Ready" value={String(suppliers.filter((supplier) => supplier.email).length)} icon={Mail} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-base">Supplier Directory</CardTitle>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search suppliers"
                  className="w-full pl-9 sm:w-72"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading suppliers...
              </p>
            ) : visibleSuppliers.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {visibleSuppliers.map((supplier, index) => (
                  <motion.div
                    key={supplier.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className="rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30"
                  >
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-foreground">{supplier.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {supplier.contact_person || "No contact person"}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => deactivateSupplier(supplier)}
                      >
                        Deactivate
                      </Button>
                    </div>
                    <div className="space-y-2">
                      <Info icon={Mail} value={supplier.email || "No email"} />
                      <Info icon={Phone} value={supplier.phone || "No phone"} />
                      <Info icon={Building2} value={supplier.address || "No address"} />
                    </div>
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
            <DialogTitle>New Supplier</DialogTitle>
            <DialogDescription>Add a vendor for this facility.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createSupplier} className="space-y-4 pt-2">
            <Field label="Name" value={form.name} onChange={(value) => setForm((current) => ({ ...current, name: value }))} required />
            <Field label="Contact Person" value={form.contact_person} onChange={(value) => setForm((current) => ({ ...current, contact_person: value }))} />
            <Field label="Email" type="email" value={form.email} onChange={(value) => setForm((current) => ({ ...current, email: value }))} />
            <Field label="Phone" value={form.phone} onChange={(value) => setForm((current) => ({ ...current, phone: value }))} />
            <div>
              <Label>Address</Label>
              <Textarea
                className="mt-1.5"
                value={form.address}
                onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))}
              />
            </div>
            {error && (
              <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex gap-3">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
                Create Supplier
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
      <Truck className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No suppliers found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Add suppliers before assigning vendors to stock.
    </p>
  </div>
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
      value={value}
      onChange={(event) => onChange(event.target.value)}
      required={required}
    />
  </div>
);

export default Suppliers;
