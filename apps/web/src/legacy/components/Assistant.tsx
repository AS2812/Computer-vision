import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Send, Sparkles, User, X } from "lucide-react";
import { api } from "../api";
import { copy } from "../i18n";
import type { LocalizedText } from "../types";

interface Message {
  role: "user" | "assistant";
  text: string;
  mode?: string;
  sources?: string[];
}

// Online providers may return light Markdown; strip the symbols for the chat bubble.
function clean(text: string): string {
  return (text ?? "")
    .replace(/\*\*|__|`/g, "")
    .replace(/^#{1,6}\s*/gm, "")
    .trim();
}

export function Assistant({
  analysisId,
  arabic,
  quickQuestions
}: {
  analysisId?: string;
  arabic: boolean;
  quickQuestions?: LocalizedText[];
}) {
  const t = copy[arabic ? "ar" : "en"];
  const lang = arabic ? "ar" : "en";
  const prompts = quickQuestions?.map((item) => arabic ? item.ar : item.en) ?? t.assistantQuickQuestions;
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const node = threadRef.current;
    if (node && typeof node.scrollTo === "function") {
      node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
    }
  }, [messages, loading, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    setMessages([]);
    setQuestion("");
  }, [analysisId]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const lastMode = [...messages].reverse().find((m) => m.role === "assistant")?.mode;
  const modeLabel =
    lastMode === "external-grounded-assistant"
      ? t.assistantOnline
      : lastMode === "offline-grounded-template"
        ? t.assistantLocal
        : lastMode === "error"
          ? t.assistantOffline
          : t.assistantReady;

  async function ask(rawText: string) {
    const text = rawText.trim();
    if (!text || loading) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setQuestion("");
    setLoading(true);
    try {
      const response = await api.assistant(text, analysisId, lang);
      setMessages((prev) => [...prev, {
        role: "assistant",
        text: clean(response.answer),
        mode: response.mode,
        sources: response.sources
      }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: t.assistantError, mode: "error" }]);
    } finally {
      setLoading(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(question);
  }

  return (
    <>
      <button
        className={`chat-fab ${open ? "is-hidden" : ""}`}
        onClick={() => setOpen(true)}
        aria-label={t.openChat}
      >
        <span className="chat-fab-orb"><Bot size={22} /></span>
        <span className="chat-fab-label">{t.openChat}</span>
        <Sparkles size={15} className="chat-fab-spark" />
      </button>

      <div className={`chat-backdrop ${open ? "show" : ""}`} onClick={() => setOpen(false)} aria-hidden="true" />

      <aside className={`chat-drawer ${open ? "open" : ""}`} dir={arabic ? "rtl" : "ltr"} aria-hidden={!open}>
        <header className="chat-drawer-head">
          <div className="assistant-orb floaty"><Bot size={20} /></div>
          <div className="chat-drawer-title">
            <p className="eyebrow">{t.assistantEyebrow}</p>
            <h2>{t.assistantTitle}</h2>
            <span className="assistant-mode"><i className={`mode-dot ${lastMode === "external-grounded-assistant" ? "live" : ""}`} /> {modeLabel}</span>
          </div>
          <button className="chat-close" onClick={() => setOpen(false)} aria-label={t.closeChat}><X size={18} /></button>
        </header>

        <div className="assistant-thread" ref={threadRef}>
          {messages.length === 0 && <p className="assistant-greeting">{t.assistantGreeting}</p>}
          {messages.length === 0 && (
            <div className="assistant-quick-questions">
              {prompts.map((prompt) => (
                <button key={prompt} type="button" onClick={() => void ask(prompt)}>{prompt}</button>
              ))}
            </div>
          )}
          {messages.map((message, index) => (
            <div key={index} className={`chat-row chat-${message.role}`}>
              <span className="chat-avatar">{message.role === "user" ? <User size={15} /> : <Bot size={15} />}</span>
              <div className="chat-bubble">
                <small>{message.role === "user" ? t.you : t.assistantName}</small>
                <p>{message.text}</p>
                {message.role === "assistant" && message.sources?.some((source) => source.startsWith("http")) && (
                  <div className="chat-sources">
                    {message.sources.filter((source) => source.startsWith("http")).map((source) => (
                      <a key={source} href={source} target="_blank" rel="noreferrer">Reviewed source</a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-row chat-assistant">
              <span className="chat-avatar"><Bot size={15} /></span>
              <div className="chat-bubble"><p className="chat-typing"><i /><i /><i /></p></div>
            </div>
          )}
        </div>

        <form onSubmit={submit} className="assistant-form">
          <input
            ref={inputRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t.assistantPlaceholder}
          />
          <button type="submit" disabled={loading} aria-label="Send question"><Send size={18} /></button>
        </form>
      </aside>
    </>
  );
}
