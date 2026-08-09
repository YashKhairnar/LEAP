import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LEAP",
  description: "A guided path from Java programming to a Python machine-learning pipeline.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
