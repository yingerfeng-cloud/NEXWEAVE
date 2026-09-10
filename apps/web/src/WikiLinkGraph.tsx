import {
  type PointerEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type WheelEvent,
} from "react";

import { messageOf, NexweaveApi } from "./api";
import { EmptyState, ErrorState, StatusPill } from "./design-system/ui";
import type {
  WikiLinkGraph,
  WikiLinkGraphEdge,
  WikiLinkGraphNode,
} from "./types";

const CANVAS_WIDTH = 1120;
const CANVAS_HEIGHT = 680;
const MIN_SCALE = 0.58;
const MAX_SCALE = 2.2;
const DEFAULT_SCALE = 1.35;
type Point = { x: number; y: number };

function problem(cause: unknown) {
  return messageOf(cause, "无法读取 Wiki 页面图谱。");
}

function colorFor(templateKey: string) {
  const palette = [
    "var(--nw-viz-1)",
    "var(--nw-viz-2)",
    "var(--nw-viz-3)",
    "var(--nw-viz-4)",
    "var(--nw-viz-5)",
    "var(--nw-viz-6)",
    "var(--nw-viz-7)",
    "var(--nw-viz-8)",
  ] as const;
  let hash = 0;
  for (const character of templateKey)
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return palette[hash % palette.length];
}

function seededOffset(value: string) {
  let hash = 2166136261;
  for (const character of value)
    hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return (hash >>> 0) / 0xffffffff - 0.5;
}

function nodeRadius(node: WikiLinkGraphNode) {
  return Math.min(40, 18 + (node.outbound_count + node.backlink_count) * 3.2);
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function forceLayout(graph: WikiLinkGraph | null) {
  const positions = new Map<string, Point>();
  if (!graph?.nodes.length) return positions;
  const nodes = [...graph.nodes].sort((left, right) =>
    left.title.localeCompare(right.title, "zh-CN"),
  );
  const byId = new Map(nodes.map((node, index) => [node.id, index]));
  const templates = [...new Set(nodes.map((node) => node.template_key))].sort();
  const centers = new Map<string, Point>();
  templates.forEach((template, index) => {
    const angle =
      (Math.PI * 2 * index) / Math.max(templates.length, 1) - Math.PI / 2;
    centers.set(template, {
      x: CANVAS_WIDTH / 2 + Math.cos(angle) * 205,
      y: CANVAS_HEIGHT / 2 + Math.sin(angle) * 126,
    });
  });
  const compactGraph = nodes.length <= 40;
  const points = nodes.map((node) => {
    const center = centers.get(node.template_key) || {
      x: CANVAS_WIDTH / 2,
      y: CANVAS_HEIGHT / 2,
    };
    return {
      x: center.x + seededOffset(`${node.id}:x`) * (compactGraph ? 250 : 130),
      y: center.y + seededOffset(`${node.id}:y`) * (compactGraph ? 180 : 95),
    };
  });
  const focusIndex = graph.focus_page_id
    ? (byId.get(graph.focus_page_id) ?? -1)
    : -1;
  if (focusIndex >= 0)
    points[focusIndex] = { x: CANVAS_WIDTH / 2, y: CANVAS_HEIGHT / 2 };

  const iterations = nodes.length > 220 ? 82 : 150;
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const force = points.map(() => ({ x: 0, y: 0 }));
    for (let source = 0; source < points.length; source += 1) {
      for (let target = source + 1; target < points.length; target += 1) {
        const dx = points[target].x - points[source].x;
        const dy = points[target].y - points[source].y;
        const distanceSquared = Math.max(dx * dx + dy * dy, 1);
        const distance = Math.sqrt(distanceSquared);
        const repulsion = (compactGraph ? 32000 : 1650) / distanceSquared;
        const x = (dx / distance) * repulsion;
        const y = (dy / distance) * repulsion;
        force[source].x -= x;
        force[source].y -= y;
        force[target].x += x;
        force[target].y += y;
      }
    }
    for (const edge of graph.edges) {
      const source = byId.get(edge.source_page_id);
      const target = byId.get(edge.target_page_id);
      if (source === undefined || target === undefined) continue;
      const dx = points[target].x - points[source].x;
      const dy = points[target].y - points[source].y;
      const distance = Math.max(Math.hypot(dx, dy), 1);
      const attraction = (distance - 132) * 0.012;
      force[source].x += (dx / distance) * attraction;
      force[source].y += (dy / distance) * attraction;
      force[target].x -= (dx / distance) * attraction;
      force[target].y -= (dy / distance) * attraction;
    }
    points.forEach((point, index) => {
      if (index === focusIndex) {
        point.x = CANVAS_WIDTH / 2;
        point.y = CANVAS_HEIGHT / 2;
        return;
      }
      const center = centers.get(nodes[index].template_key) || {
        x: CANVAS_WIDTH / 2,
        y: CANVAS_HEIGHT / 2,
      };
      const centerPull = compactGraph ? 0.004 : 0.012;
      force[index].x += (center.x - point.x) * centerPull;
      force[index].y += (center.y - point.y) * centerPull;
      const edgeMargin = compactGraph ? 112 : 42;
      point.x = clamp(
        point.x + force[index].x,
        edgeMargin,
        CANVAS_WIDTH - edgeMargin,
      );
      point.y = clamp(point.y + force[index].y, 72, CANVAS_HEIGHT - 72);
    });
  }
  nodes.forEach((node, index) => positions.set(node.id, points[index]));
  return positions;
}

