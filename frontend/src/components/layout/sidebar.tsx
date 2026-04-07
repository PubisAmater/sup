"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { removeToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

const navigation = [
  { name: "Панель управления", href: "/dashboard", icon: "grid" },
  { name: "Сотрудники", href: "/dashboard/employees", icon: "users" },
  { name: "Совещания", href: "/dashboard/meetings", icon: "calendar" },
  { name: "Задачи", href: "/dashboard/tasks", icon: "check-square" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    removeToken();
    router.push("/");
  };

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-sup-700">СУП</h1>
        <p className="text-xs text-gray-400 mt-1">Управление персоналом</p>
      </div>

      <nav className="flex-1 px-3">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-sup-50 text-sup-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-gray-200">
        <button
          onClick={handleLogout}
          className="w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          Выйти
        </button>
      </div>
    </aside>
  );
}
