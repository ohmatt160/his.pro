import { apiClient } from "@/api/client";

export type WorkTask = {
  id: string;
  title: string;
  description: string;
  role: string;
  module: string;
  priority: "urgent" | "high" | "normal" | "low" | string;
  status: string;
  source_type: string;
  source_id: string;
  patient_id?: string | null;
  patient_name?: string | null;
  action_path: string;
  due_at?: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type TaskListResponse = {
  tasks: WorkTask[];
  total: number;
  role: string;
  generated_at: string;
};

export const getTasks = (limit = 50) =>
  apiClient.get<TaskListResponse>(`/tasks?limit=${limit}`);

export const taskTone = (priority: string): "success" | "warning" | "critical" => {
  if (priority === "urgent" || priority === "high") {
    return "critical";
  }
  if (priority === "low") {
    return "success";
  }
  return "warning";
};

export const formatTaskTime = (task: WorkTask) => {
  const raw = task.due_at || task.created_at;
  if (!raw) {
    return "Now";
  }

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return "Now";
  }

  return date.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
};
