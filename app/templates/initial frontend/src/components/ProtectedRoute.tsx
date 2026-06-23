import { type ReactNode } from "react";
import { Navigate, useLocation, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { getBranchLoginPath, getFacilityLoginPath, getStaffPortalPath } from "@/lib/facility-staff";
import { getWorkspaceDashboardPath } from "@/lib/facility-workspace";
import { roleAllows, type WorkspaceRole } from "@/lib/role-access";

interface ProtectedRouteProps {
  children: ReactNode;
  requireAdmin?: boolean;
  requireFacilityAdmin?: boolean;
  allowedRoles?: WorkspaceRole[];
}

const ProtectedRoute = ({
  children,
  requireAdmin = false,
  requireFacilityAdmin = false,
  allowedRoles,
}: ProtectedRouteProps) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  const params = useParams();
  const facilitySlug = params.facilitySlug ?? "";
  const branchSlug = params.branchSlug ?? "";
  const loginPath = branchSlug
    ? getBranchLoginPath(facilitySlug, branchSlug)
    : getFacilityLoginPath(facilitySlug);
  const portalPath = branchSlug
    ? `/${facilitySlug}/branches/${branchSlug}/portal`
    : getStaffPortalPath(facilitySlug);

  if (loading) {
    return null;
  }

  if (!user) {
    return (
      <Navigate
        to={loginPath}
        state={{ from: location }}
        replace
      />
    );
  }

  if (facilitySlug && user.facilitySlug !== facilitySlug) {
    return <Navigate to={loginPath} replace />;
  }

  if (branchSlug) {
    const branchSlugs = user.branchSlugs || [];
    if (user.branchSlug !== branchSlug && !branchSlugs.includes(branchSlug)) {
      return <Navigate to={loginPath} replace />;
    }
  } else if (user.branchSlug && ["admin", "branch_admin"].includes(user.role)) {
    return <Navigate to={getWorkspaceDashboardPath(facilitySlug, user.branchSlug)} replace />;
  }

  if (requireAdmin && !["admin", "branch_admin"].includes(user.role)) {
    return <Navigate to={portalPath} replace />;
  }

  if (requireFacilityAdmin && user.role !== "admin") {
    return <Navigate to={getWorkspaceDashboardPath(facilitySlug, branchSlug || user.branchSlug)} replace />;
  }

  if (!roleAllows(user.role, allowedRoles)) {
    return <Navigate to={portalPath} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
