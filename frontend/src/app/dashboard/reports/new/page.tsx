"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";

export default function NewReportPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - today.getDay() + 1);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  const [form, setForm] = useState({
    completed_tasks: "",
    metrics_json: "",
    requests: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await apiClient.post("/api/v1/reports/", {
        period_start: monday.toISOString().split("T")[0],
        period_end: sunday.toISOString().split("T")[0],
        ...form,
      });
      // Auto-submit
      await apiClient.post(`/api/v1/reports/${res.data.id}/submit`);
      router.push("/dashboard/reports");
    } catch {
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <button onClick={() => router.push("/dashboard/reports")} className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block">
        &larr; Все отчёты
      </button>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Еженедельный отчёт</h1>
      <p className="text-sm text-gray-500 mb-6">
        Период: {monday.toLocaleDateString("ru-RU")} — {sunday.toLocaleDateString("ru-RU")}
      </p>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Выполненные задачи с итогами</label>
          <textarea value={form.completed_tasks} onChange={(e) => setForm({ ...form, completed_tasks: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm h-32 resize-y focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
            placeholder="1. Провёл аудит процессов — выявлено 5 узких мест&#10;2. Запустил новую рекламную кампанию — CTR 3.2%"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Ключевые метрики</label>
          <textarea value={form.metrics_json} onChange={(e) => setForm({ ...form, metrics_json: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm h-24 resize-y focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
            placeholder="Выручка: 12.5 млн ₽ (+8%)&#10;Загрузка кресел: 82%&#10;Средний чек: 15 200 ₽"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Запросы управленческих решений</label>
          <textarea value={form.requests} onChange={(e) => setForm({ ...form, requests: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm h-24 resize-y focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
            placeholder="Нужно утвердить бюджет на обучение — 150 000 ₽"
          />
        </div>
        <div className="flex gap-3">
          <button type="submit" disabled={submitting}
            className="px-4 py-2 bg-sup-600 text-white rounded-lg text-sm font-medium hover:bg-sup-700 disabled:opacity-50">
            {submitting ? "Отправка..." : "Подать отчёт"}
          </button>
          <button type="button" onClick={() => router.push("/dashboard/reports")}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">
            Отмена
          </button>
        </div>
      </form>
    </div>
  );
}
