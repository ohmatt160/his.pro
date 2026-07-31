import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import {
  getWorkspaceDashboardPath,
} from "@/lib/facility-workspace";
import { canAccessModule, type FacilityModuleId } from "@/lib/modules";
import { useAuth } from "@/context/AuthContext";
import { useBranchesQuery, useWorkspaceQuery } from "@/hooks/useWorkspaceQueries";
import {
  getBranchStaffPortalPath,
  getStaffPortalPath,
} from "@/lib/facility-staff";

const ModuleRoute = ({
  module,
  children,
}: {
  module: FacilityModuleId | FacilityModuleId[];
  children: ReactNode;
}) => {
  const { facilitySlug = "", branchSlug = "" } = useTenantParams();
  const { user } = useAuth();
  const workspaceQuery = useWorkspaceQuery(facilitySlug);
  const branchesQuery = useBranchesQuery(facilitySlug, Boolean(branchSlug));

  if (workspaceQuery.isPending || (branchSlug && branchesQuery.isPending)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-sm font-medium text-muted-foreground">Checking module access...</p>
      </div>
    );
  }

  const workspace = workspaceQuery.data;
  const branch = branchSlug
    ? branchesQuery.data?.find((item) => item.slug === branchSlug)
    : null;
  const userBelongsToBranch =
    !branchSlug ||
    user?.branchSlug === branchSlug ||
    Boolean(user?.branchSlugs?.includes(branchSlug));
  const modules = branchSlug ? branch?.modules || [] : workspace?.selectedModules || [];
  const requiredModules = Array.isArray(module) ? module : [module];
  const allowed = Boolean(
    workspace &&
      userBelongsToBranch &&
      requiredModules.some((moduleId) =>
        canAccessModule({
          modules,
          moduleId,
          role: user?.role,
        })
      )
  );

  if (!allowed) {
    if (user && !["admin", "branch_admin"].includes(user.role)) {
      return (
        <Navigate
          to={
            branchSlug
              ? getBranchStaffPortalPath(facilitySlug, branchSlug)
              : getStaffPortalPath(facilitySlug)
          }
          replace
        />
      );
    }

    return <Navigate to={getWorkspaceDashboardPath(facilitySlug, branchSlug || undefined)} replace />;
  }

  return <>{children}</>;
};

export default ModuleRoute;
