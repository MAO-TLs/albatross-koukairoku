import type { Metadata } from "next";
import "./globals.css";
import "./theme.css";
export const metadata: Metadata = {
  title: "Albatross Koukairoku | MAO",
  description: "Read the complete MAO English translation of Albatross Koukairoku beside its Japanese source.",
  metadataBase: new URL("https://mao-tls.github.io/albatross-koukairoku/"),
  robots: { index: true, follow: true },
};
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
