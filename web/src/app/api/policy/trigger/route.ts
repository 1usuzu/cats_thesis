import { proxyRequest } from "@/lib/api-proxy";
export async function POST(request: Request) { return proxyRequest(process.env.ORCHESTRATOR_URL ? `${process.env.ORCHESTRATOR_URL}/policy/trigger` : "http://localhost:8080/policy/trigger", request); }
