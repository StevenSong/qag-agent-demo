import type { Metadata } from "next";

import { CopilotKit } from "@copilotkit/react-core";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

export const metadata: Metadata = {
  title: "GDC QAG",
  description: "Query Augmented Generation for the NCI Genomic Data Commons",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={"antialiased"}>
        <CopilotKit
          runtimeUrl={`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/copilotkit`}
          agent="qag_agent"
          showDevConsole={false}
          enableInspector={false}
          publicApiKey="FAKE" // pragma: allowlist secret - disables the "powered by" footer
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
