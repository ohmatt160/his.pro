import { useEffect, useMemo, useState, type ElementType } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  BedDouble,
  Bell,
  CalendarDays,
  Check,
  Copy,
  Eye,
  EyeOff,
  FileHeart,
  FlaskConical,
  Layers,
  LayoutDashboard,
  Link2,
  LogOut,
  Package,
  Pill,
  Receipt,
  ScanLine,
  Search,
  Settings,
  Shield,
  Stethoscope,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  clearStaffSession,
  createStaffAccount,
  getDefaultDepartmentForRole,
  getFacilityLoginLink,
  getFacilityLoginPath,
  getFacilityStaff,
  getStaffRoleLabel,
  staffRoles,
  type FacilityStaffAccount,
  type StaffRole,
} from "@/lib/facility-staff";
import {
  getFacilityDashboardPath,
  getFacilityWorkspace,
} from "@/lib/facility-workspace";

const moduleIcons: Record<string, ElementType> = {
  reception: Users,
  records: FileHeart,
  consultations: Stethoscope,
  nursing: BedDouble,
  lab: FlaskConical,
  pharmacy: Pill,
  billing: Receipt,
  radiology: ScanLine,
  inventory: Package,
};

const moduleLabels: Record<string, string> = {
  reception: "Reception & Registration",
  records: "Shared Patient Record",
  consultations: "Doctors & Consultations",
  nursing: "Nursing & Wards",
  lab: "Laboratory",
  pharmacy: "Pharmacy",
  billing: "Billing & Claims",
  radiology: "Radiology",
  inventory: "Inventory & Stores",
};

const roleBadgeColors: Record<StaffRole, string> = {
  admin: "bg-slate-100 text-slate-700 border-slate-200",
  doctor: "bg-blue-100 text-blue-700 border-blue-200",
  nurse: "bg-emerald-100 text-emerald-700 border-emerald-200",
  reception: "bg-amber-100 text-amber-700 border-amber-200",
  pharmacist: "bg-purple-100 text-purple-700 border-purple-200",
  lab: "bg-cyan-100 text-cyan-700 border-cyan-200",
};

const departmentOptions = [
  "Administration",
  "Consultations",
  "Emergency",
  "Front Desk",
  "Laboratory",
  "Nursing",
  "Operations",
  "Pharmacy",
  "Radiology",
  "Revenue & Billing",
];

const assignableRoles = staffRoles.filter((role) => role !== "admin");

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

