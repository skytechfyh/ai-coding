/**
 * Main layout component - DataGrip-style three-panel layout
 * Left: Database sidebar with tables/views
 * Center: Query editor with tabs
 * Bottom: Results panel
 */
import { ReactNode, useState } from "react";
import { Layout } from "antd";
import { LeftOutlined, RightOutlined, DatabaseOutlined } from "@ant-design/icons";
import { layout } from "../styles/theme";

interface MainLayoutProps {
  sidebar: ReactNode;
  queryPanel: ReactNode;
  resultsPanel: ReactNode;
  header?: ReactNode;
}

export function MainLayout({
  sidebar,
  queryPanel,
  resultsPanel,
  header,
}: MainLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [resultsPanelHeight, setResultsPanelHeight] = useState(250);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const sidebarWidth = sidebarCollapsed ? layout.sidebar.collapsedWidth : layout.sidebar.width;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {/* Header */}
      {header && <div className="main-header">{header}</div>}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Sidebar - Database Explorer */}
        <div
          className="sidebar"
          style={{
            width: sidebarWidth,
            minWidth: sidebarWidth,
            background: "#F5F5F7",
            borderRight: "1px solid #E5E5EA",
            transition: "all 200ms ease",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div className="sidebar-header" onClick={toggleSidebar}>
            <span className="sidebar-title">
              <DatabaseOutlined style={{ marginRight: 6 }} />
              {!sidebarCollapsed && "Databases"}
            </span>
            <span className="sidebar-toggle">
              {sidebarCollapsed ? <RightOutlined /> : <LeftOutlined />}
            </span>
          </div>
          {!sidebarCollapsed && <div className="sidebar-content">{sidebar}</div>}
        </div>

        {/* Main Content Area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {/* Query Panel */}
          <div className="query-panel" style={{ flex: 1, overflow: "hidden" }}>
            {queryPanel}
          </div>

          {/* Resizer */}
          <div
            className="resizer resizer-horizontal"
            onMouseDown={(e) => {
              e.preventDefault();
              const startY = e.clientY;
              const startHeight = resultsPanelHeight;

              const onMouseMove = (moveEvent: MouseEvent) => {
                const delta = startY - moveEvent.clientY;
                const newHeight = Math.max(100, Math.min(startHeight + delta, window.innerHeight * 0.7));
                setResultsPanelHeight(newHeight);
              };

              const onMouseUp = () => {
                document.removeEventListener("mousemove", onMouseMove);
                document.removeEventListener("mouseup", onMouseUp);
              };

              document.addEventListener("mousemove", onMouseMove);
              document.addEventListener("mouseup", onMouseUp);
            }}
          />

          {/* Results Panel */}
          <div
            className="results-panel"
            style={{
              height: resultsPanelHeight,
              minHeight: 100,
              background: "#FFFFFF",
              borderTop: "1px solid #E5E5EA",
            }}
          >
            {resultsPanel}
          </div>
        </div>
      </div>

      <style>{`
        .main-header {
          height: ${layout.header.height}px;
          line-height: ${layout.header.height}px;
          padding: 0 16px;
          background: #FFFFFF;
          border-bottom: 1px solid #E5E5EA;
          display: flex;
          align-items: center;
        }

        .sidebar-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 12px;
          border-bottom: "1px solid #E5E5EA";
          cursor: pointer;
          user-select: none;
          transition: background 150ms ease;
          flex-shrink: 0;
        }

        .sidebar-header:hover {
          background: rgba(0, 0, 0, 0.04);
        }

        .sidebar-title {
          font-size: 12px;
          font-weight: 600;
          color: #1D1D1F;
          display: flex;
          align-items: center;
        }

        .sidebar-toggle {
          font-size: 10px;
          color: #86868B;
        }

        .sidebar-content {
          flex: 1;
          overflow: auto;
          padding: 4px 0;
        }

        .resizer-horizontal {
          height: 4px;
          background: transparent;
          cursor: row-resize;
          transition: background 150ms ease;
          flex-shrink: 0;
        }

        .resizer-horizontal:hover {
          background: #007AFF;
        }
      `}</style>
    </Layout>
  );
}
