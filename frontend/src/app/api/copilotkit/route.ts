import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();

let runtime: CopilotRuntime | null = null;

function getRuntime(): CopilotRuntime {
  if (!runtime) {
    const agentUrl = process.env.AGENT_URL;
    if (!agentUrl) {
      throw new Error("AGENT_URL environment variable is required");
    }
    runtime = new CopilotRuntime({
      agents: {
        qag_agent: new HttpAgent({ url: agentUrl }),
      },
    });
  }
  return runtime;
}

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime: getRuntime(),
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
