import { useRef, useCallback, useEffect, type ReactNode } from "react";
import { ST } from "../styles/theme";

interface DetailPanelProps {
  activeTab: "detail" | "llm";
  onTabChange: (tab: "detail" | "llm") => void;
  detailContent: ReactNode;
  llmContent: ReactNode;
  searchBar: ReactNode;
}

export default function DetailPanel({
  activeTab,
  onTabChange,
  detailContent,
  llmContent,
  searchBar,
}: DetailPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const onMouseDown = useCallback(() => {
    draggingRef.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!draggingRef.current || !panelRef.current) return;
      const newWidth = Math.max(300, Math.min(e.clientX, window.innerWidth * 0.7));
      panelRef.current.style.width = `${newWidth}px`;
    };
    const onMouseUp = () => {
      if (draggingRef.current) {
        draggingRef.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <>
      <div
        ref={panelRef}
        className="flex flex-col overflow-hidden shrink-0"
        style={{
          width: 440,
          minWidth: 300,
          background: ST.navyLight,
          borderRight: `1px solid ${ST.border}`,
          boxShadow: "4px 0 20px rgba(0,0,0,0.2)",
          zIndex: 10,
        }}
      >
        {/* Search bar */}
        {searchBar}

        {/* Tabs */}
        <div className="flex shrink-0" style={{ borderBottom: `1px solid ${ST.border}` }}>
          <button
            className={`tab detail ${activeTab === "detail" ? "active" : ""}`}
            onClick={() => onTabChange("detail")}
          >
            Detail
          </button>
          <button
            className={`tab llm ${activeTab === "llm" ? "active" : ""}`}
            onClick={() => onTabChange("llm")}
          >
            LLM Query
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 detail-scroll">
          {activeTab === "detail" ? detailContent : llmContent}
        </div>
      </div>

      {/* Drag handle */}
      <div className="drag-handle" onMouseDown={onMouseDown} />
    </>
  );
}
