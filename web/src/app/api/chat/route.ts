import { proxyRequest } from "@/lib/api-proxy";
export async function POST(request: Request) { return proxyRequest("http://localhost:8000/v1/chat", request); }
