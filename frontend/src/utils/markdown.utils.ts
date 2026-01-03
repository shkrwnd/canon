export const sanitizeMarkdown = (markdown: string): string => {
  // Basic sanitization - in production, use a proper markdown sanitizer
  return markdown;
};

export const extractTitleFromMarkdown = (markdown: string): string => {
  // Extract first heading or first line
  const lines = markdown.split("\n");
  for (const line of lines) {
    if (line.startsWith("#")) {
      return line.replace(/^#+\s*/, "").trim();
    }
  }
  return lines[0]?.trim() || "Untitled";
};





