import { useEffect, useState } from "react";
import { api, type Company, type Health } from "./lib/api";
import { Shell } from "./components/Shell";
import { Opportunities } from "./pages/Opportunities";
import { Chat } from "./pages/Chat";

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const on = () => setHash(window.location.hash);
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash;
}

export default function App() {
  const [company, setCompany] = useState<Company>("A");
  const [health, setHealth] = useState<Health | null>(null);
  const hash = useHashRoute();
  const active: "oportunidades" | "chat" = hash === "#/chat" ? "chat" : "oportunidades";

  useEffect(() => {
    let alive = true;
    api
      .health()
      .then((h) => {
        if (alive) setHealth(h);
      })
      .catch(() => {
        if (alive) setHealth(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <Shell company={company} onCompany={setCompany} health={health} active={active}>
      {active === "chat" ? (
        <Chat company={company} health={health} />
      ) : (
        <Opportunities company={company} />
      )}
    </Shell>
  );
}
