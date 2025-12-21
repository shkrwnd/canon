import React, { useCallback, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import Link from "@tiptap/extension-link";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import TurndownService from "turndown";
import { marked } from "marked";
import { Button } from "../ui";
import { Input } from "../ui/input";
import { fixMarkdownTables } from "../../utils/markdownUtils";
import { 
  Bold, 
  Italic, 
  List, 
  ListOrdered, 
  Heading1, 
  Heading2, 
  Heading3,
  Quote,
  Code,
  Table as TableIcon,
  Link as LinkIcon,
  Strikethrough,
  Minus,
  CheckSquare
} from "lucide-react";

// Configure marked to support GitHub Flavored Markdown (GFM) including tables
marked.setOptions({
  gfm: true,
  breaks: false,
});

// Configure marked renderer to add target="_blank" to all links
const renderer = new marked.Renderer();
const originalLink = renderer.link.bind(renderer);
renderer.link = (href: string, title: string | null, text: string) => {
  const link = originalLink(href, title, text);
  // Add target="_blank" and rel="noopener noreferrer" to links
  return link.replace('<a ', '<a target="_blank" rel="noopener noreferrer" ');
};
marked.setOptions({ renderer });

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string;
}

// Initialize Turndown for HTML to Markdown conversion
const turndownService = new TurndownService({
  headingStyle: "atx",
  codeBlockStyle: "fenced",
});

// Add task list support to Turndown
turndownService.addRule("taskList", {
  filter: function (node) {
    return node.nodeName === "UL" && (
      node.hasAttribute("data-type") && node.getAttribute("data-type") === "taskList"
    );
  },
  replacement: function (content) {
    return "\n" + content + "\n";
  },
});

turndownService.addRule("taskItem", {
  filter: function (node) {
    return node.nodeName === "LI" && node.hasAttribute("data-type") && node.getAttribute("data-type") === "taskItem";
  },
  replacement: function (content, node) {
    const input = node.querySelector('input[type="checkbox"]');
    const checked = input && (input as HTMLInputElement).checked;
    const prefix = checked ? "- [x]" : "- [ ]";
    // Get text content, excluding the checkbox label
    const textContent = Array.from(node.childNodes)
      .filter((n) => n.nodeType === 3 || (n.nodeName !== "LABEL" && n.nodeName !== "INPUT"))
      .map((n) => n.textContent || "")
      .join("")
      .trim();
    return prefix + " " + textContent + "\n";
  },
});

