import { proxyRequest } from "@/lib/api-proxy";
export async function GET(request: Request) { return proxyRequest(process.env.GATEWAY_URL ? `${process.env.GATEWAY_URL}/health/ready` : "http://localhost:8000/health/ready", request); }
