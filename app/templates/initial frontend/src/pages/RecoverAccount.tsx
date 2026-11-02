import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";

const RecoverAccount = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("Recovering your facility account...");
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    let active = true;
    const facility = searchParams.get("facility") || "";
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token") || "";
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);

    if (!facility || !token) {
      setStatus("This recovery link is incomplete or has already been used.");
      setFinished(true);
      return () => { active = false; };
    }

    apiClient.request<{ message?: string }>(
      `/facilities/${encodeURIComponent(facility)}/account-deletion/cancel`,
      { method: "POST", body: { recovery_token: token }, authToken: null },
    ).then((result) => {
      if (!active) return;
      setStatus(result.message || "Account deletion was cancelled. You can sign in again.");
      setFinished(true);
    }).catch(() => {
      if (!active) return;
      setStatus("This recovery link is invalid or expired. Contact HIS.Pro support for help.");
      setFinished(true);
    });

    return () => { active = false; };
  }, [searchParams]);

  const facility = searchParams.get("facility");
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <section className="w-full max-w-md space-y-5 border border-border bg-card p-6 shadow-sm">
        <div>
          <p className="text-sm font-semibold text-primary">HIS.Pro account recovery</p>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">
            {finished ? "Recovery status" : "Restoring access"}
          </h1>
        </div>
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground">{status}</p>
        {finished && facility && (
          <Button asChild><Link to={`/${encodeURIComponent(facility)}/login`}>Continue to sign in</Link></Button>
        )}
      </section>
    </main>
  );
};

export default RecoverAccount;
