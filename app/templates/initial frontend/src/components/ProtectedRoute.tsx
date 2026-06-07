import { type ReactNode } from "react";
import { Navigate, useLocation, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { roleAllows, type WorkspaceRole } from "@/lib/role-access";

interface ProtectedRouteProps {
  children: ReactNode;
  requireAdmin?: boolean;
  allowedRoles?: WorkspaceRole[];
}

const ProtectedRoute = ({
  children,
  requireAdmin = false,
  allowedRoles,
}: ProtectedRouteProps) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  const params = useParams();
  const facilitySlug = params.facilitySlug ?? "";

  if (loading) {
    return null;
  }

  if (!user) {
    return (
      <Navigate
        to={`/login/${facilitySlug}`}
        state={{ from: location }}
        replace
      />
    );
  }

  if (facilitySlug && user.facilitySlug !== facilitySlug) {
    return <Navigate to={`/login/${facilitySlug}`} replace />;
  }

  if (requireAdmin && user.role !== "admin") {
    return <Navigate to={`/portal/${facilitySlug}`} replace />;
  }

  if (!roleAllows(user.role, allowedRoles)) {
    return <Navigate to={`/portal/${facilitySlug}`} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
