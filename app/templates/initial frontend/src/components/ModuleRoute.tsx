import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useParams } from "react-router-dom";
import {
  getFacilityWorkspace,
  getWorkspaceDashboardPath,
} from "@/lib/facility-workspace";
import { canAccessModule, type FacilityModuleId } from "@/lib/modules";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/api/client";

type FacilityBranch = {
  slug?: string;
  modules?: string[];
};

const ModuleRoute = ({
  module,
  children,
}: {
  module: FacilityModuleId;
  children: ReactNode;
}) => {
  const { facilitySlug = "", branchSlug = "" } = useParams();
  const { user } = useAuth();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;

    if (!facilitySlug) {
      setAllowed(false);
      return;
    }

    Promise.all([
      getFacilityWorkspace(facilitySlug),
      branchSlug
        ? apiClient.get<FacilityBranch[]>(`/facilities/${facilitySlug}/branches`).catch(() => [])
        : Promise.resolve([] as FacilityBranch[]),
    ])
      .then(([workspace, branches]) => {
        const branch = branchSlug ? branches.find((item) => item.slug === branchSlug) : null;
        const userBelongsToBranch =
          !branchSlug ||
          user?.branchSlug === branchSlug ||
          Boolean(user?.branchSlugs?.includes(branchSlug));
        const modules = branchSlug ? branch?.modules || [] : workspace?.selectedModules || [];
        if (mounted) {
          setAllowed(
            Boolean(
              workspace &&
                userBelongsToBranch &&
                canAccessModule({
                  modules,
                  moduleId: module,
                  role: user?.role,
                })
            )
          );
        }
      })
      .catch(() => {
        if (mounted) {
          setAllowed(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [branchSlug, facilitySlug, module, user?.role]);

  if (allowed === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-sm font-medium text-muted-foreground">Checking module access...</p>
      </div>
    );
  }

  if (!allowed) {
    if (user && !["admin", "branch_admin"].includes(user.role)) {
      return <Navigate to={branchSlug ? `/${facilitySlug}/branches/${branchSlug}/portal` : `/portal/${facilitySlug}`} replace />;
    }

    return <Navigate to={getWorkspaceDashboardPath(facilitySlug, branchSlug || undefined)} replace />;
  }

  return <>{children}</>;
};

export default ModuleRoute;
