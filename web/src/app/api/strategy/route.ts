import { proxyRequest } from "@/lib/api-proxy";
export async function POST(request: Request) { return proxyRequest(process.env.GATEWAY_URL ? `${process.env.GATEWAY_URL}/admin/strategy` : "http://localhost:8000/admin/strategy", request); }
