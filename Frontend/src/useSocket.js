// src/useSocket.js
import { useEffect, useRef } from "react";

export default function useSocket(onMessage, onStatus) {
  const wsRef = useRef(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket("ws://127.0.0.1:8000/ws"); // или ws://localhost:8000/ws
      wsRef.current = ws;

      // статус соединения
      onStatus("CONNECTING");

      ws.onopen = () => {
        console.log("WS connected");
        onStatus("CONNECTED");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (err) {
          console.error("Invalid WS message", err);
        }
      };

      ws.onerror = () => {
        onStatus("ERROR");
        ws.close();
      };

      ws.onclose = () => {
        console.log("WS disconnected. Reconnecting in 2s...");
        onStatus("DISCONNECTED");
        setTimeout(connect, 2000);
      };
    }

    connect();

    return () => wsRef.current?.close(); // cleanup при unmount
  }, []);
}