import { NextRequest } from "next/server";

import { proxyPublicRegistration } from "../../../../../../lib/server/public-registration-bff";

interface RouteContext {
  params: Promise<{ publicId: string }>;
}

async function handle(request: NextRequest, context: RouteContext) {
  const { publicId } = await context.params;
  return proxyPublicRegistration(request, publicId);
}

export const GET = handle;
export const POST = handle;
