"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

interface LeaderboardEntry {
  user_id: string; first_name: string; last_name: string | null; total_points: number; rank: number;
}

interface ScoreEntry {
  id: string; score_type: string; points: number; reason: string | null; created_at: string;
}

const MEDAL = ["🥇", "🥈", "🥉"];

const TYPE_LABELS: Record<string, string> = {
  auto_task_ontime: "Задача в срок",
  auto_task_late: "Просрочка задачи",
  auto_report_ontime: "Отчёт вовремя",
  auto_report_late: "Просрочка отчёта",
  manual_bonus: "Премия",
  manual_penalty: "Штраф",
  peer_review: "Peer review",
};

export default function ScoresPage() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [history, setHistory] = useState<ScoreEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get("/api/v1/scores/leaderboard").then((r) => setLeaderboard(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const loadHistory = async (userId: string) => {
    setSelectedUser(userId);
    try {
      const res = await apiClient.get(`/api/v1/scores/user/${userId}`);
      setHistory(res.data);
    } catch {
      setHistory([]);
    }
  };

  if (loading) return <div className="text-center py-12 text-gray-500">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Рейтинг сотрудников</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Leaderboard */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Лидерборд</h2>
          {leaderboard.length === 0 ? (
            <p className="text-gray-500 text-sm">Нет данных</p>
          ) : (
            <div className="space-y-2">
              {leaderboard.map((entry) => (
                <button
                  key={entry.user_id} onClick={() => loadHistory(entry.user_id)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors ${
                    selectedUser === entry.user_id ? "bg-sup-50 border border-sup-200" : "hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg w-8 text-center">{MEDAL[entry.rank - 1] || entry.rank}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{entry.first_name} {entry.last_name || ""}</p>
                    </div>
                  </div>
                  <span className={`text-lg font-bold ${entry.total_points >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {entry.total_points > 0 ? "+" : ""}{entry.total_points}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Score History */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            {selectedUser ? "История баллов" : "Выберите сотрудника"}
          </h2>
          {!selectedUser ? (
            <p className="text-gray-500 text-sm">Нажмите на сотрудника в лидерборде</p>
          ) : history.length === 0 ? (
            <p className="text-gray-500 text-sm">Нет записей</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {history.map((entry) => (
                <div key={entry.id} className="flex items-center justify-between p-2 text-sm border-b border-gray-100">
                  <div>
                    <p className="font-medium text-gray-900">{TYPE_LABELS[entry.score_type] || entry.score_type}</p>
                    {entry.reason && <p className="text-xs text-gray-500 mt-0.5">{entry.reason}</p>}
                    <p className="text-xs text-gray-400">{new Date(entry.created_at).toLocaleDateString("ru-RU")}</p>
                  </div>
                  <span className={`font-bold ${entry.points >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {entry.points > 0 ? "+" : ""}{entry.points}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
