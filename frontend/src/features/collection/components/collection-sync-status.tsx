"use client";

import { useEffect, useState } from "react";
import { collectionStatus, COLLECTION_STATUS_EVENT, flushCollectionQueue } from "@/features/collection/lib/collection";

export default function CollectionSyncStatus() {
  const [status, setStatus] = useState({ pending: 0, failed: 0 });
  const [message, setMessage] = useState("");
  const sync = async () => {
    try { await flushCollectionQueue(); setMessage(""); }
    catch { setMessage("Unable to sync. Keep this browser's data until your responses are saved."); }
  };
  useEffect(() => {
    const update = () => {
      try { setStatus(collectionStatus()); }
      catch { setMessage("Browser storage is unavailable or unreadable. Collection cannot be confirmed."); }
    };
    const timer = window.setTimeout(() => { update(); void sync(); }, 0);
    const retry = window.setInterval(() => { if (document.visibilityState === "visible") void sync(); }, 15000);
    window.addEventListener(COLLECTION_STATUS_EVENT, update);
    window.addEventListener("online", sync);
    window.addEventListener("storage", update);
    return () => { window.clearTimeout(timer); window.clearInterval(retry); window.removeEventListener(COLLECTION_STATUS_EVENT, update); window.removeEventListener("online", sync); window.removeEventListener("storage", update); };
  }, []);
  if (!status.pending && !status.failed && !message) return null;
  return <aside role="status" className="collection-sync-status">
    <span>{status.failed > 0 ? `${status.failed} record(s) need researcher review; copies are retained in this browser. ` : ""}{status.pending > 0 ? `${status.pending} record(s) waiting to sync. ` : ""}{message}</span>
    <button type="button" className="text-button" onClick={() => void sync()}>Retry sync</button>
  </aside>;
}
