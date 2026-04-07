"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";

export default function NewMeetingPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    scheduled_at: "",
    duration_minutes: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return;

    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        title: form.title.trim(),
      };
      if (form.description.trim()) payload.description = form.description.trim();
      if (form.scheduled_at) payload.scheduled_at = new Date(form.scheduled_at).toISOString();
      if (form.duration_minutes) payload.duration_minutes = parseInt(form.duration_minutes);

      const res = await apiClient.post("/api/v1/meetings/", payload);
      router.push(`/dashboard/meetings/${res.data.id}`);
    } catch {
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <button
        onClick={() => router.push("/dashboard/meetings")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block"
      >
        &larr; Все совещания
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Новое совещание</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Название *
          </label>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
            placeholder="Еженедельное совещание руководства"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Описание
          </label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-y h-24 focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
            placeholder="Повестка совещания..."
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Дата и время
            </label>
            <input
              type="datetime-local"
              value={form.scheduled_at}
              onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Длительность (мин.)
            </label>
            <input
              type="number"
              value={form.duration_minutes}
              onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
              placeholder="60"
              min="5"
              max="480"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting || !form.title.trim()}
            className="px-4 py-2 bg-sup-600 text-white rounded-lg text-sm font-medium hover:bg-sup-700 disabled:opacity-50"
          >
            {submitting ? "Создание..." : "Создать совещание"}
          </button>
          <button
            type="button"
            onClick={() => router.push("/dashboard/meetings")}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            Отмена
          </button>
        </div>
      </form>
    </div>
  );
}
