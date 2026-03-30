import MarkdownIt from "markdown-it";

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: true,
});

const defaultLinkOpen =
  md.renderer.rules.link_open ||
  function (tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options);
  };
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  tokens[idx].attrSet("target", "_blank");
  tokens[idx].attrSet("rel", "noopener noreferrer");
  return defaultLinkOpen(tokens, idx, options, env, self);
};

/** Render markdown to HTML for v-html (html: false disallows raw HTML in source). */
export function renderMarkdown(text: string | undefined): string {
  if (!text?.trim()) {
    return "";
  }
  return md.render(text);
}

/**
 * Turn prose [1], [2] markers (Wikipedia-style) into links to reference list anchors.
 * Safe to run after markdown render; avoids matching markdown link syntax because those become <a> tags.
 */
export function linkifyCitationMarkers(html: string, idPrefix: string): string {
  return html.replace(/\[(\d+)\]/g, (_, digits: string) => {
    const n = String(digits);
    return `<a href="#${idPrefix}-ref-${n}" class="wiki-cite-link"><sup class="wiki-cite">${n}</sup></a>`;
  });
}

/** Markdown body + Wikipedia-style numeric refs linked to #idPrefix-ref-n. */
export function renderWikiCitedMarkdown(text: string | undefined, idPrefix: string): string {
  if (!text?.trim()) {
    return "";
  }
  return linkifyCitationMarkers(md.render(text), idPrefix);
}
