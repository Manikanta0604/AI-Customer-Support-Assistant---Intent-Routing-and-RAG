"use client";
import { FormEvent, useState } from "react";

type Citation = { source: string; section: string | null; passage: string; score: number };
type ChatMessage = { role: "user" | "assistant"; text: string; intent?: string; citations?: Citation[]; escalated?: boolean };
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [session, setSession] = useState<string>();
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: "assistant", text: "Hi, I’m Relay. Ask me about billing, account access, delivery, products, or technical problems." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = input.trim(); if (!text || busy) return;
    setMessages(items => [...items, { role: "user", text }]); setInput(""); setBusy(true);
    try {
      const response = await fetch(`${API}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, session_id: session }) });
      if (!response.ok) throw new Error("Support service is unavailable");
      const result = await response.json(); setSession(result.session_id);
      setMessages(items => [...items, { role: "assistant", text: result.answer, intent: result.intent, citations: result.citations, escalated: result.escalated }]);
    } catch (error) {
      setMessages(items => [...items, { role: "assistant", text: error instanceof Error ? error.message : "Something went wrong", escalated: true }]);
    } finally { setBusy(false); }
  }

  return <main>
    <nav><div className="brand"><span>R</span> Relay</div><div className="online"><i /> AI support online</div></nav>
    <section className="hero"><p className="kicker">CUSTOMER EXPERIENCE, GROUNDED IN EVIDENCE</p><h1>Support that knows<br/><em>when to listen.</em></h1><p>Intent-aware answers, verifiable sources, and a thoughtful handoff when a human should take over.</p></section>
    <section className="console">
      <aside><h2>Smart routing</h2><p>Every request is classified and sent through the right support path.</p>{["Billing","Technical","Account","Product","Complaint","General"].map(item => <div className="route" key={item}><span>{item[0]}</span>{item}</div>)}<div className="human">↗ Human escalation enabled</div></aside>
      <div className="chat">
        <div className="chathead"><div><strong>Relay Assistant</strong><small>{session ? `Session ${session.slice(0, 8)}` : "New conversation"}</small></div><span>Memory on</span></div>
        <div className="feed">{messages.map((message, index) => <div className={`message ${message.role}`} key={index}><div className="bubble">{message.intent && <b>{message.intent}</b>}<p>{message.text}</p>{message.escalated && <mark>Human handoff created</mark>}</div>{message.citations && message.citations.length > 0 && <div className="citations">{message.citations.map((citation, i) => <details key={i}><summary>[{i + 1}] {citation.source} · {Math.round(citation.score * 100)}%</summary><p>{citation.passage}</p></details>)}</div>}</div>)}</div>
        <form onSubmit={send}><input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask a support question…" /><button disabled={busy}>{busy ? "Thinking" : "Send"}</button></form>
      </div>
    </section>
  </main>;
}
