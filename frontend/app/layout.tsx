import "./globals.css";
import {AppShell} from "@/components/layout/AppShell";import {PortfolioProvider} from "@/context/PortfolioContext";
export const metadata={title:"PortfolioIQ",description:"Cloud-native portfolio analytics and investment intelligence"};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><PortfolioProvider><AppShell>{children}</AppShell></PortfolioProvider></body></html>}
