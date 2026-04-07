"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type { Employee } from "@/lib/types";

export default function EmployeeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get(`/api/v1/employees/${params.id}`).then((r) => setEmployee(r.data)).catch(() => router.push("/dashboard/employees")).finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  if (!employee) return null;

  return (
    <div className="max-w-3xl">
      <button onClick={() => router.push("/dashboard/employees")} className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block">&larr; Все сотрудники</button>
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">{employee.position}</h1>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Отдел</p>
            <p className="text-sm text-gray-900 mt-1">{employee.department}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Статус</p>
            <p className="text-sm text-gray-900 mt-1">{employee.is_active ? "Активен" : "Неактивен"}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Дата найма</p>
            <p className="text-sm text-gray-900 mt-1">{employee.hired_at ? new Date(employee.hired_at).toLocaleDateString("ru-RU") : "Не указана"}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Создан</p>
            <p className="text-sm text-gray-900 mt-1">{new Date(employee.created_at).toLocaleDateString("ru-RU")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
