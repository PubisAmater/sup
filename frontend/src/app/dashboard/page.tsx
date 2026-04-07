"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { DashboardStats } from "@/lib/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .get("/api/v1/dashboard/stats")
      .then((res) => setStats(res.data))
      .catch((err) => setError("Не удалось загрузить данные. Сервер недоступен."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Панель управления</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <DashboardCard
          title="Сотрудники"
          value={loading ? "..." : String(stats?.employees_count ?? 0)}
          description="Активных"
        />
        <DashboardCard
          title="Совещания"
          value={loading ? "..." : String(stats?.meetings_this_week ?? 0)}
          description="На этой неделе"
        />
        <DashboardCard
          title="Задачи"
          value={loading ? "..." : String(stats?.tasks_in_progress ?? 0)}
          description="В работе"
        />
        <DashboardCard
          title="Просрочено"
          value={loading ? "..." : String(stats?.overdue_tasks ?? 0)}
          description="Требует внимания"
          highlight={!!stats?.overdue_tasks}
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Последние события</h2>
        <p className="text-gray-500">Пока нет данных для отображения.</p>
      </div>
    </div>
  );
}

function DashboardCard({
  title,
  value,
  description,
  highlight = false,
}: {
  title: string;
  value: string;
  description: string;
  highlight?: boolean;
}) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border p-6 ${highlight ? "border-red-300" : "border-gray-200"}`}>
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className={`text-3xl font-bold mt-1 ${highlight ? "text-red-600" : "text-gray-900"}`}>{value}</p>
      <p className="text-sm text-gray-400 mt-1">{description}</p>
    </div>
  );
}
