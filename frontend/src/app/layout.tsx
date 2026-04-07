import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "СУП — Система Управления Персоналом",
  description: "Интеллектуальная платформа управления персоналом",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body className="antialiased">{children}</body>
    </html>
  );
}
