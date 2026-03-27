import React, { useEffect, useState } from "react";

export default function App() {
  const [portfolio, setPortfolio] = useState({});

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/portfolio");
    ws.onmessage = (e) => setPortfolio(JSON.parse(e.data));
    return () => ws.close();
  }, []);

  const pauseBuying = async () => {
    await fetch("http://localhost:8000/api/pause_buying", { method: "POST" });
  };

  const resumeBuying = async () => {
    await fetch("http://localhost:8000/api/resume_buying", { method: "POST" });
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Live Portfolio</h2>
      <ul>
        {Object.entries(portfolio).map(([k,v]) => (
          <li key={k}>{k}: {v}</li>
        ))}
      </ul>
      <div style={{ marginTop: "20px" }}>
        <button onClick={pauseBuying} style={{ marginRight: "10px" }}>Pause Buying</button>
        <button onClick={resumeBuying}>Resume Buying</button>
      </div>
    </div>
  );
}