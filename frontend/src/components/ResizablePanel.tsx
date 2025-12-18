import React, { useState, useRef, useEffect, useCallback, ReactNode } from "react";

interface ResizablePanelProps {
  children: ReactNode;
  side: "left" | "right";
  initialWidth: number;
  minWidth?: number;
  maxWidth?: number;
}

export const ResizablePanel: React.FC<ResizablePanelProps> = ({
  children,
  side,
  initialWidth,
  minWidth = 200,
  maxWidth = 600,
}) => {
  const [width, setWidth] = useState(initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const resizeRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (isResizing) {
        const newWidth = side === "left" ? e.clientX : window.innerWidth - e.clientX;
        setWidth(Math.max(minWidth, Math.min(maxWidth, newWidth)));
      }
    },
    [isResizing, side, minWidth, maxWidth]
  );

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    } else {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const startResizing = () => {
    setIsResizing(true);
  };

  const resizeHandlePosition = side === "left" ? "right-0" : "left-0";

  return (
    <div className="flex-shrink-0 relative" style={{ width: `${width}px` }}>
      {side === "right" && (
        <div
          ref={resizeRef}
          onMouseDown={startResizing}
          className={`absolute ${resizeHandlePosition} top-0 w-1 h-full cursor-col-resize hover:bg-blue-500 bg-transparent transition-colors z-10`}
          style={{ touchAction: "none" }}
        />
      )}
      {children}
      {side === "left" && (
        <div
          ref={resizeRef}
          onMouseDown={startResizing}
          className={`absolute ${resizeHandlePosition} top-0 w-1 h-full cursor-col-resize hover:bg-blue-500 bg-transparent transition-colors z-10`}
          style={{ touchAction: "none" }}
        />
      )}
    </div>
  );
};

