import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAG Social Chatbot",
  description: "AI-powered social video comparison chatbot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}