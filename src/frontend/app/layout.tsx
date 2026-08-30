import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GestaltX Research",
  description: "Gap-driven research over the Ashen Era Archive"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
