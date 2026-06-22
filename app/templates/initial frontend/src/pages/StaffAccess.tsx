import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Check,
  Copy,
  Eye,
  EyeOff,
  Link2,
  Search,
  Settings,
  Shield,
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
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/api/client";
import {
  createStaffAccount,
  getBranchLoginLink,
  getDefaultDepartmentForRole,
  getFacilityLoginLink,
  getFacilityStaff,
  getStaffRoleLabel,
  staffRoles,
  updateStaffAccount,
  type FacilityStaffAccount,
  type StaffRole,
} from "@/lib/facility-staff";
import { getFacilityWorkspace } from "@/lib/facility-workspace";

type FacilityBranch = {
  id: string;
  name: string;
  slug?: string;
  location?: string;
  modules?: string[];
  login_url_path?: string;
  dashboard_url_path?: string;
};

const roleBadgeColors: Record<StaffRole, string> = {
  admin: "bg-slate-100 text-slate-700 border-slate-200",
  branch_admin: "bg-teal-100 text-teal-700 border-teal-200",
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

const emptyEditStaff = {
  fullName: "",
  role: "doctor" as StaffRole,
  department: "",
  email: "",
  phone: "",
  password: "",
  mustChangePassword: true,
  isActive: true,
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const isValidOptionalEmail = (value: string) => {
  const trimmed = value.trim();
  return !trimmed || emailPattern.test(trimmed);
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

const StaffAccess = () => {
  const { facilitySlug = "", branchSlug = "" } = useParams();
  const { user } = useAuth();
  const [workspace, setWorkspace] = useState<
    | {
        facilityName: string;
        facilityType: string;
        country: string;
        fullName: string;
        email: string;
        phone: string;
        selectedModules: string[];
      }
    | null
    | undefined
  >(undefined);
  const [staffList, setStaffList] = useState<FacilityStaffAccount[]>([]);
  const [facilityDepartments, setFacilityDepartments] = useState<FacilityBranch[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [staffError, setStaffError] = useState("");
  const [creatingStaff, setCreatingStaff] = useState(false);
  const [updatingStaff, setUpdatingStaff] = useState(false);
  const [editingStaff, setEditingStaff] = useState<FacilityStaffAccount | null>(null);
  const [editStaff, setEditStaff] = useState(emptyEditStaff);
  const [editStaffDepartmentId, setEditStaffDepartmentId] = useState("");
  const [justCreated, setJustCreated] = useState<FacilityStaffAccount | null>(
    null
  );
  const [newStaff, setNewStaff] = useState({
    fullName: "",
    role: "doctor" as StaffRole,
    department: getDefaultDepartmentForRole("doctor"),
    departmentId: "",
    email: "",
    phone: "",
  });

  useEffect(() => {
    if (!facilitySlug) {
      return;
    }

    getFacilityWorkspace(facilitySlug).then(setWorkspace).catch(() => setWorkspace(null));
    apiClient
      .get<FacilityBranch[]>(`/facilities/${facilitySlug}/branches`)
      .then(setFacilityDepartments)
      .catch(() => setFacilityDepartments([]));
    getFacilityStaff(facilitySlug)
      .then((staff) => {
        setStaffList(staff);
        setStaffError("");
      })
      .catch((error) => {
        setStaffList([]);
        setStaffError(
          error instanceof Error
            ? error.message
            : "Staff accounts could not be loaded."
        );
      });
  }, [facilitySlug]);

  const isBranchAdmin = user?.role === "branch_admin";
  const currentBranch = useMemo(() => {
    if (!isBranchAdmin) {
      return null;
    }

    return (
      facilityDepartments.find((branch) => user?.branchId && branch.id === user.branchId) ||
      facilityDepartments.find((branch) => branchSlug && branch.slug === branchSlug) ||
      facilityDepartments[0] ||
      null
    );
  }, [branchSlug, facilityDepartments, isBranchAdmin, user?.branchId]);
  const branchScopedStaff = useMemo(() => {
    if (!isBranchAdmin || !currentBranch) {
      return staffList;
    }

    return staffList.filter((staff) => {
      const assignedBranch = staff.branchId || staff.departmentId;
      return assignedBranch === currentBranch.id;
    });
  }, [currentBranch, isBranchAdmin, staffList]);
  const assignableStaffRoles = useMemo(
    () => isBranchAdmin ? assignableRoles.filter((role) => role !== "branch_admin") : assignableRoles,
    [isBranchAdmin]
  );

  const rolesProvisioned = useMemo(
    () => new Set(branchScopedStaff.map((staff) => staff.role)).size,
    [branchScopedStaff]
  );

  const filteredStaff = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    if (!query) {
      return branchScopedStaff;
    }

    return branchScopedStaff.filter((staff) => {
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
  }, [branchScopedStaff, searchQuery]);

  const branchOptions = isBranchAdmin && currentBranch ? [currentBranch] : facilityDepartments;
  const branchById = useMemo(
    () => new Map(branchOptions.map((branch) => [branch.id, branch])),
    [branchOptions]
  );

  const loginLink = currentBranch?.slug ? getBranchLoginLink(facilitySlug, currentBranch.slug) : getFacilityLoginLink(facilitySlug);
  const getLoginLinkForBranch = (branchId?: string | null) => {
    const branch = branchId ? branchById.get(branchId) : undefined;
    if (!branch) {
      return loginLink;
    }

    if (branch.login_url_path) {
      const origin =
        typeof window !== "undefined" ? window.location.origin : "https://his.pro";
      return `${origin}${branch.login_url_path}`;
    }

    return branch.slug ? getBranchLoginLink(facilitySlug, branch.slug) : loginLink;
  };

  const getStaffLoginLink = (staff?: FacilityStaffAccount | null) =>
    getLoginLinkForBranch(staff?.branchId || staff?.departmentId);

  const justCreatedLoginLink = getStaffLoginLink(justCreated);

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

  const handleCopy = async (value: string, field: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedField(field);
      window.setTimeout(() => setCopiedField(null), 1800);
    } catch {
      setCopiedField(null);
    }
  };

  const handleAddStaff = async () => {
    if (!newStaff.fullName.trim() || !newStaff.department.trim()) {
      return;
    }
    if (!isValidOptionalEmail(newStaff.email)) {
      setStaffError("Enter a valid work email address or leave it blank.");
      return;
    }
    const assignedBranchId = isBranchAdmin ? currentBranch?.id || "" : newStaff.departmentId;
    if (isBranchAdmin && !assignedBranchId) {
      setStaffError("Your branch could not be found. Please sign in through your branch portal again.");
      return;
    }
    if (newStaff.role === "branch_admin" && !assignedBranchId) {
      setStaffError("Select the branch this branch admin will manage.");
      return;
    }

    setCreatingStaff(true);
    setStaffError("");
    try {
      const account = await createStaffAccount({
        facilitySlug,
        fullName: newStaff.fullName.trim(),
        role: newStaff.role,
        department: newStaff.department.trim(),
        branchId: assignedBranchId || undefined,
        branchIds: assignedBranchId ? [assignedBranchId] : undefined,
        email: newStaff.email.trim(),
        phone: newStaff.phone.trim(),
        createdBy: workspace?.fullName,
      });

      const updatedStaff = await getFacilityStaff(facilitySlug);
      setStaffList(updatedStaff);
      setJustCreated(account);
      setShowAddModal(false);
      setNewStaff({
        fullName: "",
        role: "doctor",
        department: getDefaultDepartmentForRole("doctor"),
        departmentId: isBranchAdmin ? assignedBranchId : "",
        email: "",
        phone: "",
      });
    } catch (error) {
      setStaffError(
        error instanceof Error
          ? error.message
          : "Staff account could not be created."
      );
    } finally {
      setCreatingStaff(false);
    }
  };

  const openEditStaff = (member: FacilityStaffAccount) => {
    setStaffError("");
    setEditingStaff(member);
    setEditStaff({
      fullName: member.fullName,
      role: member.role === "admin" ? "doctor" : member.role,
      department: member.department,
      email: member.email,
      phone: member.phone === "—" ? "" : member.phone,
      password: "",
      mustChangePassword: true,
      isActive: member.status === "active",
    });
    setEditStaffDepartmentId(member.branchId || member.departmentId || "");
  };

  const handleUpdateStaff = async () => {
    if (!editingStaff || !editStaff.fullName.trim() || !editStaff.department.trim()) {
      return;
    }
    if (!isValidOptionalEmail(editStaff.email)) {
      setStaffError("Enter a valid work email address or leave it blank.");
      return;
    }

    setUpdatingStaff(true);
    setStaffError("");
    try {
      const assignedBranchId = isBranchAdmin ? currentBranch?.id || "" : editStaffDepartmentId;
      if (isBranchAdmin && !assignedBranchId) {
        setStaffError("Your branch could not be found. Please sign in through your branch portal again.");
        setUpdatingStaff(false);
        return;
      }

      const updated = await updateStaffAccount({
        facilitySlug,
        loginId: editingStaff.loginId,
        fullName: editStaff.fullName,
        role: editingStaff.role === "admin" ? undefined : editStaff.role,
        department: editStaff.department,
        branchId: assignedBranchId || undefined,
        branchIds: assignedBranchId ? [assignedBranchId] : undefined,
        email: editStaff.email,
        phone: editStaff.phone,
        password: editStaff.password || undefined,
        mustChangePassword: editStaff.password ? editStaff.mustChangePassword : undefined,
        isActive: editStaff.isActive,
      });
      const updatedStaff = await getFacilityStaff(facilitySlug);
      setStaffList(updatedStaff);
      setEditingStaff(null);
      setEditStaff(emptyEditStaff);
      setEditStaffDepartmentId("");
      if (updated.temporaryPassword) {
        setJustCreated(updated);
      }
    } catch (error) {
      setStaffError(
        error instanceof Error
          ? error.message
          : "Staff account could not be updated."
      );
    } finally {
      setUpdatingStaff(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
        <main className="p-6">
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
                      {branchScopedStaff.length}
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
                      Default Login Link
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
              {staffError && (
                <motion.div
                  initial={{ opacity: 0, y: -10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.98 }}
                >
                  <Card className="border-destructive/30 bg-destructive/5">
                    <CardContent className="flex flex-col gap-3 p-4 text-sm text-destructive sm:flex-row sm:items-center sm:justify-between">
                      <span>{staffError}</span>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setStaffError("")}
                      >
                        Dismiss
                      </Button>
                    </CardContent>
                  </Card>
                </motion.div>
              )}

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
                          value={justCreatedLoginLink}
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
                        sign in through the assigned branch login page.
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
                        {branchScopedStaff.length === 0
                          ? "No staff accounts yet"
                          : "No results found"}
                      </p>
                      <p className="mb-4 text-sm text-muted-foreground">
                        {branchScopedStaff.length === 0
                          ? isBranchAdmin
                            ? "Add the first staff member for this branch."
                            : "Add your first staff member to get this facility ready."
                          : "Try a different search term."}
                      </p>
                      {branchScopedStaff.length === 0 && (
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

                      {filteredStaff.map((member, index) => {
                        const branchName = member.branchId
                          ? branchOptions.find((branch) => branch.id === member.branchId)?.name
                          : "";

                        return (
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
                            {branchName && (
                              <span className="mt-1 block text-[11px] text-muted-foreground">
                                {branchName}
                              </span>
                            )}
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
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 text-xs"
                              onClick={() => openEditStaff(member)}
                            >
                              Edit
                            </Button>
                          </div>
                        </motion.div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        </main>

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
                    {assignableStaffRoles.map((role) => (
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
                    setNewStaff((previous) => ({ ...previous, department: value }))
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


            {!isBranchAdmin && branchOptions.length > 0 && (
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Branch / Clinic
                </Label>
                <Select
                  value={newStaff.departmentId || "none"}
                  onValueChange={(value) =>
                    setNewStaff((previous) => ({
                      ...previous,
                      departmentId: value === "none" ? "" : value,
                    }))
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select branch or clinic" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No branch assigned</SelectItem>
                    {branchOptions.map((branch) => (
                      <SelectItem key={branch.id} value={branch.id}>
                        {branch.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

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
                disabled={
                  creatingStaff ||
                  !newStaff.fullName.trim() ||
                  !newStaff.department.trim() ||
                  (!isBranchAdmin && newStaff.role === "branch_admin" && !newStaff.departmentId)
                }
              >
                {creatingStaff ? "Creating..." : "Create Account"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(editingStaff)} onOpenChange={(open) => !open && setEditingStaff(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Settings className="h-5 w-5 text-primary" /> Edit Staff Account
            </DialogTitle>
            <DialogDescription>
              Update staff details or reset their password.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Full Name *
              </Label>
              <Input
                value={editStaff.fullName}
                onChange={(event) =>
                  setEditStaff((previous) => ({ ...previous, fullName: event.target.value }))
                }
                className="mt-1.5"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Role
                </Label>
                <Select
                  value={editingStaff?.role === "admin" ? "admin" : editStaff.role}
                  disabled={editingStaff?.role === "admin"}
                  onValueChange={(value) => {
                    const role = value as StaffRole;
                    setEditStaff((previous) => ({
                      ...previous,
                      role,
                      department: getDefaultDepartmentForRole(role),
                    }));
                  }}
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {editingStaff?.role === "admin" && (
                      <SelectItem value="admin">Facility Admin</SelectItem>
                    )}
                    {assignableStaffRoles.map((role) => (
                      <SelectItem key={role} value={role}>
                        {getStaffRoleLabel(role)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </Label>
                <Select
                  value={editStaff.isActive ? "active" : "inactive"}
                  onValueChange={(value) =>
                    setEditStaff((previous) => ({
                      ...previous,
                      isActive: value === "active",
                    }))
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Department *
              </Label>
              <Select
                value={editStaff.department}
                onValueChange={(value) =>
                  setEditStaff((previous) => ({ ...previous, department: value }))
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

            {!isBranchAdmin && branchOptions.length > 0 && (
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Branch / Clinic
                </Label>
                <Select
                  value={editStaffDepartmentId || "none"}
                  onValueChange={(value) =>
                    setEditStaffDepartmentId(value === "none" ? "" : value)
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select branch or clinic" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No branch assigned</SelectItem>
                    {branchOptions.map((branch) => (
                      <SelectItem key={branch.id} value={branch.id}>
                        {branch.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Work Email
              </Label>
              <Input
                type="email"
                value={editStaff.email}
                onChange={(event) =>
                  setEditStaff((previous) => ({ ...previous, email: event.target.value }))
                }
                className="mt-1.5"
              />
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Phone
              </Label>
              <Input
                value={editStaff.phone}
                onChange={(event) =>
                  setEditStaff((previous) => ({ ...previous, phone: event.target.value }))
                }
                className="mt-1.5"
              />
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                New Password
              </Label>
              <Input
                type="password"
                placeholder="Leave blank to keep current password"
                value={editStaff.password}
                onChange={(event) =>
                  setEditStaff((previous) => ({ ...previous, password: event.target.value }))
                }
                className="mt-1.5"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setEditingStaff(null)}
              >
                Cancel
              </Button>
              <Button
                className="gradient-cta flex-1 border-0 text-primary-foreground"
                onClick={handleUpdateStaff}
                disabled={
                  updatingStaff ||
                  !editStaff.fullName.trim() ||
                  !editStaff.department.trim()
                }
              >
                {updatingStaff ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
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

