// src/App.jsx
import { useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import useSocket from "./useSocket";
import { useStore } from "./store";

export default function App() {
  // Zustand: функции для обновления состояния
  const setState = useStore((state) => state.setState);
  const setWsStatus = useStore((state) => state.setWsStatus);

  // Инициализация WebSocket через кастомный хук
  //useSocket(
  //  (data) => setState(data),       // callback для обновления портфеля / ботов / трейдов
  //  (status) => setWsStatus(status) // callback для статуса WS
  //);

  useSocket(
    (data) => {
      //console.log("APP RECEIVED:", data);
      setState(data);

      },
    (status) => setWsStatus(status)
  );

  return (
    <div className="layout" style={{ display: "flex", height: "100vh" }}>
      <Sidebar />
      <div className="content" style={{ flex: 1, padding: "20px" }}>
        <Dashboard />
      </div>
    </div>
  );
}