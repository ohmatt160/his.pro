import { type ReactNode } from "react";
import { Navigate, useLocation, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

interface ProtectedRouteProps {
  children: ReactNode;
  requireAdmin?: boolean;
}

const ProtectedRoute = ({
  children,
  requireAdmin = false,
}: ProtectedRouteProps) => {
  const { token, user, loading } = useAuth();
  const location = useLocation();
  const params = useParams();
  const facilitySlug = params.facilitySlug ?? "";

  if (loading) {
    return null;
  }

  if (!token || !user) {
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

  return <>{children}</>;
};

export default ProtectedRoute;
