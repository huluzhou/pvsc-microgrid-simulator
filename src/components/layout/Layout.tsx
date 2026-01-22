import { ReactNode } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import StatusBar from "./StatusBar";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto bg-white">
          {children}
        </main>
      </div>
      <StatusBar />
    </div>
  );
}
