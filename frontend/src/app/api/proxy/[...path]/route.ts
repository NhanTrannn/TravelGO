import { NextRequest } from "next/server";

export const runtime = "nodejs";

const BACKEND = process.env.BACKEND_ORIGIN!;

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(req.url);
  const target = `${BACKEND}/${path.join("/")}${url.search}`;

  const resp = await fetch(target, {
    headers: { accept: req.headers.get("accept") ?? "*/*" },
    cache: "no-store",
  });

  return new Response(resp.body, { status: resp.status, headers: resp.headers });
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(req.url);
  const target = `${BACKEND}/${path.join("/")}${url.search}`;

  const resp = await fetch(target, {
    method: "POST",
    headers: {
      "content-type": req.headers.get("content-type") ?? "application/json",
      accept: req.headers.get("accept") ?? "*/*",
    },
    body: await req.arrayBuffer(),
    cache: "no-store",
  });

  return new Response(resp.body, { status: resp.status, headers: resp.headers });
}
