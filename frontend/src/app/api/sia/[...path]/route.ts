import { NextRequest } from "next/server";

import { proxySiaRequest } from "../../../../lib/server/sia-proxy";

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

async function handle(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxySiaRequest(request, path);
}

export const GET = handle;
export const HEAD = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
