"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import type { Employee } from "@/lib/types";

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [department, setDepartment] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (department) params.set("department", department);
    apiClient.get(`/api/v1/employees/?${params}`).then((r) => setEmployees(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [department]);

  const departments = [...new Set(employees.map((e) => e.department))];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Сотрудники</h1>

      {departments.length > 0 && (
        <div className="flex gap-2 mb-4">
          <button onClick={() => setDepartment("")} className={`px-3 py-1.5 rounded-lg text-sm font-medium ${!department ? "bg-sup-100 text-sup-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            Все
          </button>
          {departments.map((d) => (
            <button key={d} onClick={() => setDepartment(d)} className={`px-3 py-1.5 rounded-lg text-sm font-medium ${department === d ? "bg-sup-100 text-sup-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {d}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Загрузка...</div>
      ) : employees.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Сотрудники не найдены</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y">
          {employees.map((emp) => (
            <Link key={emp.id} href={`/dashboard/employees/${emp.id}`} className="flex items-center justify-between p-4 hover:bg-gray-50">
              <div>
                <p className="text-sm font-medium text-gray-900">{emp.position}</p>
                <p className="text-xs text-gray-500 mt-1">{emp.department}</p>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${emp.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                {emp.is_active ? "Активен" : "Неактивен"}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
