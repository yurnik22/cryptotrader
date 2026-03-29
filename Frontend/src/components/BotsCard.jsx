export default function BotsCard({ bots }) {
  //console.log("BOTS =", bots, typeof bots);

  if (!Array.isArray(bots)) {
    return (
      <div className="card">
        <h3>Bots</h3>
        <div>No bots data</div>
      </div>
    );
  }

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