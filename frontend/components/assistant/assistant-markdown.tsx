import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const ALLOWED = ["p", "ul", "ol", "li", "strong", "em", "del", "code", "pre", "a", "br", "table", "thead", "tbody", "tr", "th", "td"];
export function AssistantMarkdown({ children }: { children: string }) {
  return <div className="assistant-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml allowedElements={ALLOWED} components={{
    a: ({ href, children: content }) => <a href={href} target="_blank" rel="noopener noreferrer">{content}</a>,
    table: ({ children: content }) => <div className="assistant-table-scroll"><table>{content}</table></div>,
  }}>{children}</ReactMarkdown></div>;
}
