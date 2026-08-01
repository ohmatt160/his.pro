import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { apiClient } from "@/api/client";
import {
  getCanonicalSubdomainFromHostname,
  getPublicAppUrl,
} from "@/lib/tenant-routing";

type HostResolution = {
  slug: string;
  canonical_subdomain: string;
};

type TenantRoutingContextValue = {
  canonicalSubdomain: string;
  facilitySlug: string;
};

type TenantRouteParams = Record<string, string | undefined> & {
  routeFacilitySlug: string;
  facilitySlug: string;
  branchSlug: string;
};

const EMPTY_TENANT: TenantRoutingContextValue = {
  canonicalSubdomain: "",
  facilitySlug: "",
};

const TenantRoutingContext = createContext<TenantRoutingContextValue>(EMPTY_TENANT);

const TenantState = ({ title, detail }: { title: string; detail: string }) => (
  <div className="flex min-h-screen items-center justify-center bg-background px-6">
    <div className="max-w-md text-center">
      <h1 className="text-2xl font-bold text-foreground">{title}</h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{detail}</p>
      <a
        className="mt-6 inline-flex text-sm font-semibold text-primary hover:underline"
        href={getPublicAppUrl("/login")}
      >
        Find your workspace
      </a>
    </div>
  </div>
);

export const TenantRoutingProvider = ({ children }: { children: ReactNode }) => {
  const canonicalSubdomain = getCanonicalSubdomainFromHostname();
  const resolution = useQuery<HostResolution>({
    queryKey: ["tenant-host", canonicalSubdomain],
    queryFn: () =>
      apiClient.get<HostResolution>(
        `/facilities/resolve-host/${encodeURIComponent(canonicalSubdomain)}`
      ),
    enabled: Boolean(canonicalSubdomain),
    staleTime: 15 * 60_000,
    gcTime: 60 * 60_000,
    retry: 2,
  });

  if (!canonicalSubdomain) {
    return (
      <TenantRoutingContext.Provider value={EMPTY_TENANT}>
        {children}
      </TenantRoutingContext.Provider>
    );
  }

  if (resolution.isPending) {
    return (
      <TenantState
        title="Opening secure workspace"
        detail="Verifying this facility address before loading its data."
      />
    );
  }

  const facility = resolution.data;
  if (
    resolution.isError ||
    !facility ||
    facility.canonical_subdomain !== canonicalSubdomain ||
    !facility.slug
  ) {
    return (
      <TenantState
        title="Workspace unavailable"
        detail="This address is not assigned to an active HIS.Pro hospital or clinic."
      />
    );
  }

  return (
    <TenantRoutingContext.Provider
      value={{
        canonicalSubdomain,
        facilitySlug: facility.slug,
      }}
    >
      {children}
    </TenantRoutingContext.Provider>
  );
};

export const useTenantRouting = () => useContext(TenantRoutingContext);

export const useTenantParams = (): TenantRouteParams => {
  const params = useParams();
  const tenant = useTenantRouting();

  return {
    ...params,
    routeFacilitySlug: params.facilitySlug || "",
    facilitySlug: tenant.facilitySlug || params.facilitySlug || "",
    branchSlug: params.branchSlug || "",
  } as TenantRouteParams;
};