// Add table support to Turndown
turndownService.addRule("table", {
  filter: "table",
  replacement: function (content, node) {
    const table = node as HTMLTableElement;
    const rows: string[] = [];
    
    // Process header row
    const thead = table.querySelector("thead");
    if (thead) {
      const headerRow = thead.querySelector("tr");
      if (headerRow) {
        const cells = Array.from(headerRow.querySelectorAll("th, td"))
          .map((cell) => {
            const text = turndownService.turndown(cell.innerHTML).trim();
            return text.replace(/\n/g, " ");
          });
        rows.push("| " + cells.join(" | ") + " |");
        rows.push("| " + cells.map(() => "---").join(" | ") + " |");
      }
    }
    
    // Process body rows
    const tbody = table.querySelector("tbody") || table;
    const bodyRows = tbody.querySelectorAll("tr");
    bodyRows.forEach((row) => {
      const cells = Array.from(row.querySelectorAll("td, th"))
        .map((cell) => {
          const text = turndownService.turndown(cell.innerHTML).trim();
          return text.replace(/\n/g, " ");
        });
      rows.push("| " + cells.join(" | ") + " |");
    });
    
    // Ensure proper spacing - tables need blank lines before and after
    const tableMarkdown = rows.join("\n");
    // Add extra newlines to ensure it's not treated as inline content
    return "\n\n" + tableMarkdown + "\n\n";
  },
});

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  height = "100%",
}) => {
  const [linkUrl, setLinkUrl] = useState("");
  const [linkText, setLinkText] = useState("");
  const [showLinkDialog, setShowLinkDialog] = useState(false);

  const handleUpdate = useCallback((editor: any) => {
    // Convert HTML to Markdown
    const html = editor.getHTML();
    const markdown = turndownService.turndown(html);
    onChange(markdown);
  }, [onChange]);

  // Helper to ensure all links have target="_blank"
  const ensureLinksOpenInNewTab = useCallback((html: string): string => {
    // Use a temporary DOM element to parse and modify HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const links = tempDiv.querySelectorAll('a');
    links.forEach((link) => {
      if (!link.getAttribute('target')) {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noopener noreferrer');
      }
    });
    return tempDiv.innerHTML;
  }, []);

  // Convert markdown to HTML for initial content
  const getInitialContent = useCallback((markdown: string) => {
    if (!markdown || markdown.trim() === "") {
      return "";
    }
    try {
      // Ensure tables are properly formatted before parsing
      const processedMarkdown = fixMarkdownTables(markdown);
      const html = marked.parse(processedMarkdown) as string;
      // Ensure all links open in new tab
      return ensureLinksOpenInNewTab(html);
    } catch (e) {
      console.error('Markdown parsing error:', e);
      return markdown;
    }
  }, [ensureLinksOpenInNewTab]);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
        strike: {},
        horizontalRule: {},
      }),
      Link.extend({
        addAttributes() {
          return {
            ...this.parent?.(),
            target: {
              default: "_blank",
            },
            rel: {
              default: "noopener noreferrer",
            },
          };
        },
      }).configure({
        openOnClick: false,
        HTMLAttributes: {
          class: "text-blue-600 underline cursor-pointer",
        },
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      TaskList.configure({
        HTMLAttributes: {
          class: "contains-task-list",
        },
      }),
      TaskItem.configure({
        nested: true,
        HTMLAttributes: {
          class: "task-list-item",
        },
      }),
      Placeholder.configure({
        placeholder: "Start writing...",
      }),
    ],
    content: getInitialContent(value),
    onUpdate: ({ editor }) => {
      handleUpdate(editor);
    },
    editorProps: {
      attributes: {
        class: "prose prose-sm max-w-none focus:outline-none min-h-full",
      },
    },
  });

  // Convert markdown to HTML when value changes externally
  React.useEffect(() => {
    if (editor && value !== undefined) {
      const currentHtml = editor.getHTML();
      let currentMarkdown = "";
      try {
        currentMarkdown = turndownService.turndown(currentHtml);
      } catch (e) {
        // If conversion fails, compare HTML directly
        currentMarkdown = currentHtml;
      }
      
      // Only update if the markdown actually changed (avoid infinite loops)
      if (value !== currentMarkdown) {
        if (value === "" || !value) {
          // Clear editor if value is empty
          editor.commands.clearContent(false);
        } else {
          // Convert markdown to HTML for Tiptap
          try {
            const processedMarkdown = fixMarkdownTables(value);
            const html = marked.parse(processedMarkdown) as string;
            // Ensure all links open in new tab
            const htmlWithTargets = ensureLinksOpenInNewTab(html);
            editor.commands.setContent(htmlWithTargets, false);
          } catch (e) {
            console.error('Error converting markdown to HTML:', e);
            editor.commands.setContent(value, false);
          }
        }
      }
    }
  }, [value, editor]);

  const handleSetLink = useCallback(() => {
    if (!editor) return;
    
    const { from, to } = editor.state.selection;
    const selectedText = editor.state.doc.textBetween(from, to);
    
    if (selectedText) {
      setLinkText(selectedText);
    }
    
    setShowLinkDialog(true);
  }, [editor]);

  const handleInsertLink = useCallback(() => {
    if (!editor || !linkUrl) return;
    
    if (linkText) {
      editor.chain().focus().insertContent(`<a href="${linkUrl}" target="_blank" rel="noopener noreferrer">${linkText}</a>`).run();
    } else {
      editor.chain().focus().setLink({ href: linkUrl, target: "_blank" }).run();
    }
    
    setLinkUrl("");
    setLinkText("");
    setShowLinkDialog(false);
  }, [editor, linkUrl, linkText]);

  if (!editor) {
    return null;
  }

  return (
    <div className="flex flex-col h-full border rounded-lg overflow-hidden bg-white relative">
      {/* Link Dialog */}
      {showLinkDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-4 rounded-lg shadow-lg min-w-[400px]">
            <h3 className="text-lg font-semibold mb-4">Insert Link</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Link Text</label>
                <Input
                  value={linkText}
                  onChange={(e) => setLinkText(e.target.value)}
                  placeholder="Link text"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">URL</label>
                <Input
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="https://example.com"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleInsertLink();
                    } else if (e.key === "Escape") {
                      setShowLinkDialog(false);
                    }
                  }}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4 justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowLinkDialog(false);
                  setLinkUrl("");
                  setLinkText("");
                }}
              >
                Cancel
              </Button>
              <Button size="sm" onClick={handleInsertLink} disabled={!linkUrl}>
                Insert
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {/* Toolbar */}
      <div className="flex items-center gap-1 p-2 border-b bg-gray-50 flex-wrap">
        <Button
          variant={editor.isActive("bold") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className="h-8 w-8 p-0"
          title="Bold"
        >
          <Bold className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("italic") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className="h-8 w-8 p-0"
          title="Italic"
        >
          <Italic className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("strike") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className="h-8 w-8 p-0"
          title="Strikethrough"
        >
          <Strikethrough className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("code") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleCode().run()}
          className="h-8 w-8 p-0"
          title="Inline Code"
        >
          <Code className="h-4 w-4" />
        </Button>
        <div className="w-px h-6 bg-gray-300 mx-1" />
        <Button
          variant={editor.isActive("heading", { level: 1 }) ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className="h-8 w-8 p-0"
          title="Heading 1"
        >
          <Heading1 className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("heading", { level: 2 }) ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className="h-8 w-8 p-0"
          title="Heading 2"
        >
          <Heading2 className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("heading", { level: 3 }) ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className="h-8 w-8 p-0"
          title="Heading 3"
        >
          <Heading3 className="h-4 w-4" />
        </Button>
        <div className="w-px h-6 bg-gray-300 mx-1" />
        <Button
          variant={editor.isActive("bulletList") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className="h-8 w-8 p-0"
          title="Bullet List"
        >
          <List className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("orderedList") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className="h-8 w-8 p-0"
          title="Numbered List"
        >
          <ListOrdered className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("taskList") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleTaskList().run()}
          className="h-8 w-8 p-0"
          title="Task List"
        >
          <CheckSquare className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("blockquote") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className="h-8 w-8 p-0"
          title="Quote"
        >
          <Quote className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("codeBlock") ? "default" : "ghost"}
          size="sm"
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          className="h-8 w-8 p-0"
          title="Code Block"
        >
          <Code className="h-4 w-4" />
        </Button>
        <Button
          variant={editor.isActive("link") ? "default" : "ghost"}
          size="sm"
          onClick={() => {
            if (editor.isActive("link")) {
              editor.chain().focus().unsetLink().run();
            } else {
              handleSetLink();
            }
          }}
          className="h-8 w-8 p-0"
          title="Insert Link"
        >
          <LinkIcon className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().setHorizontalRule().run()}
          className="h-8 w-8 p-0"
          title="Horizontal Rule"
        >
          <Minus className="h-4 w-4" />
        </Button>
        <div className="w-px h-6 bg-gray-300 mx-1" />
        <Button
          variant={editor.isActive("table") ? "default" : "ghost"}
          size="sm"
          onClick={() => {
            if (editor.isActive("table")) {
              editor.chain().focus().deleteTable().run();
            } else {
              editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
            }
          }}
          className="h-8 w-8 p-0"
          title="Insert Table"
        >
          <TableIcon className="h-4 w-4" />
        </Button>
      </div>
      {/* Editor Content */}
      <div className="flex-1 overflow-auto bg-white" style={{ height }}>
        <div className="h-full">
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  );
};
