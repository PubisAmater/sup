"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import type { Meeting } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  scheduled: "Запланировано",
  in_progress: "В процессе",
  completed: "Завершено",
  cancelled: "Отменено",
};

const PROCESSING_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: "Ожидает", color: "bg-gray-100 text-gray-700" },
  processing: { label: "Обработка...", color: "bg-blue-100 text-blue-700" },
  completed: { label: "Обработано", color: "bg-green-100 text-green-700" },
  failed: { label: "Ошибка", color: "bg-red-100 text-red-700" },
};

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status", statusFilter);
    setError(null);

    apiClient
      .get(`/api/v1/meetings/?${params}`)
      .then((res) => setMeetings(res.data))
      .catch(() => setError("Не удалось загрузить совещания"))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Совещания</h1>
        <Link
          href="/dashboard/meetings/new"
          className="bg-sup-600 text-white px-4 py-2 rounded-lg hover:bg-sup-700 transition-colors text-sm font-medium"
        >
          Новое совещание
        </Link>
      </div>

      <div className="flex gap-2 mb-4">
        {["", "scheduled", "completed", "cancelled"].map((s) => (
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

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-4 text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Загрузка...</div>
      ) : meetings.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Совещания не найдены</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y divide-gray-100">
          {meetings.map((meeting) => {
            const proc = PROCESSING_LABELS[meeting.processing_status] || PROCESSING_LABELS.pending;
            return (
              <Link
                key={meeting.id}
                href={`/dashboard/meetings/${meeting.id}`}
                className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{meeting.title}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {meeting.scheduled_at
                      ? new Date(meeting.scheduled_at).toLocaleString("ru-RU")
                      : "Дата не указана"}
                    {meeting.duration_minutes && ` · ${meeting.duration_minutes} мин.`}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${proc.color}`}>
                    {proc.label}
                  </span>
                  <span className="text-xs text-gray-400">
                    {STATUS_LABELS[meeting.status] || meeting.status}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
