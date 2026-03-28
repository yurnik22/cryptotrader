export async function stopBuying() {
  await fetch("http://localhost:8000/control/stop-buying", {
    method: "POST"
  });
}