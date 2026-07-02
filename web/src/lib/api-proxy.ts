import { NextResponse } from "next/server";

export async function proxyRequest(url: string, request: Request) {
  try {
    const init: RequestInit = {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
      }
    };

    const apiKey = request.headers.get("X-API-Key");
    if (apiKey) {
      (init.headers as Record<string, string>)["X-API-Key"] = apiKey;
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      const body = await request.text();
      if (body) {
        init.body = body;
      }
    }

    const response = await fetch(url, init);
    const data = await response.text();

    let parsedData;
    try {
      parsedData = JSON.parse(data);
    } catch {
      parsedData = data;
    }

    return NextResponse.json(parsedData, { status: response.status });
  } catch (error) {
    console.error(`Proxy Error to ${url}:`, error);
    return NextResponse.json({ error: "Internal Proxy Error" }, { status: 500 });
  }
}
