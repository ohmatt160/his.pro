import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useParams } from "react-router-dom";
import { getFacilityWorkspace } from "@/lib/facility-workspace";
import { canAccessModule, type FacilityModuleId } from "@/lib/modules";
import { useAuth } from "@/context/AuthContext";

const ModuleRoute = ({
  module,
  children,
}: {
  module: FacilityModuleId;
  children: ReactNode;
}) => {
  const { facilitySlug = "" } = useParams();
  const { user } = useAuth();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;

    if (!facilitySlug) {
      setAllowed(false);
      return;
    }

    getFacilityWorkspace(facilitySlug)
      .then((workspace) => {
        if (mounted) {
          setAllowed(
            Boolean(
              workspace &&
                canAccessModule({
                  modules: workspace.selectedModules,
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
  }, [facilitySlug, module, user?.role]);

  if (allowed === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-sm font-medium text-muted-foreground">Checking module access...</p>
      </div>
    );
  }

  if (!allowed) {
    if (user && user.role !== "admin") {
      return <Navigate to={`/portal/${facilitySlug}`} replace />;
    }

    return <Navigate to={`/dashboard/${facilitySlug}`} replace />;
  }

  return <>{children}</>;
};

export default ModuleRoute;
