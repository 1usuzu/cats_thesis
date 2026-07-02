import { proxyRequest } from "@/lib/api-proxy";
export async function GET(request: Request) { return proxyRequest("http://localhost:8000/health/ready", request); }