const StaffAccess = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const workspace = facilitySlug ? getFacilityWorkspace(facilitySlug) : null;
  const [staffList, setStaffList] = useState<FacilityStaffAccount[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<FacilityStaffAccount | null>(
    null
  );
  const [newStaff, setNewStaff] = useState({
    fullName: "",
    role: "doctor" as StaffRole,
    department: getDefaultDepartmentForRole("doctor"),
    email: "",
    phone: "",
  });

  useEffect(() => {
    if (facilitySlug) {
      setStaffList(getFacilityStaff(facilitySlug));
    }
  }, [facilitySlug]);

  const rolesProvisioned = useMemo(
    () => new Set(staffList.map((staff) => staff.role)).size,
    [staffList]
  );

  const filteredStaff = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    if (!query) {
      return staffList;
    }

    return staffList.filter((staff) => {
      const roleLabel = getStaffRoleLabel(staff.role).toLowerCase();

      return (
        staff.fullName.toLowerCase().includes(query) ||
        roleLabel.includes(query) ||
        staff.department.toLowerCase().includes(query) ||
        staff.loginId.toLowerCase().includes(query) ||
        staff.email.toLowerCase().includes(query) ||
        staff.phone.toLowerCase().includes(query)
      );
    });
  }, [searchQuery, staffList]);

  if (!workspace) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
            Facility not found
          </h1>
          <p className="mt-3 text-muted-foreground">
            We could not load the facility workspace for staff access
            management.
          </p>
          <Button
            asChild
            className="gradient-cta mt-6 border-0 text-primary-foreground"
          >
            <Link to="/">Back to landing page</Link>
          </Button>
        </div>
      </div>
    );
  }

  const fullName = workspace.fullName || "Admin";
  const selectedModules =
    workspace.selectedModules?.length > 0
      ? workspace.selectedModules
      : ["reception", "records", "consultations", "billing"];
  const dashboardPath = getFacilityDashboardPath(facilitySlug);
  const facilityLoginPath = getFacilityLoginPath(facilitySlug);
  const loginLink = getFacilityLoginLink(facilitySlug);

  const handleCopy = async (value: string, field: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedField(field);
      window.setTimeout(() => setCopiedField(null), 1800);
    } catch {
      setCopiedField(null);
    }
  };

  const handleAddStaff = () => {
    if (!newStaff.fullName.trim() || !newStaff.department.trim()) {
      return;
    }

    const account = createStaffAccount({
      facilitySlug,
      fullName: newStaff.fullName.trim(),
      role: newStaff.role,
      department: newStaff.department.trim(),
      email: newStaff.email.trim(),
      phone: newStaff.phone.trim(),
      createdBy: workspace.fullName,
    });

    setStaffList(getFacilityStaff(facilitySlug));
    setJustCreated(account);
    setShowAddModal(false);
    setNewStaff({
      fullName: "",
      role: "doctor",
      department: getDefaultDepartmentForRole("doctor"),
      email: "",
      phone: "",
    });
  };

  const handleLogout = () => {
    clearStaffSession();
    navigate(facilityLoginPath, { replace: true });
  };

  return (
    <div className="min-h-screen bg-background flex">
      <motion.aside
        initial={{ x: -260 }}
        animate={{ x: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 25 }}
        className="hidden w-64 flex-col border-r border-border bg-card lg:flex"
      >
        <div className="border-b border-border p-5">
          <Link to="/" className="text-xl font-extrabold tracking-tight">
            <span className="text-gradient">HIS</span>
            <span className="text-foreground">.Pro</span>
          </Link>
          <p className="mt-1 text-xs capitalize text-muted-foreground">
            {workspace.facilityType} Dashboard
          </p>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          <SidebarLink
            icon={LayoutDashboard}
            label="Dashboard"
            to={dashboardPath}
          />
          <SidebarLink icon={Users} label="Staff & Access" active />
          <SidebarLink icon={Activity} label="Analytics" />
          <SidebarLink icon={CalendarDays} label="Appointments" />
          <div className="px-3 pb-1 pt-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              Modules
            </p>
          </div>
          {selectedModules.map((moduleId) => {
            const Icon = moduleIcons[moduleId] || Layers;

            return (
              <SidebarLink
                key={moduleId}
                icon={Icon}
                label={moduleLabels[moduleId] || moduleId}
              />
            );
          })}
        </nav>

        <div className="space-y-1 border-t border-border p-3">
          <SidebarLink icon={Settings} label="Settings" />
          <SidebarLink icon={LogOut} label="Log Out" onClick={handleLogout} />
        </div>
      </motion.aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex h-16 items-center justify-between border-b border-border bg-card/80 px-6 backdrop-blur-lg"
        >
          <div className="flex items-center gap-3">
            <div className="text-xl font-extrabold tracking-tight lg:hidden">
              <span className="text-gradient">HIS</span>
              <span className="text-foreground">.Pro</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5 text-muted-foreground" />
            </Button>
            <div className="flex h-9 w-9 items-center justify-center rounded-full gradient-hero text-sm font-bold text-primary-foreground">
              {fullName.charAt(0).toUpperCase()}
            </div>
          </div>
        </motion.header>

        <main className="flex-1 overflow-auto p-6">
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="mx-auto max-w-6xl space-y-6"
          >
            <motion.div
              variants={item}
              className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {workspace.facilityName}
                </p>
                <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
                  Staff & Access
                </h1>
              </div>
              <Button
                onClick={() => setShowAddModal(true)}
                className="gradient-cta gap-2 border-0 text-primary-foreground shadow-lg"
              >
                <UserPlus className="h-4 w-4" /> Add Staff
              </Button>
            </motion.div>

            <motion.div
              variants={item}
              className="grid grid-cols-1 gap-4 sm:grid-cols-3"
            >
              <Card className="border-border/60">
                <CardContent className="flex items-center gap-4 p-5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                    <Users className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="text-2xl font-extrabold text-foreground">
                      {staffList.length}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Staff Accounts
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/60">
                <CardContent className="flex items-center gap-4 p-5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10">
                    <Shield className="h-6 w-6 text-accent" />
                  </div>
                  <div>
                    <p className="text-2xl font-extrabold text-foreground">
                      {rolesProvisioned}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Roles Provisioned
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/60">
                <CardContent className="p-5">
                  <div className="mb-2 flex items-center gap-2">
                    <Link2 className="h-4 w-4 text-primary" />
                    <p className="text-xs font-medium text-muted-foreground">
                      Staff Login Link
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 truncate rounded-lg bg-muted px-2 py-1.5 font-mono text-xs text-foreground">
                      {loginLink}
                    </code>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0"
                      onClick={() => handleCopy(loginLink, "link")}
                    >
                      {copiedField === "link" ? (
                        <Check className="h-3.5 w-3.5 text-accent" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <AnimatePresence>
              {justCreated && (
                <motion.div
                  initial={{ opacity: 0, y: -10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.98 }}
                >
                  <Card className="border-accent/30 bg-accent/5 shadow-md">
                    <CardContent className="p-5">
                      <div className="mb-3 flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20">
                            <UserCheck className="h-4 w-4 text-accent" />
                          </div>
                          <div>
                            <p className="text-sm font-bold text-foreground">
                              Staff account created
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {justCreated.fullName} ·{" "}
                              {getStaffRoleLabel(justCreated.role)}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => setJustCreated(null)}
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-3">
                        <CredentialBlock
                          label="Login Link"
                          value={loginLink}
                          field="cred-link"
                          copiedField={copiedField}
                          onCopy={handleCopy}
                        />
                        <CredentialBlock
                          label="Login ID"
                          value={justCreated.loginId}
                          field="cred-id"
                          copiedField={copiedField}
                          onCopy={handleCopy}
                        />
                        <CredentialBlock
                          label="Temp Password"
                          value={justCreated.temporaryPassword}
                          field="cred-password"
                          copiedField={copiedField}
                          onCopy={handleCopy}
                          sensitive
                        />
                      </div>

                      <p className="mt-3 text-[11px] text-muted-foreground">
                        Share these credentials securely so the staff member can
                        sign in through the facility login page.
                      </p>
                    </CardContent>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            <motion.div variants={item}>
              <Card className="border-border/60">
                <CardHeader className="pb-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <CardTitle className="text-base font-bold">
                      Staff Directory
                    </CardTitle>
                    <div className="relative w-full sm:w-64">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        placeholder="Search staff..."
                        value={searchQuery}
                        onChange={(event) => setSearchQuery(event.target.value)}
                        className="h-9 border-0 bg-muted/50 pl-9"
                      />
                    </div>
                  </div>
                </CardHeader>

                <CardContent>
                  {filteredStaff.length === 0 ? (
                    <div className="py-16 text-center">
                      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/80">
                        <Users className="h-7 w-7 text-muted-foreground" />
                      </div>
                      <p className="mb-1 font-semibold text-foreground">
                        {staffList.length === 0
                          ? "No staff accounts yet"
                          : "No results found"}
                      </p>
                      <p className="mb-4 text-sm text-muted-foreground">
                        {staffList.length === 0
                          ? "Add your first staff member to get this facility ready."
                          : "Try a different search term."}
                      </p>
                      {staffList.length === 0 && (
                        <Button
                          onClick={() => setShowAddModal(true)}
                          variant="outline"
                          className="gap-2"
                        >
                          <UserPlus className="h-4 w-4" /> Add First Staff
                        </Button>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="hidden grid-cols-12 gap-3 px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground md:grid">
                        <div className="col-span-3">Name</div>
                        <div className="col-span-2">Role</div>
                        <div className="col-span-2">Department</div>
                        <div className="col-span-2">Login ID</div>
                        <div className="col-span-2">Contact</div>
                        <div className="col-span-1" />
                      </div>

                      {filteredStaff.map((member, index) => (
                        <motion.div
                          key={member.staffRecordId}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.04 }}
                          className="grid grid-cols-1 items-center gap-3 rounded-xl border border-border/50 px-4 py-3 transition-all hover:border-primary/20 hover:bg-muted/30 md:grid-cols-12"
                        >
                          <div className="col-span-3 flex items-center gap-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                              {member.fullName
                                .split(" ")
                                .map((name) => name[0])
                                .join("")
                                .slice(0, 2)
                                .toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-foreground">
                                {member.fullName}
                              </p>
                              <p className="text-[11px] text-muted-foreground md:hidden">
                                {getStaffRoleLabel(member.role)} ·{" "}
                                {member.department}
                              </p>
                              <p className="text-[11px] text-muted-foreground md:hidden">
                                {member.loginId}
                              </p>
                            </div>
                          </div>

                          <div className="col-span-2 hidden md:block">
                            <span
                              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
                                roleBadgeColors[member.role]
                              }`}
                            >
                              {getStaffRoleLabel(member.role)}
                            </span>
                          </div>

                          <div className="col-span-2 hidden text-sm text-muted-foreground md:block">
                            {member.department}
                          </div>

                          <div className="col-span-2 hidden md:block">
                            <code className="rounded-md bg-muted px-2 py-1 font-mono text-xs text-foreground">
                              {member.loginId}
                            </code>
                          </div>

                          <div className="col-span-2 hidden text-xs text-muted-foreground md:block">
                            {member.email ? (
                              <span className="block truncate">{member.email}</span>
                            ) : (
                              <span className="block">No email added</span>
                            )}
                            {member.phone !== "—" && (
                              <span className="block">{member.phone}</span>
                            )}
                          </div>

                          <div className="col-span-1 hidden justify-end md:flex">
                            <Button asChild variant="ghost" size="sm" className="h-8 text-xs">
                              <Link to={facilityLoginPath}>Open login</Link>
                            </Button>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        </main>
      </div>

      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <UserPlus className="h-5 w-5 text-primary" /> Add Staff Member
            </DialogTitle>
            <DialogDescription>
              Create an account and generate login credentials for a new staff
              member.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Full Name *
              </Label>
              <Input
                placeholder="Dr. Sarah Mensah"
                value={newStaff.fullName}
                onChange={(event) =>
                  setNewStaff((previous) => ({
                    ...previous,
                    fullName: event.target.value,
                  }))
                }
                className="mt-1.5"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Role *
                </Label>
                <Select
                  value={newStaff.role}
                  onValueChange={(value) => {
                    const role = value as StaffRole;

                    setNewStaff((previous) => ({
                      ...previous,
                      role,
                      department: getDefaultDepartmentForRole(role),
                    }));
                  }}
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    {assignableRoles.map((role) => (
                      <SelectItem key={role} value={role}>
                        {getStaffRoleLabel(role)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Department *
                </Label>
                <Select
                  value={newStaff.department}
                  onValueChange={(value) =>
                    setNewStaff((previous) => ({
                      ...previous,
                      department: value,
                    }))
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    {departmentOptions.map((department) => (
                      <SelectItem key={department} value={department}>
                        {department}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Work Email
              </Label>
              <Input
                type="email"
                placeholder="sarah@facility.com"
                value={newStaff.email}
                onChange={(event) =>
                  setNewStaff((previous) => ({
                    ...previous,
                    email: event.target.value,
                  }))
                }
                className="mt-1.5"
              />
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Phone
              </Label>
              <Input
                placeholder="+234 800 000 0000"
                value={newStaff.phone}
                onChange={(event) =>
                  setNewStaff((previous) => ({
                    ...previous,
                    phone: event.target.value,
                  }))
                }
                className="mt-1.5"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowAddModal(false)}
              >
                Cancel
              </Button>
              <Button
                className="gradient-cta flex-1 border-0 text-primary-foreground"
                onClick={handleAddStaff}
                disabled={!newStaff.fullName.trim() || !newStaff.department.trim()}
              >
                Create Account
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const SidebarLink = ({
  icon: Icon,
  label,
  active,
  to,
  onClick,
}: {
  icon: ElementType;
  label: string;
  active?: boolean;
  to?: string;
  onClick?: () => void;
}) => {
  const className = `w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
    active
      ? "bg-primary/10 text-primary"
      : "text-muted-foreground hover:bg-muted hover:text-foreground"
  }`;

  if (to) {
    return (
      <Link to={to} className={className}>
        <Icon className="h-4 w-4 shrink-0" />
        {label}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </button>
  );
};

const CredentialBlock = ({
  label,
  value,
  field,
  copiedField,
  onCopy,
  sensitive,
}: {
  label: string;
  value: string;
  field: string;
  copiedField: string | null;
  onCopy: (value: string, field: string) => void;
  sensitive?: boolean;
}) => {
  const [show, setShow] = useState(!sensitive);

  return (
    <div className="rounded-lg border border-border/50 bg-background p-3">
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <div className="flex items-center gap-1.5">
        <code className="flex-1 truncate font-mono text-xs text-foreground">
          {show ? value : "••••••••••"}
        </code>
        {sensitive && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setShow((current) => !current)}
          >
            {show ? (
              <EyeOff className="h-3 w-3" />
            ) : (
              <Eye className="h-3 w-3" />
            )}
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => onCopy(value, field)}
        >
          {copiedField === field ? (
            <Check className="h-3 w-3 text-accent" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      </div>
    </div>
  );
};

export default StaffAccess;
