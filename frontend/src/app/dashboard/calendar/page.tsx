"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

interface Slot {
  start: string;
  end: string;
}

export default function CalendarPage() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState<string | null>(null);
  const [title, setTitle] = useState("");

  useEffect(() => {
    apiClient.get("/api/v1/calendar/slots").then((r) => setSlots(r.data.slots || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleBook = async (slot: Slot) => {
    if (!title.trim()) return;
    setBooking(slot.start);
    try {
      await apiClient.post("/api/v1/calendar/book", {
        title: title.trim(),
        start: slot.start,
        end: slot.end,
      });
      setSlots(slots.filter((s) => s.start !== slot.start));
      setTitle("");
    } catch {
    } finally {
      setBooking(null);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Календарь CEO</h1>
      <p className="text-sm text-gray-500 mb-6">Забронируйте свободный слот для встречи с CEO</p>

      <div className="mb-4">
        <input
          type="text" value={title} onChange={(e) => setTitle(e.target.value)}
          placeholder="Тема встречи"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-80 focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
        />
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Загрузка слотов...</div>
      ) : slots.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Нет доступных слотов</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {slots.slice(0, 30).map((slot) => (
            <div key={slot.start} className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {new Date(slot.start).toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "short" })}
                </p>
                <p className="text-xs text-gray-500">
                  {new Date(slot.start).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })} —{" "}
                  {new Date(slot.end).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
              <button
                onClick={() => handleBook(slot)}
                disabled={!title.trim() || booking === slot.start}
                className="px-3 py-1.5 bg-sup-600 text-white rounded-lg text-xs font-medium hover:bg-sup-700 disabled:opacity-50"
              >
                {booking === slot.start ? "..." : "Забронировать"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
