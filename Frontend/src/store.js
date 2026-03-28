import { create } from "zustand";

export const useStore = create((set) => ({
  portfolio: { value: 0, pnl: 0 },
  bots: [],
  trades: [],
  wsStatus: "DISCONNECTED",
  setWsStatus: (status) => set({ wsStatus: status }),
  setState: (data) => set(data),
  addTrade: (trade) => set((state) => ({ trades: [trade, ...state.trades] }))
}));