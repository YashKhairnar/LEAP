import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { WORKSHOP_HREF, showLessonPaths } from "@/features/workshop/lib/visibility";

export function proxy(request: NextRequest) {
  if (!request.cookies.has("leap_session")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  // While only the workshop is shown, the other learning paths are hidden.
  const path = request.nextUrl.pathname;
  if (!showLessonPaths && path.startsWith("/learn/") && path !== WORKSHOP_HREF && !path.startsWith(`${WORKSHOP_HREF}/`)) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/learn/:path*"],
};
