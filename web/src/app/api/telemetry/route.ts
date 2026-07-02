import { proxyRequest } from "@/lib/api-proxy";
export async function GET(request: Request) { return proxyRequest(process.env.ORCHESTRATOR_URL ? `${process.env.ORCHESTRATOR_URL}/telemetry` : "http://localhost:8080/telemetry", request); }
