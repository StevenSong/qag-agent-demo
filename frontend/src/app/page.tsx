"use client";

import { useRenderToolCall, CatchAllActionRenderProps } from "@copilotkit/react-core";
import {
  CopilotKitCSSProperties,
  CopilotChat,
  AssistantMessageProps,
  Markdown,
} from "@copilotkit/react-ui";
import { useState, useEffect, useRef, useCallback } from "react";

const HEADER_SENTINEL = "HEADER_TEXT";

// ─── Thinking block component ─────────────────────────────────────────────────

function ThinkingBlock({ content }: { content: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-2 rounded-lg border border-purple-200 bg-purple-50 text-sm overflow-hidden">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left font-medium text-purple-700 hover:bg-purple-100 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="text-base">💭</span>
        <span className="flex-1">Thinking...</span>
        <span className="text-purple-400 text-xs">{open ? "▲ hide" : "▼ show"}</span>
      </button>
      {open && (
        <pre className="px-3 pb-3 pt-1 text-purple-900 whitespace-pre-wrap text-xs leading-relaxed border-t border-purple-200">
          {content}
        </pre>
      )}
    </div>
  );
}

// ─── Generic tool call card ───────────────────────────────────────────────────
//
// Works for any tool: pass `name`, `args`, and optionally `result`.
// When `result` is undefined/null the card shows an animated "running…" badge.

function ToolCallCard({
  name,
  args,
  result,
}: {
  name: string;
  args: Record<string, unknown>;
  result: unknown;
}) {
  const [open, setOpen] = useState(false);
  const isPending = result === undefined || result === null;

  return (
    <div className="my-2 rounded-lg border border-blue-200 bg-blue-50 text-sm overflow-hidden">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left font-medium text-blue-700 hover:bg-blue-100 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="text-base">🔧</span>
        <span className="flex-1 font-mono">{name}</span>
        {isPending && (
          <span className="text-xs text-blue-400 animate-pulse">running…</span>
        )}
        <span className="text-blue-400 text-xs">{open ? "▲ hide" : "▼ show"}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 border-t border-blue-200 space-y-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-500 mb-1">
              Parameters
            </p>
            <pre className="text-xs text-blue-900 whitespace-pre-wrap bg-white/60 rounded p-2">
              {JSON.stringify(args, null, 2)}
            </pre>
          </div>
          {!isPending && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-500 mb-1">
                Result
              </p>
              <pre className="text-xs text-blue-900 whitespace-pre-wrap bg-white/60 rounded p-2">
                {typeof result === "string"
                  ? result
                  : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CopilotKitPage() {
  const thinkingBlocksRef = useRef<string[]>([]);
  const thinkingConsumeRef = useRef(0);
  const assistantIndexMap = useRef<Map<string, number>>(new Map());
  const assistantCountRef = useRef(0);
  const [, forceUpdate] = useState(0);

  // Intercept the SSE stream to pull out thinking blocks in arrival order.
  useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const response = await originalFetch(...args);
      const url =
        typeof args[0] === "string" ? args[0] : (args[0] as Request).url;
      if (!url.includes("/api/copilotkit")) return response;

      const [stream1, stream2] = response.body!.tee();
      const reader = stream2.getReader();
      const decoder = new TextDecoder();

      (async () => {
        try {
          let accumulated = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const text = decoder.decode(value, { stream: true });
            for (const line of text.split("\n")) {
              if (!line.startsWith("data:")) continue;
              try {
                const json = JSON.parse(line.slice(5).trim());
                const type: string = json.type ?? "";
                if (type === "THINKING_TEXT_MESSAGE_START") {
                  accumulated = "";
                } else if (type === "THINKING_TEXT_MESSAGE_CONTENT") {
                  accumulated += json.delta ?? "";
                } else if (type === "THINKING_TEXT_MESSAGE_END") {
                  if (accumulated) {
                    thinkingBlocksRef.current = [
                      ...thinkingBlocksRef.current,
                      accumulated,
                    ];
                    accumulated = "";
                    forceUpdate((n) => n + 1);
                  }
                }
              } catch {
                /* not JSON */
              }
            }
          }
        } catch {
          /* stream closed */
        }
      })();

      return new Response(stream1, {
        headers: response.headers,
        status: response.status,
        statusText: response.statusText,
      });
    };
    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  // Stable component — consumes thinking blocks in FIFO order as messages render.
  const AssistantMessage = useCallback((props: AssistantMessageProps) => {
    const msg = props.message as unknown as {
      id?: string;
      content?: string;
      toolCalls?: unknown[];
    } | null;

    const text = msg?.content ?? "";
    const msgId = msg?.id ?? "";
    const p = props as unknown as Record<string, unknown>;
    const toolComponent =
      (p.component as React.ReactNode) ??
      (p.subComponent as React.ReactNode) ??
      null;
    const { isLoading, isGenerating } = props;

    if (
      msgId &&
      msgId !== HEADER_SENTINEL &&
      !assistantIndexMap.current.has(msgId)
    ) {
      assistantIndexMap.current.set(msgId, assistantCountRef.current++);
    }
    const idx = msgId ? (assistantIndexMap.current.get(msgId) ?? -1) : -1;
    const thinking = idx >= 0 ? thinkingBlocksRef.current[idx] : undefined;

    if (text === HEADER_SENTINEL) {
      return (
        <div className="mx-4 my-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm text-center">
          <h1 className="text-2xl font-semibold text-gray-800 mb-2">
            🧬 GDC QAG 🔬
          </h1>
          <p className="text-gray-500 text-sm">Ask me a question!</p>
        </div>
      );
    }

    return (
      <div>
        {thinking !== undefined && <ThinkingBlock content={thinking} />}

        {text && (
          <div className="copilotKitMessage copilotKitAssistantMessage">
            <Markdown content={text} />
          </div>
        )}

        {toolComponent}

        {(isLoading || isGenerating) && !text && !toolComponent && (
          <div className="copilotKitMessage copilotKitAssistantMessage">
            <span className="animate-pulse">…</span>
          </div>
        )}
      </div>
    );
  }, []);

  return (
    <main
      className="h-screen flex flex-col"
      style={
        { "--copilot-kit-primary-color": "#6366f1" } as CopilotKitCSSProperties
      }
    >
      <MainContent AssistantMessage={AssistantMessage} />
    </main>
  );
}

// ─── Main content ─────────────────────────────────────────────────────────────

function MainContent({
  AssistantMessage,
}: {
  AssistantMessage: React.ComponentType<AssistantMessageProps>;
}) {
  // Cast to `any` on the config object to satisfy the v1 type constraint on `name`,
  // which incorrectly excludes "*" at the type level despite supporting it at runtime.
  // The render props are typed via CatchAllActionRenderProps which correctly includes `name`.
  useRenderToolCall({
    name: "*",
    render: (props: CatchAllActionRenderProps) => {
      const { name, args, result, status } = props;
      return (
        <ToolCallCard
          name={name}
          args={args as Record<string, unknown>}
          result={status === "complete" ? result : undefined}
        />
      );
    },
  } as any);

  return (
    <CopilotChat
      className="flex-1 min-h-0 max-w-3xl mx-auto w-full"
      AssistantMessage={AssistantMessage}
      labels={{
        title: "Assistant",
        initial: HEADER_SENTINEL,
      }}
    />
  );
}
