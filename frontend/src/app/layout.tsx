import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "BlindSpot",
  description: "뉴스 편향성 분석 서비스",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="max-w-md mx-auto min-h-screen p-0 sm:p-4">
          {children}
        </div>
      </body>
    </html>
  );
}
