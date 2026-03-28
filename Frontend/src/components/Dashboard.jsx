import PortfolioCard from "./PortfolioCard";
import TradesFeed from "./TradesFeed";
import ControlPanel from "./ControlPanel";
import { useStore } from "../store";
import BotsCard from "./BotsCard";

export default function Dashboard() {
  //const bots = useStore((state) => state.bots);
  const bots='bot';

  return (
    <>
      <PortfolioCard />
      <BotsCard bots={bots} />
      <TradesFeed />
      <ControlPanel />
    </>
  );
}