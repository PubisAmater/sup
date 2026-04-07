"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.push("/dashboard");
    }
  }, [router]);

  return (
    <main className="min-h-screen bg-gradient-to-br from-sup-50 to-sup-100 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-xl p-10 max-w-md w-full text-center">
        <h1 className="text-4xl font-bold text-sup-900 mb-2">СУП</h1>
        <p className="text-sup-600 mb-8">Система Управления Персоналом</p>

        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            Войдите через Telegram для доступа к платформе
          </p>

          {/* Telegram Login Widget placeholder */}
          <div
            id="telegram-login"
            className="flex justify-center"
          >
            <a
              href={`https://oauth.telegram.org/auth?bot_id=${process.env.NEXT_PUBLIC_TELEGRAM_BOT_ID}&origin=${encodeURIComponent(window.location.origin)}&return_to=${encodeURIComponent(window.location.origin + "/auth/telegram/callback")}`}
              className="inline-flex items-center gap-2 bg-[#0088cc] text-white px-6 py-3 rounded-lg hover:bg-[#006daa] transition-colors font-medium"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
              </svg>
              Войти через Telegram
            </a>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-8">
          &copy; 2026 СУП. Все права защищены.
        </p>
      </div>
    </main>
  );
}