function curvePath(source: Point, target: Point, edgeId: string) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const distance = Math.max(Math.hypot(dx, dy), 1);
  const bend =
    Math.min(36, distance * 0.16) * (seededOffset(edgeId) > 0 ? 1 : -1);
  const control = {
    x: (source.x + target.x) / 2 + (-dy / distance) * bend,
    y: (source.y + target.y) / 2 + (dx / distance) * bend,
  };
  return `M ${source.x} ${source.y} Q ${control.x} ${control.y} ${target.x} ${target.y}`;
}

export function WikiLinkGraphCenter({
  api,
  spaceId,
  onOpenWikiPage,
  onShowReleaseGraph,
}: {
  api: NexweaveApi;
  spaceId: string;
  onOpenWikiPage: (pageId: string) => void;
  onShowReleaseGraph: () => void;
}) {
  const [graph, setGraph] = useState<WikiLinkGraph | null>(null);
  const [focusPageId, setFocusPageId] = useState("");
  const [search, setSearch] = useState("");
  const [activeTemplates, setActiveTemplates] = useState<Set<string>>(
    new Set(),
  );
  const [selected, setSelected] = useState<WikiLinkGraphNode | null>(null);
  const [hoveredPageId, setHoveredPageId] = useState("");
  const [scale, setScale] = useState(DEFAULT_SCALE);
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [error, setError] = useState("");
  const drag = useRef<{ x: number; y: number; pan: Point } | null>(null);
  const didPan = useRef(false);

  const load = useCallback(async () => {
    if (!spaceId) return;
    try {
      const next = await api.wikiLinkGraph(spaceId, focusPageId || undefined);
      setGraph(next);
      setSelected((current) =>
        current
          ? next.nodes.find((node) => node.id === current.id) || null
          : null,
      );
      setError("");
    } catch (cause) {
      setError(problem(cause));
    }
  }, [api, focusPageId, spaceId]);
  useEffect(() => void load(), [load]);

  const positions = useMemo(() => forceLayout(graph), [graph]);
  const visibleNodeIds = useMemo(() => {
    const normalized = search.trim().toLocaleLowerCase();
    return new Set(
      graph?.nodes
        .filter(
          (node) =>
            (!normalized ||
              `${node.title} ${node.template_key}`
                .toLocaleLowerCase()
                .includes(normalized)) &&
            (!activeTemplates.size || activeTemplates.has(node.template_key)),
        )
        .map((node) => node.id),
    );
  }, [activeTemplates, graph, search]);
  const visibleEdges = useMemo(
    () =>
      graph?.edges.filter(
        (edge) =>
          visibleNodeIds.has(edge.source_page_id) &&
          visibleNodeIds.has(edge.target_page_id),
      ) || [],
    [graph, visibleNodeIds],
  );
  const templates = useMemo(
    () =>
      [...new Set(graph?.nodes.map((node) => node.template_key) || [])].sort(),
    [graph],
  );
  const pageById = useMemo(
    () => new Map(graph?.nodes.map((node) => [node.id, node]) || []),
    [graph],
  );
  const emphasizedPageId = selected?.id || hoveredPageId;
  const neighbors = useMemo(() => {
    if (!emphasizedPageId || !graph) return new Set<string>();
    return new Set(
      graph.edges.flatMap((edge) => {
        if (edge.source_page_id === emphasizedPageId)
          return [edge.target_page_id];
        if (edge.target_page_id === emphasizedPageId)
          return [edge.source_page_id];
        return [];
      }),
    );
  }, [emphasizedPageId, graph]);
  const connections = useMemo(() => {
    if (!selected || !graph) return { inbound: [], outbound: [] };
    return graph.edges.reduce<{
      inbound: WikiLinkGraphEdge[];
      outbound: WikiLinkGraphEdge[];
    }>(
      (result, edge) => {
        if (edge.source_page_id === selected.id) result.outbound.push(edge);
        if (edge.target_page_id === selected.id) result.inbound.push(edge);
        return result;
      },
      { inbound: [], outbound: [] },
    );
  }, [graph, selected]);
  const viewBox = useMemo(() => {
    const width = CANVAS_WIDTH / scale;
    const height = CANVAS_HEIGHT / scale;
    return `${(CANVAS_WIDTH - width) / 2 - pan.x} ${(CANVAS_HEIGHT - height) / 2 - pan.y} ${width} ${height}`;
  }, [pan, scale]);

  function resetView() {
    setScale(DEFAULT_SCALE);
    setPan({ x: 0, y: 0 });
  }
  function focus(node: WikiLinkGraphNode) {
    setSelected(node);
    setFocusPageId(node.id);
    resetView();
  }
  function toggleTemplate(template: string) {
    setActiveTemplates((current) => {
      const next = new Set(current);
      if (next.has(template)) next.delete(template);
      else next.add(template);
      return next;
    });
  }
  function startPan(event: PointerEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { x: event.clientX, y: event.clientY, pan };
    didPan.current = false;
    setIsPanning(true);
  }
  function movePan(event: PointerEvent<SVGSVGElement>) {
    if (!drag.current) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x =
      ((event.clientX - drag.current.x) / Math.max(bounds.width, 1)) *
      (CANVAS_WIDTH / scale);
    const y =
      ((event.clientY - drag.current.y) / Math.max(bounds.height, 1)) *
      (CANVAS_HEIGHT / scale);
    if (Math.abs(x) > 2 || Math.abs(y) > 2) didPan.current = true;
    setPan({ x: drag.current.pan.x + x, y: drag.current.pan.y + y });
  }
  function endPan(event: PointerEvent<SVGSVGElement>) {
    if (drag.current)
      event.currentTarget.releasePointerCapture(event.pointerId);
    drag.current = null;
    setIsPanning(false);
  }
  function zoomGraph(event: WheelEvent<SVGSVGElement>) {
    event.preventDefault();
    setScale((current) =>
      clamp(current * (event.deltaY < 0 ? 1.14 : 0.88), MIN_SCALE, MAX_SCALE),
    );
  }

  return (
    <section className="content-page wiki-graph-page">
      <div className="page-heading">
        <div>
          <h1>页面知识图谱</h1>
          <p>
            探索页面之间的出链与反向引用。草稿页面可见，但不会被当作已发布知识或
            Evidence 结论。
          </p>
        </div>
        <div className="wiki-graph-actions">
          <button type="button" onClick={onShowReleaseGraph}>
            发布关系图
          </button>
          <button type="button" onClick={() => void load()}>
            刷新
          </button>
          <button type="button" onClick={resetView}>
            重置视图
          </button>
          <button
            type="button"
            onClick={() => {
              setFocusPageId("");
              setSelected(null);
              resetView();
            }}
            disabled={!focusPageId}
          >
            查看空间全图
          </button>
        </div>
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="页面知识图谱需要读取当前空间的 Wiki 页面与双向链接。"
        />
      )}
      <div className="wiki-graph-toolbar data-card">
        <label>
          搜索页面
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="按页面标题或模板筛选"
          />
        </label>
        <span>
          {visibleNodeIds.size} / {graph?.nodes.length || 0} 个页面
        </span>
        <span>{visibleEdges.length} 条可见链接</span>
        <span>→ 出链 · ← 反向引用</span>
        <button
          type="button"
          aria-pressed={showLabels}
          onClick={() => setShowLabels((current) => !current)}
        >
          {showLabels ? "隐藏标签" : "显示标签"}
        </button>
        <div>
          <button
            type="button"
            onClick={() =>
              setScale((value) => clamp(value + 0.16, MIN_SCALE, MAX_SCALE))
            }
          >
            放大
          </button>
          <button
            type="button"
            onClick={() =>
              setScale((value) => clamp(value - 0.16, MIN_SCALE, MAX_SCALE))
            }
          >
            缩小
          </button>
        </div>
      </div>
      {graph?.truncated && (
        <div className="notice-banner">
          图谱已达到安全显示上限。选择一个页面可查看其最多两跳的双向邻域。
        </div>
      )}
      <div className="wiki-graph-shell data-card">
        <div className="wiki-graph-canvas" aria-label="Wiki 双向链接知识图谱">
          <div className="wiki-graph-hint">
            滚轮缩放 · 拖拽平移 · 悬停查看关联 · 点击聚焦
          </div>
          <svg
            className={isPanning ? "is-panning" : ""}
            viewBox={viewBox}
            role="img"
            aria-label="Wiki 双向链接知识图谱"
            onPointerDown={startPan}
            onPointerMove={movePan}
            onPointerUp={endPan}
            onPointerCancel={endPan}
            onWheel={zoomGraph}
          >
            <defs>
              <marker
                id="wiki-graph-arrow"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="5"
                markerHeight="5"
                orient="auto"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" />
              </marker>
              <filter
                id="wiki-graph-glow"
                x="-50%"
                y="-50%"
                width="200%"
                height="200%"
              >
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            {visibleEdges.map((edge) => {
              const source = positions.get(edge.source_page_id);
              const target = positions.get(edge.target_page_id);
              if (!source || !target) return null;
              const active =
                emphasizedPageId === edge.source_page_id ||
                emphasizedPageId === edge.target_page_id;
              return (
                <path
                  className={
                    active
                      ? "wiki-graph-link active"
                      : emphasizedPageId
                        ? "wiki-graph-link muted"
                        : "wiki-graph-link"
                  }
                  key={edge.id}
                  d={curvePath(source, target, edge.id)}
                  markerEnd="url(#wiki-graph-arrow)"
                />
              );
            })}
            {graph?.nodes
              .filter((node) => visibleNodeIds.has(node.id))
              .map((node) => {
                const point = positions.get(node.id);
                if (!point) return null;
                const isSelected = selected?.id === node.id;
                const related = neighbors.has(node.id);
                const dimmed =
                  Boolean(emphasizedPageId) &&
                  !isSelected &&
                  !related &&
                  hoveredPageId !== node.id;
                return (
                  <g
                    className={
                      isSelected
                        ? "wiki-graph-node selected"
                        : related
                          ? "wiki-graph-node related"
                          : dimmed
                            ? "wiki-graph-node dimmed"
                            : "wiki-graph-node"
                    }
                    key={node.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`聚焦页面 ${node.title}`}
                    onClick={() => {
                      if (didPan.current) {
                        didPan.current = false;
                        return;
                      }
                      focus(node);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ")
                        focus(node);
                    }}
                    onPointerEnter={() => setHoveredPageId(node.id)}
                    onPointerLeave={() => setHoveredPageId("")}
                  >
                    <circle
                      cx={point.x}
                      cy={point.y}
                      r={Math.max(nodeRadius(node) + 8, 20)}
                      style={{
                        fill: "transparent",
                        filter: "none",
                        stroke: "transparent",
                        strokeWidth: 0,
                      }}
                    />
                    <circle
                      cx={point.x}
                      cy={point.y}
                      r={nodeRadius(node)}
                      fill={colorFor(node.template_key)}
                    />
                    {showLabels && (
                      <text x={point.x} y={point.y + nodeRadius(node) + 16}>
                        {node.title.length > 24
                          ? `${node.title.slice(0, 24)}…`
                          : node.title}
                      </text>
                    )}
                  </g>
                );
              })}
          </svg>
          {!graph?.nodes.length && (
            <div className="wiki-graph-empty">
              <strong>当前还没有页面关系</strong>
              <p>创建 Wiki 页面并建立链接后，可在这里探索出链与反向引用。</p>
              <button type="button" onClick={onShowReleaseGraph}>
                查看已发布关系图
              </button>
            </div>
          )}
        </div>
        <aside className="wiki-graph-sidepanel">
          <div className="wiki-graph-panel-header">
            <h2>页面类型</h2>
            {!!activeTemplates.size && (
              <button
                type="button"
                onClick={() => setActiveTemplates(new Set())}
              >
                清除
              </button>
            )}
          </div>
          <ul className="wiki-graph-legend">
            {templates.map((template) => (
              <li key={template}>
                <button
                  type="button"
                  aria-pressed={
                    !activeTemplates.size || activeTemplates.has(template)
                  }
                  onClick={() => toggleTemplate(template)}
                >
                  <i style={{ background: colorFor(template) }} />
                  {template}
                </button>
              </li>
            ))}
          </ul>
          {selected ? (
            <div className="wiki-graph-detail">
              <div>
                <StatusPill value={selected.status} />
                <h2>{selected.title}</h2>
                <small>
                  {selected.template_key} · v{selected.version}
                </small>
              </div>
              <p>
                {selected.outbound_count} 条出链 · {selected.backlink_count}{" "}
                个反向引用
              </p>
              <ConnectionList
                title="出链"
                edges={connections.outbound}
                pageById={pageById}
                useSource={false}
                onFocus={focus}
              />
              <ConnectionList
                title="反向引用"
                edges={connections.inbound}
                pageById={pageById}
                useSource
                onFocus={focus}
              />
              <button
                type="button"
                className="primary"
                onClick={() => onOpenWikiPage(selected.id)}
              >
                打开 Wiki 页面
              </button>
            </div>
          ) : (
            <p className="wiki-graph-empty-detail">
              点击任一节点，可聚焦两跳的出链与反向引用，并打开对应 Wiki 页面。
            </p>
          )}
        </aside>
      </div>
    </section>
  );
}

function ConnectionList({
  title,
  edges,
  pageById,
  useSource,
  onFocus,
}: {
  title: string;
  edges: WikiLinkGraphEdge[];
  pageById: Map<string, WikiLinkGraphNode>;
  useSource: boolean;
  onFocus: (node: WikiLinkGraphNode) => void;
}) {
  if (!edges.length) return null;
  return (
    <div className="wiki-graph-connections">
      <h3>{title}</h3>
      <ul>
        {edges.slice(0, 6).map((edge) => {
          const node = pageById.get(
            useSource ? edge.source_page_id : edge.target_page_id,
          );
          if (!node) return null;
          return (
            <li key={edge.id}>
              <button type="button" onClick={() => onFocus(node)}>
                {node.title}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
