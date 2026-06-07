import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  Clock,
  Phone,
  Play,
  RefreshCw,
  UserCheck,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";

type QueueEntry = {
  id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_phone?: string | null;
  appointment_time?: string | null;
  department: string;
  status: "waiting" | "in_progress" | "completed" | "no_show";
  queue_number: number;
  priority: "normal" | "urgent";
  checked_in_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
};

type QueueResponse = {
  queue_entries: QueueEntry[];
  total: number;
};

const statusLabels: Record<QueueEntry["status"], string> = {
  waiting: "Waiting",
  in_progress: "In Care",
  completed: "Completed",
  no_show: "No Show",
};

const Queue = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const loadQueue = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get<QueueResponse>("/queue?per_page=100");
      setEntries(response.queue_entries);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Queue failed to load.");
      setEntries([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue().catch(() => undefined);
  }, []);

  const summary = useMemo(
    () => ({
      waiting: entries.filter((entry) => entry.status === "waiting").length,
      inCare: entries.filter((entry) => entry.status === "in_progress").length,
      completed: entries.filter((entry) => entry.status === "completed").length,
      urgent: entries.filter((entry) => entry.priority === "urgent").length,
    }),
    [entries]
  );

  const updateQueue = async (entry: QueueEntry, action: "checkin" | "start" | "complete") => {
    setError("");
    try {
      await apiClient.put<QueueEntry>(`/queue/${entry.id}/${action}`, {});
      await loadQueue();
    } catch (queueError) {
      setError(
        queueError instanceof Error
          ? queueError.message
          : "Queue action could not be completed."
      );
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 px-6 py-4 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Button
              variant="ghost"
              className="mb-2 -ml-3 gap-2 text-muted-foreground"
              onClick={() => navigate(dashboardPath)}
            >
              <ArrowLeft className="h-4 w-4" /> Dashboard
            </Button>
            <h1 className="text-2xl font-extrabold tracking-tight">Reception Queue</h1>
            <p className="text-sm text-muted-foreground">
              Track arrivals, check-ins, active visits, and completed flow.
            </p>
          </div>
          <Button onClick={loadQueue} variant="outline" className="gap-2">
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Waiting" value={String(summary.waiting)} icon={Clock} />
          <Metric label="In Care" value={String(summary.inCare)} icon={Activity} />
          <Metric label="Completed" value={String(summary.completed)} icon={CheckCircle2} />
          <Metric label="Urgent" value={String(summary.urgent)} icon={ClipboardList} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-base">Patient Flow</CardTitle>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}
            {loading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Loading queue...</p>
            ) : entries.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No patients are currently in the queue.
              </p>
            ) : (
              <div className="space-y-3">
                {entries.map((entry, index) => (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-card p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-sm font-bold text-primary">
                        #{entry.queue_number}
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-foreground">
                            {entry.patient_name || "Unnamed patient"}
                          </p>
                          <Badge variant={entry.priority === "urgent" ? "destructive" : "secondary"}>
                            {entry.priority}
                          </Badge>
                          <Badge variant="outline">{statusLabels[entry.status]}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {entry.department}
                          {entry.patient_phone ? ` · ${entry.patient_phone}` : ""}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {entry.status === "waiting" && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            className="gap-2"
                            onClick={() => updateQueue(entry, "checkin")}
                          >
                            <UserCheck className="h-4 w-4" /> Check In
                          </Button>
                          <Button
                            size="sm"
                            className="gradient-cta gap-2 border-0 text-primary-foreground"
                            onClick={() => updateQueue(entry, "start")}
                          >
                            <Play className="h-4 w-4" /> Start
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="gap-2"
                            onClick={() => updateQueue(entry, "complete")}
                          >
                            <CheckCircle2 className="h-4 w-4" /> Clear
                          </Button>
                        </>
                      )}
                      {entry.status === "in_progress" && (
                        <Button
                          size="sm"
                          className="gradient-cta gap-2 border-0 text-primary-foreground"
                          onClick={() => updateQueue(entry, "complete")}
                        >
                          <CheckCircle2 className="h-4 w-4" /> Clear
                        </Button>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

const Metric = ({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
}) => (
  <Card className="border-border/60">
    <CardContent className="flex items-center gap-3 p-5">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div>
        <p className="text-2xl font-extrabold text-foreground">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </CardContent>
  </Card>
);

export default Queue;
