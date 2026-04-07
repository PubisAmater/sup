"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";

interface Report {
  id: string;
  user_id: string;
  period_start: string;
  period_end: string;
  status: string;
  submitted_at: string | null;
  created_at: string;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: "Черновик", color: "bg-gray-100 text-gray-700" },
  submitted: { label: "Подан", color: "bg-green-100 text-green-700" },
  reviewed: { label: "Рассмотрен", color: "bg-blue-100 text-blue-700" },
};

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get("/api/v1/reports/").then((r) => setReports(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Еженедельные отчёты</h1>
        <Link
          href="/dashboard/reports/new"
          className="bg-sup-600 text-white px-4 py-2 rounded-lg hover:bg-sup-700 text-sm font-medium"
        >
          Новый отчёт
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Загрузка...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Отчёты не найдены</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y">
          {reports.map((r) => {
            const st = STATUS_LABELS[r.status] || STATUS_LABELS.draft;
            return (
              <Link key={r.id} href={`/dashboard/reports/${r.id}`} className="flex items-center justify-between p-4 hover:bg-gray-50">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {new Date(r.period_start).toLocaleDateString("ru-RU")} — {new Date(r.period_end).toLocaleDateString("ru-RU")}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {r.submitted_at ? `Подан: ${new Date(r.submitted_at).toLocaleString("ru-RU")}` : "Не подан"}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${st.color}`}>{st.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
