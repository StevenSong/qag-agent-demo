import { CopilotChat } from "@copilotkit/react-ui"; 

export default function Page() {
  return (
    <main>
      <h1>QAG Agent Demo</h1>
      <CopilotChat 
        labels={{
          placeholder: "Ask me a question about genomic variant statistics!",
        }}
      />
    </main>
  );
}
