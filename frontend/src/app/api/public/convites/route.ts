import { NextRequest } from "next/server";

import { proxyPublicInvitation } from "../../../../lib/server/public-invitation-bff";

export const POST = (request: NextRequest) => proxyPublicInvitation(request);
