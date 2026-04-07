"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";

interface Report {
  id: string; user_id: string; period_start: string; period_end: string;
  completed_tasks: string | null; metrics_json: string | null; requests: string | null;
  status: string; submitted_at: string | null; created_at: string;
}

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get(`/api/v1/reports/${params.id}`).then((r) => setReport(r.data)).catch(() => router.push("/dashboard/reports")).finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  if (!report) return null;

  return (
    <div className="max-w-3xl">
      <button onClick={() => router.push("/dashboard/reports")} className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block">&larr; Все отчёты</button>
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-gray-900">
            Отчёт за {new Date(report.period_start).toLocaleDateString("ru-RU")} — {new Date(report.period_end).toLocaleDateString("ru-RU")}
          </h1>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${report.status === "submitted" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-700"}`}>
            {report.status === "submitted" ? "Подан" : report.status === "reviewed" ? "Рассмотрен" : "Черновик"}
          </span>
        </div>

        {report.completed_tasks && (
          <div className="mb-5">
            <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">Выполненные задачи</h2>
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{report.completed_tasks}</p>
          </div>
        )}
        {report.metrics_json && (
          <div className="mb-5">
            <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">Метрики</h2>
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{report.metrics_json}</p>
          </div>
        )}
        {report.requests && (
          <div className="mb-5">
            <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">Запросы управленческих решений</h2>
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{report.requests}</p>
          </div>
        )}
        {report.submitted_at && (
          <p className="text-xs text-gray-400 mt-4">Подан: {new Date(report.submitted_at).toLocaleString("ru-RU")}</p>
        )}
      </div>
    </div>
  );
}
