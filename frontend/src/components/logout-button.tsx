"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { logout } from "@/lib/auth";

export default function LogoutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const signOut = async () => {
    setBusy(true);
    await logout();
    router.replace("/login");
    router.refresh();
  };
  return <button className="logout-button" disabled={busy} onClick={signOut}>{busy ? "Signing out…" : "Log out"}</button>;
}
