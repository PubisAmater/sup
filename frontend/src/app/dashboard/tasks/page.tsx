"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import type { Task } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  todo: "К выполнению",
  in_progress: "В работе",
  done: "Выполнено",
  cancelled: "Отменено",
};

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status", statusFilter);
    if (priorityFilter) params.set("priority", priorityFilter);
    setError(null);

    apiClient
      .get(`/api/v1/tasks/?${params}`)
      .then((res) => setTasks(res.data))
      .catch(() => setError("Не удалось загрузить задачи"))
      .finally(() => setLoading(false));
  }, [statusFilter, priorityFilter]);

  const isOverdue = (task: Task) =>
    task.due_date &&
    new Date(task.due_date) < new Date() &&
    ["todo", "in_progress"].includes(task.status);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Задачи</h1>

      <div className="flex gap-4 mb-4 flex-wrap">
        <div className="flex gap-2">
          {["", "todo", "in_progress", "done"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === s
                  ? "bg-sup-100 text-sup-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {s === "" ? "Все" : STATUS_LABELS[s] || s}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {["", "critical", "high", "medium", "low"].map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                priorityFilter === p
                  ? "bg-sup-100 text-sup-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {p === "" ? "Все приоритеты" : p}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-4 text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Загрузка...</div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Задачи не найдены</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y divide-gray-100">
          {tasks.map((task) => (
            <Link
              key={task.id}
              href={`/dashboard/tasks/${task.id}`}
              className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate ${isOverdue(task) ? "text-red-700" : "text-gray-900"}`}>
                  {task.title}
                </p>
                <div className="flex gap-3 mt-1 text-xs text-gray-500">
                  <span>{STATUS_LABELS[task.status] || task.status}</span>
                  {task.due_date && (
                    <span className={isOverdue(task) ? "text-red-500 font-medium" : ""}>
                      Срок: {new Date(task.due_date).toLocaleDateString("ru-RU")}
                    </span>
                  )}
                </div>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ml-4 ${PRIORITY_STYLES[task.priority] || ""}`}>
                {task.priority}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
