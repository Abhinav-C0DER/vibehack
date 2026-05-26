import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Vibehack | The Void",
  description: "Identity without footprint.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-void antialiased">
        {children}
      </body>
    </html>
  );
}
