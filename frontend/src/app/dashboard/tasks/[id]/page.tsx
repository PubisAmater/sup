"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type { Task } from "@/lib/types";

const STATUS_OPTIONS = ["todo", "in_progress", "done", "cancelled"];
const STATUS_LABELS: Record<string, string> = {
  todo: "К выполнению",
  in_progress: "В работе",
  done: "Выполнено",
  cancelled: "Отменено",
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);

  const taskId = params.id as string;

  useEffect(() => {
    apiClient
      .get(`/api/v1/tasks/${taskId}`)
      .then((res) => setTask(res.data))
      .catch(() => router.push("/dashboard/tasks"))
      .finally(() => setLoading(false));
  }, [taskId]);

  const handleStatusChange = async (newStatus: string) => {
    try {
      const res = await apiClient.patch(`/api/v1/tasks/${taskId}`, { status: newStatus });
      setTask(res.data);
    } catch {}
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  }

  if (!task) return null;

  const isOverdue =
    task.due_date &&
    new Date(task.due_date) < new Date() &&
    ["todo", "in_progress"].includes(task.status);

  return (
    <div className="max-w-3xl">
      <button
        onClick={() => router.push("/dashboard/tasks")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block"
      >
        &larr; Все задачи
      </button>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{task.title}</h1>

        {task.description && (
          <p className="text-gray-600 mt-3 whitespace-pre-wrap">{task.description}</p>
        )}

        <div className="grid grid-cols-2 gap-4 mt-6">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Статус</p>
            <div className="flex gap-2 mt-1">
              {STATUS_OPTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleStatusChange(s)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    task.status === s
                      ? "bg-sup-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {STATUS_LABELS[s]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Приоритет</p>
            <p className="text-sm text-gray-900 mt-1 capitalize">{task.priority}</p>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Срок</p>
            <p className={`text-sm mt-1 ${isOverdue ? "text-red-600 font-medium" : "text-gray-900"}`}>
              {task.due_date
                ? new Date(task.due_date).toLocaleDateString("ru-RU")
                : "Не указан"}
              {isOverdue && " (просрочена)"}
            </p>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Создана</p>
            <p className="text-sm text-gray-900 mt-1">
              {new Date(task.created_at).toLocaleString("ru-RU")}
            </p>
          </div>
        </div>

        {task.meeting_id && (
          <div className="mt-6 pt-4 border-t border-gray-100">
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Совещание</p>
            <button
              onClick={() => router.push(`/dashboard/meetings/${task.meeting_id}`)}
              className="text-sm text-sup-600 hover:underline"
            >
              Перейти к совещанию &rarr;
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
