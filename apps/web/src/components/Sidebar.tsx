// Persistent sidebar: crop disease grounded assistant.
// It answers questions grounded only in the reviewed Egyptian crop disease knowledge base.
// Bouncing dot typing indicator is displayed while thinking/pending.

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Bot, LoaderCircle, MessageCircle, Send } from "lucide-react";
import type { AppAnalysis } from "../appTypes";
import type { Bi, Lang } from "../data/diseases";
import { askCropBot } from "../lib/cropBot";

const tr = (bi: Bi, lang: Lang) => bi[lang];

const QUICK: Bi[] = [
  { en: "Give me the best treatment and online prices", ar: "هات أفضل علاج وأسعار أونلاين" },
  { en: "Compare the treatment options for my case", ar: "قارن بدائل العلاج لحالتي" },
  { en: "What should I do today and this week?", ar: "أعمل إيه النهارده والأسبوع ده؟" },
  { en: "How do I prevent it next season?", ar: "أمنعه إزاي الموسم الجاي؟" },
];

function cleanLatex(value: string): string {
  return value
    .replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, "($1) / ($2)")
    .replace(/\\times/g, "×")
    .replace(/\\cdot/g, "·")
    .replace(/\\leq?/g, "≤")
    .replace(/\\geq?/g, "≥")
    .replace(/\\neq/g, "≠")
    .replace(/\\approx/g, "≈")
    .replace(/\\pm/g, "±")
    .replace(/\\%/g, "%")
    .replace(/\\text\{([^{}]+)\}/g, "$1")
    .trim();
}

