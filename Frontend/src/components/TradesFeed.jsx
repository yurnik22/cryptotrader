import { useStore } from "../store";

export default function TradesFeed() {
  const trades = useStore((state) => state.trades);

  return (
    <div className="card">
      <h3>Trades Feed</h3>
      {trades.map((t, i) => (
        <div key={i}>
          {t.time} — {t.pair} — {t.side} — ${t.price} x {t.amount}
        </div>
      ))}
    </div>
  );
}