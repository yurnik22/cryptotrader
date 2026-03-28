export default function BotsCard({ bots }) {
  return (
    <div className="card">
      <h3>Bots</h3>

      {bots.map((b, i) => (
        <div key={i}>
          {b.name} — {b.status} — PnL {b.pnl}
        </div>
      ))}
    </div>
  );
}