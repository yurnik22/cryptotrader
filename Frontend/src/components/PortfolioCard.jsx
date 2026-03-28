import { Line } from "react-chartjs-2";
import { useStore } from "../store";
import { useEffect, useState } from "react";

export default function PortfolioCard() {
  //const portfolio = useStore((state) => state.portfolio);
  const portfolio = {'value':1000};
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setHistory((prev) => [...prev.slice(-29), portfolio.value]);
  }, [portfolio.value]);

  const data = {
    labels: history.map((_, i) => i),
    datasets: [
      {
        label: "Portfolio Value",
        data: history,
        fill: false,
        borderColor: portfolio.pnl >= 0 ? "#22c55e" : "#ef4444"
      }
    ]
  };

  return (
    <div className="card">
      <h3>Portfolio</h3>
      <h1>${portfolio.value.toFixed(2)}</h1>
      <p style={{ color: portfolio.pnl >= 0 ? "#22c55e" : "#ef4444" }}>
        PnL: {portfolio.pnl}%
      </p>
      <Line data={data} />
    </div>
  );
}