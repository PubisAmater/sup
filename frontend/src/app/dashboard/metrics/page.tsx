"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

interface MetricAlert {
  id: string; alert_type: string; message: string; severity: string; is_resolved: boolean; created_at: string;
}
interface RevenueFormula {
  chairs: number; utilization_percent: number; avg_check: number; revenue: number; target_revenue: number; gap_percent: number;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  warning: "bg-yellow-100 text-yellow-700 border-yellow-200",
  info: "bg-blue-100 text-blue-700 border-blue-200",
};

export default function MetricsPage() {
  const [alerts, setAlerts] = useState<MetricAlert[]>([]);
  const [formula, setFormula] = useState<RevenueFormula | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get("/api/v1/metrics/alerts?resolved=false").catch(() => ({ data: [] })),
      apiClient.get("/api/v1/metrics/revenue-formula").catch(() => ({ data: null })),
    ]).then(([alertsRes, formulaRes]) => {
      setAlerts(alertsRes.data);
      setFormula(formulaRes.data);
    }).finally(() => setLoading(false));
  }, []);

  const handleResolve = async (id: string) => {
    await apiClient.post(`/api/v1/metrics/alerts/${id}/resolve`);
    setAlerts(alerts.filter((a) => a.id !== id));
  };

  if (loading) return <div className="text-center py-12 text-gray-500">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Метрики и аналитика</h1>

      {/* Revenue Formula */}
      {formula && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Формула выручки</h2>
          <div className="flex items-center gap-4 text-center">
            <div className="bg-sup-50 rounded-lg p-4 flex-1">
              <p className="text-3xl font-bold text-sup-700">{formula.chairs}</p>
              <p className="text-xs text-gray-500 mt-1">Кресел</p>
            </div>
            <span className="text-2xl text-gray-400">&times;</span>
            <div className="bg-sup-50 rounded-lg p-4 flex-1">
              <p className="text-3xl font-bold text-sup-700">{formula.utilization_percent}%</p>
              <p className="text-xs text-gray-500 mt-1">Загрузка</p>
            </div>
            <span className="text-2xl text-gray-400">&times;</span>
            <div className="bg-sup-50 rounded-lg p-4 flex-1">
              <p className="text-3xl font-bold text-sup-700">{(formula.avg_check / 1000).toFixed(1)}к</p>
              <p className="text-xs text-gray-500 mt-1">Средний чек</p>
            </div>
            <span className="text-2xl text-gray-400">=</span>
            <div className={`rounded-lg p-4 flex-1 ${formula.gap_percent > 10 ? "bg-red-50" : "bg-green-50"}`}>
              <p className={`text-3xl font-bold ${formula.gap_percent > 10 ? "text-red-700" : "text-green-700"}`}>
                {(formula.revenue / 1_000_000).toFixed(1)}М
              </p>
              <p className="text-xs text-gray-500 mt-1">Выручка</p>
            </div>
          </div>
          {formula.gap_percent > 0 && (
            <p className="text-sm text-gray-500 mt-3">
              До цели ({(formula.target_revenue / 1_000_000).toFixed(1)}М ₽): <span className="text-red-600 font-medium">-{formula.gap_percent}%</span>
            </p>
          )}
        </div>
      )}

      {/* Alerts */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Алерты ({alerts.length})</h2>
        {alerts.length === 0 ? (
          <p className="text-gray-500 text-sm">Нет активных алертов</p>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div key={alert.id} className={`flex items-center justify-between p-3 rounded-lg border ${SEVERITY_STYLES[alert.severity] || ""}`}>
                <div>
                  <p className="text-sm font-medium">{alert.message}</p>
                  <p className="text-xs opacity-75 mt-1">{new Date(alert.created_at).toLocaleString("ru-RU")}</p>
                </div>
                <button onClick={() => handleResolve(alert.id)} className="text-xs underline opacity-75 hover:opacity-100">Решено</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
