import React, { useCallback } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import TurndownService from "turndown";
import { marked } from "marked";
import { Button } from "./ui/button";
import { 
  Bold, 
  Italic, 
  List, 
  ListOrdered, 
  Heading1, 
  Heading2, 
  Heading3,
  Quote,
  Code
} from "lucide-react";

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

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  height = "100%",
}) => {
  const handleUpdate = useCallback((editor: any) => {
    // Convert HTML to Markdown
    const html = editor.getHTML();
    const markdown = turndownService.turndown(html);
    onChange(markdown);
  }, [onChange]);

  // Convert markdown to HTML for initial content
  const getInitialContent = useCallback((markdown: string) => {
    if (!markdown || markdown.trim() === "") {
      return "";
    }
    try {
      return marked.parse(markdown) as string;
    } catch (e) {
      // Fallback to plain text if parsing fails
      return markdown;
    }
  }, []);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
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
            const html = marked.parse(value) as string;
            editor.commands.setContent(html, false);
          } catch (e) {
            // Fallback: set as plain text
            editor.commands.setContent(value, false);
          }
        }
      }
    }
  }, [value, editor]);

  if (!editor) {
    return null;
  }

  return (
    <div className="flex flex-col h-full border rounded-lg overflow-hidden bg-white">
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
