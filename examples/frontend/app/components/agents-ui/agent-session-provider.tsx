import type { ReactNode } from "react";
import { SessionProvider, type UseSessionReturn } from "@livekit/components-react";

type Props = {
  session: UseSessionReturn;
  children: ReactNode;
};

export function AgentSessionProvider({ session, children }: Props) {
  return <SessionProvider session={session}>{children}</SessionProvider>;
}
