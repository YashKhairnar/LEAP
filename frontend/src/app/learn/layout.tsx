"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { validateAuth } from "@/lib/auth";

export default function LearningLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  useEffect(() => {
    let active = true;
    void validateAuth().then((user) => {
      if (!active) return;
      if (!user) { router.replace("/login"); return; }
      setAuthorized(true);
    });
    return () => { active = false; };
  }, [router]);
  return authorized ? children : <main className="auth-loading" aria-live="polite">Checking your LEAP session…</main>;
}
