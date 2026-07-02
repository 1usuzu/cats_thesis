import { proxyRequest } from "@/lib/api-proxy";
export async function GET(request: Request) { return proxyRequest("http://localhost:8080/telemetry", request); }