function renderInlineText(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\\\((.+?)\\\)|\\\[(.+?)\\\]|\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$|\*\*([^*]+?)\*\*|`([^`]+?)`)/g;
  let lastIndex = 0;
  let index = 0;
  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > lastIndex) nodes.push(text.slice(lastIndex, start));
    const math = match[2] ?? match[3] ?? match[4] ?? match[5];
    const bold = match[6];
    const code = match[7];
    if (math) {
      nodes.push(
        <span key={`${keyPrefix}-m-${index}`} className="assistant-math-inline" dir="ltr">
          {cleanLatex(math)}
        </span>,
      );
    } else if (bold) {
      nodes.push(<strong key={`${keyPrefix}-b-${index}`}>{renderInlineText(bold, `${keyPrefix}-b-${index}`)}</strong>);
    } else if (code) {
      nodes.push(<code key={`${keyPrefix}-c-${index}`} className="assistant-inline-code">{code}</code>);
    }
    lastIndex = start + match[0].length;
    index += 1;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

function listItem(line: string): { ordered: boolean; text: string } | null {
  const ordered = line.match(/^\s*(?:\d+|[٠-٩]+|[۰-۹]+)[.)،:-]\s*(.+)$/);
  if (ordered) return { ordered: true, text: ordered[1].trim() };
  const bullet = line.match(/^\s*[-*•]\s+(.+)$/);
  if (bullet) return { ordered: false, text: bullet[1].trim() };
  return null;
}

function FormattedAssistantText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let activeList: { ordered: boolean; items: string[] } | null = null;

  const flushList = () => {
    if (!activeList) return;
    const Tag = activeList.ordered ? "ol" : "ul";
    const items = activeList.items;
    blocks.push(
      <Tag key={`list-${blocks.length}`} className="assistant-rich-list">
        {items.map((item, i) => (
          <li key={i}>{renderInlineText(item, `li-${blocks.length}-${i}`)}</li>
        ))}
      </Tag>,
    );
    activeList = null;
  };

  text.split(/\r?\n/).forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      return;
    }
    const displayMath = line.match(/^(?:\$\$|\\\[)([\s\S]+?)(?:\$\$|\\\])$/);
    if (displayMath) {
      flushList();
      blocks.push(
        <div key={`math-${blocks.length}`} className="assistant-math-block" dir="ltr">
          {cleanLatex(displayMath[1])}
        </div>,
      );
      return;
    }
    const item = listItem(line);
    if (item) {
      if (!activeList || activeList.ordered !== item.ordered) flushList();
      activeList = activeList ?? { ordered: item.ordered, items: [] };
      activeList.items.push(item.text);
      return;
    }
    flushList();
    blocks.push(
      <p key={`p-${blocks.length}`} className="assistant-rich-p">
        {renderInlineText(line, `p-${blocks.length}`)}
      </p>,
    );
  });
  flushList();

  return <div className="assistant-rich">{blocks}</div>;
}

export function Sidebar({
  analysis,
  lang,
}: {
  analysis: AppAnalysis | null;
  lang: Lang;
}) {
  const [thread, setThread] = useState<Array<{ id: number; q: string; a: string; mode?: string; pending?: boolean; online?: boolean }>>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread]);

  async function ask(q: string) {
    if (!q.trim()) return;
    const id = Date.now();
    setThread((t) => [
      ...t,
      {
        id,
        q,
        a: lang === "ar"
          ? "بفحص الحالة كاملة مع الأسعار المتاحة أونلاين وقواعد العلاج..."
          : "Checking the full case with available online prices and treatment rules...",
        mode: lang === "ar" ? "متصل بالـ API" : "online API",
        pending: true,
        online: true,
      },
    ]);
    setInput("");
    const result = await askCropBot(q, analysis, lang);
    setThread((t) =>
      t.map((m) =>
        m.id === id
          ? {
              ...m,
              a: result?.answer ?? (lang === "ar"
                ? "تعذر الوصول للمساعد. حاول مرة أخرى."
                : "Assistant unavailable. Please try again."),
              mode: result?.mode ?? "api-unavailable",
              pending: false,
              online: result?.mode === "external-grounded-assistant",
            }
          : m,
      ),
    );
  }

  return (
    <div className="flex flex-1 flex-col justify-between min-h-0 h-full overflow-hidden gap-3">
      {/* Thread list / Welcome Greeting */}
      {thread.length === 0 ? (
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col justify-start sm:justify-center items-center text-center p-2 sm:p-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-400/10 text-emerald-300 mb-3 animate-[pulse_2s_infinite]">
            <Bot size={24} />
          </div>
          <h3 className="text-sm font-bold text-emerald-50">{lang === "ar" ? "مساعد الحالة الزراعي" : "Case Crop Assistant"}</h3>
          <p className="mt-1.5 text-[11px] leading-relaxed text-emerald-100/50 max-w-[280px]">
            {lang === "ar"
              ? "يساعدك في حالة الطماطم الحالية فقط: تشخيص، علاج، أسعار، وقاية، ري، اقتصاديات، وسلامة."
              : "Helps only with this tomato case: diagnosis, treatment, prices, prevention, irrigation, economics, and safety."}
          </p>
          <div className="mt-6 w-full max-w-[320px] text-start">
            <span className="text-[10px] uppercase font-bold text-emerald-200/40 block mb-2 px-1">
              {lang === "ar" ? "أسئلة مقترحة" : "Suggested questions"}
            </span>
            <div className="grid gap-2">
              {QUICK.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => void ask(tr(q, lang))}
                  className="w-full text-start rounded-xl border border-white/5 bg-white/5 px-3 py-2.5 text-xs text-emerald-100/90 hover:border-emerald-400/30 hover:bg-emerald-400/5 transition cursor-pointer"
                >
                  {tr(q, lang)}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 min-h-0 overflow-y-auto space-y-4 pr-1 pb-2">
          {thread.map((m, i) => (
            <div key={i} className="space-y-2">
              {/* User Bubble */}
              <div className="flex justify-end animate-rise">
                <div className="max-w-[85%] break-words rounded-2xl rounded-tr-none border border-emerald-500/20 bg-emerald-500/15 px-4 py-2.5 text-emerald-50 text-xs leading-relaxed shadow-sm">
                  {m.q}
                </div>
              </div>
              {/* Bot Bubble */}
              <div className="flex gap-2.5 items-start justify-start animate-rise">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-400/20 text-emerald-300">
                  <Bot size={15} />
                </div>
                <div className="flex-1 max-w-[85%] min-w-0 break-words rounded-2xl rounded-tl-none border border-white/5 bg-white/5 px-4 py-2.5 text-emerald-50/90 text-xs shadow-sm">
                  {m.pending ? (
                    <div className="py-1">
                      <div className="chat-typing">
                        <i />
                        <i />
                        <i />
                      </div>
                    </div>
                  ) : (
                    <FormattedAssistantText text={m.a} />
                  )}
                  
                  <div className="mt-2 flex items-center gap-1.5 text-[9px] text-emerald-200/40">
                    {m.pending && <LoaderCircle size={10} className="animate-spin text-sky-300" />}
                    {!m.pending && (
                      <MessageCircle
                        size={10}
                        className={
                          m.online
                            ? "text-sky-300"
                            : m.mode === "offline-template"
                              ? "text-violet-400"
                              : "text-amber-300"
                        }
                      />
                    )}
                    <span>
                      {m.pending
                        ? (lang === "ar" ? "بيفكر أونلاين..." : "thinking online...")
                        : m.online
                          ? (lang === "ar" ? "إجابة API أونلاين مبنية على الحالة" : "online API answer grounded in the case")
                          : m.mode === "offline-template"
                            ? (lang === "ar" ? "إجابة محلية من قاعدة البيانات (أوفلاين)" : "local KB answer (offline)")
                            : m.mode === "api-unavailable"
                              ? (lang === "ar" ? "تعذر الاتصال الأونلاين" : "online unavailable")
                              : (lang === "ar" ? "إجابة حالة موثوقة" : "grounded case answer")}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input area stuck to bottom */}
      <form onSubmit={(e) => { e.preventDefault(); void ask(input); }} className="shrink-0 mt-auto pt-3 border-t border-white/10 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={lang === "ar" ? "اسأل عن علاج وأسعار ووقاية حالة الطماطم..." : "Ask about treatment, prices, prevention..."}
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-xs text-emerald-50 placeholder:text-emerald-200/30 focus:border-emerald-400/40 focus:outline-none focus:ring-1 focus:ring-emerald-400/20"
        />
        <button type="submit" className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-emerald-400/20 text-emerald-300 hover:bg-emerald-400/30 transition cursor-pointer">
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
