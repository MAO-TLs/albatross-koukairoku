import type { Metadata } from "next";
import { SITE_BASE_PATH } from "../site-target.mjs";
import "./globals.css";
import "./theme.css";
export const metadata: Metadata = {
  title: "Albatross Koukairoku | MAO",
  description: "Read the complete MAO English translation of Albatross Koukairoku beside its Japanese source.",
  metadataBase: new URL("https://mao-tls.github.io/albatross-koukairoku/"),
  robots: { index: true, follow: true },
  icons: {
    icon: [
      { url: `${SITE_BASE_PATH}/favicon.ico`, sizes: "16x16 32x32 48x48", type: "image/x-icon" },
      { url: `${SITE_BASE_PATH}/favicon.png`, sizes: "32x32", type: "image/png" },
      { url: `${SITE_BASE_PATH}/favicon.svg`, sizes: "any", type: "image/svg+xml" },
    ],
    apple: { url: `${SITE_BASE_PATH}/apple-touch-icon.png`, sizes: "180x180", type: "image/png" },
  },
};
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
