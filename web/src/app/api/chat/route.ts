import { proxyRequest } from "@/lib/api-proxy";
export async function POST(request: Request) { return proxyRequest(process.env.GATEWAY_URL ? `${process.env.GATEWAY_URL}/v1/chat` : "http://localhost:8000/v1/chat", request); }
