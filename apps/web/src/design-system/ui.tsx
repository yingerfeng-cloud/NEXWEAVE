import { useEffect, useId, useRef, type ReactNode } from "react";

export function Modal({
  title,
  busy = false,
  onClose,
  children,
}: {
  title: string;
  busy?: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal-panel"
      aria-labelledby={titleId}
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <header>
        <div>
          <small className="modal-eyebrow">WORKSPACE CONFIGURATION</small>
          <h2 id={titleId}>{title}</h2>
        </div>
        <button
          type="button"
          aria-label="关闭"
          disabled={busy}
          onClick={onClose}
        >
          ×
        </button>
      </header>
      {children}
    </dialog>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  index?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-title">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Panel({
  title,
  children,
  actions,
}: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="panel">
      <header>
        <h2>{title}</h2>
        {actions}
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Metric({
  value,
  label,
  detail,
  tone = "",
}: {
  value: string | number;
  label: string;
  detail: string;
  tone?: "" | "warning" | "danger" | "success" | string;
}) {
  const longValue = String(value).length > 12;
  return (
    <article className={`metric ${tone} ${longValue ? "is-long" : ""}`.trim()}>
      <span>{label}</span>
      <strong title={String(value)}>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

export function DataTable({
  headers,
  rows,
  empty,
}: {
  headers: string[];
  rows: ReactNode[][];
  empty: string;
}) {
  if (!rows.length)
    return (
      <EmptyState
        title={empty}
        description="可调整当前条件，或通过本页主要操作开始添加内容。"
      />
    );
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StatusPill({ value, tone }: { value: string; tone?: string }) {
  return (
    <span
      className={`status-pill ${tone ?? statusTone(value)}`.trim()}
      title={value}
    >
      {statusLabel(value)}
    </span>
  );
}

const STATUS_LABELS: Record<string, string> = {
  PUBLIC: "公开",
  ACTIVE: "启用",
  AVAILABLE: "可用",
  ARCHIVED: "已归档",
  DISABLED: "停用",
  DRAFT: "草稿",
  TESTING: "验证中",
  PUBLISHED: "已发布",
  DEPRECATED: "已停用",
  OPEN: "待处理",
  IN_PROGRESS: "处理中",
  ACCEPTED: "已通过",
  APPROVED: "已批准",
  REJECTED: "已拒绝",
  PENDING_APPROVAL: "待审批",
  COMPLETED: "已完成",
  CREATED: "已创建",
  STARTING: "启动中",
  RUNNING: "运行中",
  CANCELLING: "取消中",
  CANCELLED: "已取消",
  PAUSED: "已暂停",
  SUCCEEDED: "已成功",
  PARTIAL_FAILED: "部分失败",
  FAILED: "失败",
  REGISTERED: "已登记",
  PARSED: "已解析",
  PARTIAL: "部分完成",
  OCR_REQUIRED: "需要 OCR",
  SUPERSEDED: "已被替代",
  INVALIDATED: "已失效",
  QUEUED: "排队中",
  WAITING: "等待中",
  WAITING_INPUT: "等待补充",
  COMPENSATING: "补偿中",
  TIMED_OUT: "已超时",
  CANCELED: "已取消",
  BLOCKED: "已阻断",
  UNRESOLVED: "未决",
  REVOKED: "已撤销",
  VALID: "有效",
  STALE: "已过期",
  STORED: "已存储",
  CHECKSUM: "校验中",
  UPLOADING: "上传中",
  PROCESSING: "处理中",
  PARSING: "解析中",
  INSTALLING: "安装中",
  PLANNED: "已计划",
  NOT_EVALUATED: "未评估",
  IMPORTED_UNVERIFIED: "已导入待核验",
  USER_DEFINED_UNVERIFIED: "用户定义待核验",
  UNAVAILABLE: "暂不可用",
  RETRYING: "重试中",
  NO_ANCHOR: "未指定定位",
  BREAKING: "破坏性变更",
  REFUSED: "明确拒答",
  CITED_CONTEXT: "已引用依据",
  INSUFFICIENT_EVIDENCE: "证据不足",
  ALLOWED: "已允许",
  DENIED: "已拒绝",
  INTERNAL: "内部",
  CONFIDENTIAL: "机密",
  HIGHLY_RESTRICTED: "高度受限",
};

function statusLabel(value: string) {
  return STATUS_LABELS[value] ?? value.replaceAll("_", " ");
}

function statusTone(value: string) {
  if (
    [
      "ACTIVE",
      "AVAILABLE",
      "PUBLISHED",
      "ACCEPTED",
      "APPROVED",
      "COMPLETED",
      "SUCCEEDED",
      "REGISTERED",
      "PARSED",
      "VALID",
      "STORED",
      "CITED_CONTEXT",
      "ALLOWED",
    ].includes(value)
  )
    return "success";
  if (
    [
      "FAILED",
      "REJECTED",
      "BLOCKED",
      "PARTIAL",
      "PARTIAL_FAILED",
      "OCR_REQUIRED",
      "INVALIDATED",
      "UNRESOLVED",
      "REVOKED",
      "TIMED_OUT",
      "REFUSED",
      "INSUFFICIENT_EVIDENCE",
      "DENIED",
    ].includes(value)
  )
    return "danger";
  if (
    [
      "OPEN",
      "IN_PROGRESS",
      "PENDING_APPROVAL",
      "TESTING",
      "CREATED",
      "STARTING",
      "RUNNING",
      "CANCELLING",
      "PAUSED",
      "PARTIAL_FAILED",
      "QUEUED",
      "WAITING",
      "WAITING_INPUT",
      "COMPENSATING",
      "STALE",
      "CHECKSUM",
      "UPLOADING",
      "PROCESSING",
      "PARSING",
      "CANCELED",
      "INSTALLING",
      "PLANNED",
      "RETRYING",
    ].includes(value)
  )
    return "warning";
  return "";
}

export function LoadingState({ text }: { text: string }) {
  return (
    <div className="state-card state-loading" aria-live="polite">
      <i aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  text,
  icon = "◇",
  primaryAction,
  secondaryAction,
}: {
  title?: string;
  description?: string;
  text?: string;
  icon?: ReactNode;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
}) {
  return (
    <div className="empty-state state-card">
      <span className="empty-state-icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <strong>{title ?? text ?? "当前没有可显示的内容"}</strong>
        <p>{description ?? "完成本页的主要操作后，相关内容会出现在这里。"}</p>
        {(primaryAction || secondaryAction) && (
          <div className="empty-state-actions">
            {primaryAction}
            {secondaryAction}
          </div>
        )}
      </div>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void | Promise<void>;
}) {
  return (
    <div className="form-error state-card" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" onClick={() => void onRetry()}>
          重试
        </button>
      )}
    </div>
  );
}

const GOVERNANCE_STEPS = [
  ["claims", "主张与证据"],
  ["conflicts", "冲突"],
  ["reviews", "审核"],
  ["quality", "质量"],
  ["releases", "发布"],
] as const;

export function GovernanceStepper({ current }: { current: string }) {
  return (
    <nav className="governance-stepper" aria-label="可信知识治理流程">
      {GOVERNANCE_STEPS.map(([key, label], index) => (
        <div className={key === current ? "current" : ""} key={key}>
          <span>{index + 1}</span>
          <strong>{label}</strong>
        </div>
      ))}
    </nav>
  );
}

export function TechnicalDetails({
  summary = "查看技术详情",
  children,
}: {
  summary?: string;
  children: ReactNode;
}) {
  return (
    <details className="technical-details">
      <summary>{summary}</summary>
      <div>{children}</div>
    </details>
  );
}

export function PermissionDenied({ description }: { description: string }) {
  return (
    <section className="page">
      <PageHeader index="403" title="无权访问" description={description} />
    </section>
  );
}
