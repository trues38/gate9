import "../globals.css";
import { Inter, JetBrains_Mono } from "next/font/google";
import { getTranslations } from 'next-intl/server';

const inter = Inter({ subsets: ["latin"] });
const mono = JetBrains_Mono({ subsets: ["latin"] });

export async function generateMetadata({ params: { locale } }: { params: { locale: string } }) {
  const t = await getTranslations({ locale, namespace: 'Metadata' });
  return {
    title: "REGIME PRO",
    description: "The Bloomberg Terminal for Sports Bettors"
  };
}

export default function RootLayout({
  children,
  params: { locale }
}: Readonly<{
  children: React.ReactNode;
  params: { locale: string };
}>) {
  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={`${inter.className} bg-[#050505] text-white`}>
        {children}
      </body>
    </html>
  );
}
