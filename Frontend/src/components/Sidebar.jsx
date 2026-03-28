import { useState } from "react";

export default function Sidebar() {
  const pages = ["Dashboard", "Portfolio", "Bots", "Analytics"];
  //const [active, setActive] = useState("Dashboard");
  const [active, setActive] = "Dashboard";

  return (
    <div className="sidebar">
      <h2>CryptoTrader</h2>
      {pages.map((p) => (
        <div
          key={p}
          onClick={() => setActive(p)}
          style={{
            padding: "10px",
            cursor: "pointer",
            background: active === p ? "#1f2937" : "transparent",
            borderRadius: "8px"
          }}
        >
          {p}
        </div>
      ))}
    </div>
  );
}