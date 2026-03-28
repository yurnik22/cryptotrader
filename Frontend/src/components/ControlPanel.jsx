import { useStore } from "../store";

export default function ControlPanel() {
  const stopBot = () => alert("Stop bot clicked"); // позже подключим backend
  const startBot = () => alert("Start bot clicked");

  return (
    <div className="card">
      <h3>Control Panel</h3>
      <button className="danger" onClick={stopBot}>
        STOP ALL BOTS
      </button>
      <button style={{ marginLeft: "10px" }} onClick={startBot}>
        START ALL BOTS
      </button>
    </div>
  );
}