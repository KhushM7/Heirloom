import React from "react"
import type { Metadata } from 'next'
import { Libre_Baskerville, Cormorant_Garamond } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'
import { ProfileProvider } from '@/lib/profile-context'

const _libreBaskerville = Libre_Baskerville({ 
  subsets: ["latin"],
  weight: ["400", "700"],
});
const _cormorantGaramond = Cormorant_Garamond({ 
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: 'Heirloom - Preserve Your Family Legacy',
  description: 'Connect with your ancestors through preserved memories and stories',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/logo.svg',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/logo.svg',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/logo.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`font-sans antialiased`} suppressHydrationWarning>
        <ProfileProvider>{children}</ProfileProvider>
        <Analytics />
      </body>
    </html>
  )
}
