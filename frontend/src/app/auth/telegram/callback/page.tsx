"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { setToken } from "@/lib/auth";

export default function TelegramCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const authenticate = async () => {
      try {
        const params: Record<string, string> = {};
        searchParams.forEach((value, key) => {
          params[key] = value;
        });

        const response = await apiClient.post("/auth/telegram/callback", params);
        setToken(response.data.access_token);
        router.push("/dashboard");
      } catch {
        setError("Ошибка авторизации. Попробуйте снова.");
      }
    };

    authenticate();
  }, [router, searchParams]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <a href="/" className="text-sup-600 hover:underline">
            Вернуться на главную
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sup-600 mx-auto mb-4" />
        <p className="text-gray-500">Выполняется авторизация...</p>
      </div>
    </div>
  );
}
