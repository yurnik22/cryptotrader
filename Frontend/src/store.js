import { create } from "zustand";

export const useStore = create((set) => ({
  portfolio: { value: 0, pnl: 0 },
  bots: [],
  trades: [],
  wsStatus: "DISCONNECTED",

  setWsStatus: (status) => set({ wsStatus: status }),

  setState: (data) =>
    set((state) => ({
      portfolio: data.portfolio ?? state.portfolio,
      bots: Array.isArray(data.bots) ? data.bots : state.bots,
      trades: Array.isArray(data.trades) ? data.trades : state.trades,
    })),
}));