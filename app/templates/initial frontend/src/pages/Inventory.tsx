import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Boxes,
  Package,
  PackagePlus,
  Plus,
  Search,
  TriangleAlert,
  Truck,
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
import { getFacilityDashboardPath } from "@/lib/facility-workspace";

type InventoryItem = {
  id: string;
  facility_slug: string;
  name: string;
  sku: string;
  category: "medication" | "supplies" | "equipment" | string;
  unit: string;
  reorder_level: number;
  reorder_quantity: number;
  current_stock: number;
  expiry_date?: string | null;
  supplier_id?: string | null;
  supplier_name?: string | null;
  unit_cost: number;
  needs_reorder: boolean;
};

type Supplier = {
  id: string;
  name: string;
};

const emptyItemForm = {
  name: "",
  sku: "",
  category: "supplies",
  unit: "piece",
  reorder_level: "10",
  reorder_quantity: "20",
  current_stock: "0",
  expiry_date: "",
  supplier_id: "none",
  unit_cost: "",
};

const emptyStockForm = {
  item_id: "",
  adjustment_type: "addition",
  current_stock: "",
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(value || 0);

const Inventory = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showItemDialog, setShowItemDialog] = useState(false);
  const [showStockDialog, setShowStockDialog] = useState(false);
  const [itemForm, setItemForm] = useState(emptyItemForm);
  const [stockForm, setStockForm] = useState(emptyStockForm);
  const [error, setError] = useState("");

  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const visibleItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return items;
    }
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(query) ||
        item.sku.toLowerCase().includes(query) ||
        item.category.toLowerCase().includes(query)
    );
  }, [items, search]);

  const summary = useMemo(
    () => ({
      stock: items.reduce((sum, item) => sum + item.current_stock, 0),
      lowStock: items.filter((item) => item.needs_reorder).length,
      supplies: items.filter((item) => item.category === "supplies").length,
      equipment: items.filter((item) => item.category === "equipment").length,
    }),
    [items]
  );

  const loadInventory = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<InventoryItem[]>("/inventory?per_page=100");
      const supplierResponse = await apiClient.get<Supplier[]>("/suppliers");
      setItems(response);
      setSuppliers(supplierResponse);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInventory().catch(() => {
      setItems([]);
      setLoading(false);
    });
  }, []);

  const createItem = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!itemForm.name.trim() || !itemForm.sku.trim() || !itemForm.unit.trim()) {
      setError("Name, SKU, and unit are required.");
      return;
    }

    try {
      await apiClient.post<InventoryItem>("/inventory", {
        name: itemForm.name.trim(),
        sku: itemForm.sku.trim().toUpperCase(),
        category: itemForm.category,
        unit: itemForm.unit.trim(),
        reorder_level: Number(itemForm.reorder_level) || 0,
        reorder_quantity: Number(itemForm.reorder_quantity) || 0,
        current_stock: Number(itemForm.current_stock) || 0,
        expiry_date: itemForm.expiry_date || undefined,
        supplier_id: itemForm.supplier_id === "none" ? undefined : itemForm.supplier_id,
        unit_cost: itemForm.unit_cost ? Number(itemForm.unit_cost) : 0,
      });
      setItemForm(emptyItemForm);
      setShowItemDialog(false);
      await loadInventory();
    } catch (itemError) {
      setError(itemError instanceof Error ? itemError.message : "Inventory item creation failed.");
    }
  };

  const updateStock = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    const quantity = Number(stockForm.current_stock);
    if (!stockForm.item_id || Number.isNaN(quantity) || quantity < 0) {
      setError("Item and valid stock quantity are required.");
      return;
    }

    try {
      await apiClient.put<InventoryItem>(`/inventory/${stockForm.item_id}/stock`, {
        adjustment_type: stockForm.adjustment_type,
        current_stock: quantity,
      });
      setStockForm(emptyStockForm);
      setShowStockDialog(false);
      await loadInventory();
    } catch (stockError) {
      setError(stockError instanceof Error ? stockError.message : "Stock update failed.");
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
            <h1 className="text-2xl font-extrabold tracking-tight">Inventory</h1>
            <p className="text-sm text-muted-foreground">
              Track supplies, equipment, and general facility stock.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowStockDialog(true)}>
              <PackagePlus className="mr-2 h-4 w-4" /> Adjust Stock
            </Button>
            <Button
              onClick={() => setShowItemDialog(true)}
              className="gradient-cta gap-2 border-0 text-primary-foreground"
            >
              <Plus className="h-4 w-4" /> New Item
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Items" value={String(items.length)} icon={Boxes} />
          <Metric label="Stock Units" value={String(summary.stock)} icon={Package} />
          <Metric label="Low Stock" value={String(summary.lowStock)} icon={TriangleAlert} />
          <Metric label="Equipment" value={String(summary.equipment)} icon={PackagePlus} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-base">Inventory Items</CardTitle>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search name, SKU, category"
                  className="w-full pl-9 sm:w-72"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading inventory...
              </p>
            ) : visibleItems.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-2">
                {visibleItems.map((item, index) => (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className="grid gap-3 rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30 lg:grid-cols-[1.2fr_.7fr_.8fr_.8fr_auto]"
                  >
                    <div>
                      <p className="font-semibold text-foreground">{item.name}</p>
                      <p className="text-xs text-muted-foreground">{item.sku}</p>
                    </div>
                    <StatusBadge active={item.needs_reorder} />
                    <div>
                      <p className="text-sm font-semibold">{item.current_stock} {item.unit}</p>
                      <p className="text-xs text-muted-foreground">Reorder at {item.reorder_level}</p>
                    </div>
                    <div>
                      <p className="text-sm font-semibold capitalize">{item.category}</p>
                      <p className="text-xs text-muted-foreground">{formatCurrency(item.unit_cost)}</p>
                      {item.supplier_name && (
                        <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                          <Truck className="h-3 w-3" /> {item.supplier_name}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setStockForm({
                          item_id: item.id,
                          adjustment_type: "addition",
                          current_stock: "",
                        });
                        setShowStockDialog(true);
                      }}
                    >
                      Adjust
                    </Button>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <Dialog open={showItemDialog} onOpenChange={setShowItemDialog}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>New Inventory Item</DialogTitle>
            <DialogDescription>Create a stock-tracked facility item.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createItem} className="grid gap-4 pt-2 sm:grid-cols-2">
            <Field label="Name" value={itemForm.name} onChange={(value) => setItemForm((current) => ({ ...current, name: value }))} required />
            <Field label="SKU" value={itemForm.sku} onChange={(value) => setItemForm((current) => ({ ...current, sku: value }))} required />
            <SelectField
              label="Category"
              value={itemForm.category}
              options={[
                { value: "supplies", label: "Supplies" },
                { value: "equipment", label: "Equipment" },
                { value: "medication", label: "Medication" },
              ]}
              onChange={(value) => setItemForm((current) => ({ ...current, category: value }))}
            />
            <Field label="Unit" value={itemForm.unit} onChange={(value) => setItemForm((current) => ({ ...current, unit: value }))} required />
            <Field label="Opening Stock" type="number" value={itemForm.current_stock} onChange={(value) => setItemForm((current) => ({ ...current, current_stock: value }))} />
            <Field label="Reorder Level" type="number" value={itemForm.reorder_level} onChange={(value) => setItemForm((current) => ({ ...current, reorder_level: value }))} />
            <Field label="Reorder Quantity" type="number" value={itemForm.reorder_quantity} onChange={(value) => setItemForm((current) => ({ ...current, reorder_quantity: value }))} />
            <Field label="Unit Cost" type="number" value={itemForm.unit_cost} onChange={(value) => setItemForm((current) => ({ ...current, unit_cost: value }))} />
            <Field label="Expiry Date" type="date" value={itemForm.expiry_date} onChange={(value) => setItemForm((current) => ({ ...current, expiry_date: value }))} />
            <SelectField
              label="Supplier"
              value={itemForm.supplier_id}
              options={[
                { value: "none", label: "No supplier" },
                ...suppliers.map((supplier) => ({
                  value: supplier.id,
                  label: supplier.name,
                })),
              ]}
              onChange={(value) => setItemForm((current) => ({ ...current, supplier_id: value }))}
            />
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowItemDialog(false)} submitLabel="Create Item" />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={showStockDialog} onOpenChange={setShowStockDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Adjust Stock</DialogTitle>
            <DialogDescription>Set, add, or reduce item stock.</DialogDescription>
          </DialogHeader>
          <form onSubmit={updateStock} className="space-y-4 pt-2">
            <SelectField
              label="Item"
              value={stockForm.item_id}
              placeholder="Select item"
              options={items.map((item) => ({ value: item.id, label: `${item.name} (${item.sku})` }))}
              onChange={(value) => setStockForm((current) => ({ ...current, item_id: value }))}
            />
            <SelectField
              label="Adjustment"
              value={stockForm.adjustment_type}
              options={[
                { value: "addition", label: "Add" },
                { value: "reduction", label: "Reduce" },
                { value: "set", label: "Set exact stock" },
              ]}
              onChange={(value) => setStockForm((current) => ({ ...current, adjustment_type: value }))}
            />
            <Field label="Quantity" type="number" value={stockForm.current_stock} onChange={(value) => setStockForm((current) => ({ ...current, current_stock: value }))} required />
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowStockDialog(false)} submitLabel="Save Stock" />
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
      <Boxes className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No inventory items found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Create supplies or equipment to start tracking stock.
    </p>
  </div>
);

const StatusBadge = ({ active }: { active: boolean }) => (
  <span
    className={`inline-flex h-fit rounded-full px-2.5 py-1 text-xs font-semibold ${
      active ? "bg-amber-500/10 text-amber-700" : "bg-emerald-500/10 text-emerald-700"
    }`}
  >
    {active ? "Low stock" : "Stock ok"}
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

const SelectField = ({
  label,
  value,
  placeholder,
  options,
  onChange,
}: {
  label: string;
  value: string;
  placeholder?: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) => (
  <div>
    <Label>{label}</Label>
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="mt-1.5">
        <SelectValue placeholder={placeholder} />
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

const DialogActions = ({
  onCancel,
  submitLabel,
}: {
  onCancel: () => void;
  submitLabel: string;
}) => (
  <div className="flex gap-3 sm:col-span-2">
    <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
      Cancel
    </Button>
    <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
      {submitLabel}
    </Button>
  </div>
);

const FormError = ({ message }: { message: string }) => (
  <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">
    {message}
  </p>
);

export default Inventory;
