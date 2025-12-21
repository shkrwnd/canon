/**
 * Utility functions for markdown processing
 */

/**
 * Ensures markdown tables have proper formatting:
 * - Adds separator rows if missing
 * - Ensures blank lines before and after tables
 */
export const fixMarkdownTables = (markdown: string): string => {
  if (!markdown) return markdown;

  const lines = markdown.split('\n');
  const processedLines: string[] = [];
  let tableBlock: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Check if this is a table row (starts with | and has at least 2 | characters)
    const isTableRow = /^\|/.test(trimmed) && (trimmed.match(/\|/g) || []).length >= 2;
    const isSeparator = /^\|[\s\-:]+\|$/.test(trimmed);

    if (isTableRow && !isSeparator) {
      tableBlock.push(line);
    } else if (isSeparator) {
      tableBlock.push(line);
      // Ensure blank lines before and after table
      if (processedLines.length > 0 && processedLines[processedLines.length - 1].trim() !== '') {
        processedLines.push('');
      }
      processedLines.push(...tableBlock);
      processedLines.push('');
      tableBlock = [];
    } else {
      // Not a table row - flush any pending table block
      if (tableBlock.length > 0) {
        const hasSeparator = tableBlock.some((l: string) => /^\|[\s\-:]+\|$/.test(l.trim()));

        if (!hasSeparator && tableBlock.length >= 2) {
          // Add separator after first row
          const headerLine = tableBlock[0].trim();
          const headerCells = headerLine.split('|').map((cell: string) => cell.trim()).filter((cell: string) => cell);
          const numColumns = headerCells.length;
          if (numColumns >= 2) {
            const separator = '| ' + Array(numColumns).fill('---').join(' | ') + ' |';
            tableBlock.splice(1, 0, separator);
          }
        }

        // Ensure blank lines before and after table
        if (processedLines.length > 0 && processedLines[processedLines.length - 1].trim() !== '') {
          processedLines.push('');
        }
        processedLines.push(...tableBlock);
        processedLines.push('');
        tableBlock = [];
      }
      processedLines.push(line);
    }
  }

  // Handle table block at end of content
  if (tableBlock.length > 0) {
    const hasSeparator = tableBlock.some((l: string) => /^\|[\s\-:]+\|$/.test(l.trim()));
    if (!hasSeparator && tableBlock.length >= 2) {
      const headerLine = tableBlock[0].trim();
      const headerCells = headerLine.split('|').map((cell: string) => cell.trim()).filter((cell: string) => cell);
      const numColumns = headerCells.length;
      if (numColumns >= 2) {
        const separator = '| ' + Array(numColumns).fill('---').join(' | ') + ' |';
        tableBlock.splice(1, 0, separator);
      }
    }
    if (processedLines.length > 0 && processedLines[processedLines.length - 1].trim() !== '') {
      processedLines.push('');
    }
    processedLines.push(...tableBlock);
    processedLines.push('');
  }

  return processedLines.join('\n');
};


