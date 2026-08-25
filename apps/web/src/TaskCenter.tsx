import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError, NexweaveApi } from "./api";
import type {
  Principal,
  WorkflowCommand,
  WorkflowTask,
  WorkflowTaskDetail,
  WorkflowType,
} from "./types";

const TYPES: Array<[WorkflowType, string]> = [
  ["SOURCE_INGESTION", "资料接入内核"],
  ["KNOWLEDGE_COMPILE", "知识编译内核"],
  ["HUMAN_REVIEW", "人工审核内核"],
  ["QUALITY_EVALUATION", "质量评估内核"],
  ["KNOWLEDGE_RELEASE", "知识发布内核"],
  ["DOMAIN_PACK_INSTALL", "领域包安装内核"],
  ["GRIDCREW_FEEDBACK_INGESTION", "GridCrew 反馈内核"],
];

const COMMAND_LABEL: Record<WorkflowCommand, string> = {
  PAUSE: "暂停",
  RESUME: "继续",
  CANCEL: "取消并补偿",
  CLAIM: "领取",
  REQUEST_INPUT: "请求补充资料",
  PROVIDE_INPUT: "资料已补充",
  APPROVE: "批准",
  REJECT: "驳回",
  RETRY: "创建重试 Run",
};

export function TaskCenter({
  api,
  principal,
  spaceId,
}: {
  api: NexweaveApi;
  principal: Principal;
  spaceId: string;
}) {
  const [tasks, setTasks] = useState<WorkflowTask[]>([]);
  const [selectedId, setSelectedId] = useState(readTaskId);
  const [detail, setDetail] = useState<WorkflowTaskDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const canCreate = principal.roles.some((role) =>
    ["tenant_admin", "space_admin", "knowledge_engineer"].includes(role),
  );

  const refresh = useCallback(async () => {
    if (!spaceId) {
      setTasks([]);
      setDetail(null);
      setLoading(false);
      return;
    }
    setError("");
    setLoading(true);
    try {
      const page = await api.workflowTasks(spaceId);
      setTasks(page.items);
      const routeId = readTaskId();
      const target = routeId || selectedId;
      if (target) {
        const value = await api.workflowTask(target);
        setDetail(value);
        setSelectedId(target);
      } else {
        setDetail(null);
      }
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setLoading(false);
    }
  }, [api, selectedId, spaceId]);

  useEffect(() => void refresh(), [refresh]);
  useEffect(() => {
    const restore = () => {
      setSelectedId(readTaskId());
      void refresh();
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, [refresh]);

  const counts = useMemo(
    () => ({
      active: tasks.filter((task) =>
        [
          "CREATED",
          "STARTING",
          "RUNNING",
          "CANCELLING",
          "COMPENSATING",
        ].includes(task.status),
      ).length,
      waiting: tasks.filter((task) =>
        ["PAUSED", "WAITING", "WAITING_INPUT"].includes(task.status),
      ).length,
      failed: tasks.filter((task) =>
        ["FAILED", "TIMED_OUT", "REJECTED"].includes(task.status),
      ).length,
    }),
    [tasks],
  );

  function openTask(id: string) {
    history.pushState({}, "", `/compile/${id}`);
    setSelectedId(id);
    setLoading(true);
    api
      .workflowTask(id)
      .then(setDetail)
      .catch((nextError: unknown) => setError(messageOf(nextError)))
      .finally(() => setLoading(false));
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setWorking(true);
    setError("");
    try {
      const created = await api.createWorkflowTask(spaceId, {
        workflow_type: data.get("workflow_type"),
        business_key: data.get("business_key"),
        display_name: data.get("display_name"),
        input_refs: {},
        start_paused: data.get("start_paused") === "on",
      });
      form.reset();
      openTask(created.id);
      await refresh();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  async function command(action: WorkflowCommand) {
    if (!detail) return;
    setWorking(true);
    setError("");
    try {
      await api.commandWorkflowTask(
        detail.task,
        action,
        `任务中心执行 ${COMMAND_LABEL[action]}`,
      );
      await refresh();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  async function reconcile() {
    if (!detail) return;
    setWorking(true);
    setError("");
    try {
      await api.reconcileWorkflowTask(detail.task.id);
      await refresh();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="page">
      <header className="page-title">
        <span>05</span>
        <div>
          <h1>任务中心</h1>
          <p>
            Temporal 是执行权威；此处展示 PostgreSQL
            只读投影、步骤、日志和服务端允许的动作。
          </p>
        </div>
      </header>
      {error && (
        <div className="form-error" role="alert">
          {error}
          <button onClick={() => void refresh()}>重试</button>
        </div>
      )}
      <div className="metric-grid task-metrics">
        <Metric value={tasks.length} label="全部任务" detail="当前知识空间" />
        <Metric value={counts.active} label="执行中" detail="Temporal 运行态" />
        <Metric
          value={counts.waiting}
          label="等待处理"
          detail="暂停 / 人工输入"
        />
        <Metric
          value={counts.failed}
          label="需关注"
          detail="失败 / 超时 / 驳回"
        />
      </div>
      {canCreate && spaceId && (
        <Panel title="启动 M2 内核任务">
          <form className="inline-form task-create" onSubmit={create}>
            <select name="workflow_type" aria-label="工作流类型">
              {TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <input
              name="business_key"
              aria-label="业务键"
              placeholder="稳定业务键，例如 demo-001"
              pattern="[A-Za-z0-9][A-Za-z0-9._:-]*"
              required
            />
            <input
              name="display_name"
              aria-label="任务名称"
              placeholder="任务名称"
              required
            />
            <label className="check-field">
              <input name="start_paused" type="checkbox" /> 启动后暂停
            </label>
            <button className="primary" disabled={working}>
              启动
            </button>
          </form>
          <small className="boundary-note">
            七类任务仅执行 M2 可靠性边界 Stub，不生成 M3+ 业务对象。
          </small>
        </Panel>
      )}
      <div className="task-layout">
        <Panel title={`任务列表 · ${tasks.length}`}>
          <div className="task-list">
            {tasks.map((task) => (
              <button
                className={selectedId === task.id ? "selected" : ""}
                key={task.id}
                onClick={() => openTask(task.id)}
              >
                <span
                  className={`workflow-status ${task.status.toLowerCase()}`}
                >
                  {task.status}
                </span>
                <strong>{task.display_name}</strong>
                <small>{typeLabel(task.workflow_type)}</small>
                <progress value={task.progress} max="100" />
                <code>{task.workflow_id}</code>
              </button>
            ))}
            {!tasks.length && (
              <div className="empty">
                {loading ? "正在加载任务投影…" : "当前空间尚无工作流任务"}
              </div>
            )}
          </div>
        </Panel>
        <div className="stack">
          {detail ? (
            <TaskDetail
              canReconcile={principal.roles.some((role) =>
                ["platform_admin", "tenant_admin"].includes(role),
              )}
              detail={detail}
              working={working}
              onCommand={command}
              onReconcile={reconcile}
              onRefresh={refresh}
            />
          ) : (
            <Panel title="任务详情">
              <div className="empty">选择任务查看步骤、日志和可执行动作</div>
            </Panel>
          )}
        </div>
      </div>
    </section>
  );
}

function TaskDetail({
  detail,
  canReconcile,
  working,
  onCommand,
  onReconcile,
  onRefresh,
}: {
  detail: WorkflowTaskDetail;
  canReconcile: boolean;
  working: boolean;
  onCommand: (action: WorkflowCommand) => Promise<void>;
  onReconcile: () => Promise<void>;
  onRefresh: () => Promise<void>;
}) {
  const task = detail.task;
  return (
    <>
      <Panel title="任务详情">
        <div className="task-summary">
          <div>
            <span>状态</span>
            <strong>{task.status}</strong>
          </div>
          <div>
            <span>进度</span>
            <strong>{task.progress}%</strong>
          </div>
          <div>
            <span>投影</span>
            <strong>{task.projection_in_sync ? "已同步" : "待对账"}</strong>
          </div>
          <div>
            <span>Run ID</span>
            <code>{task.temporal_run_id ?? "等待启动"}</code>
          </div>
        </div>
        <div className="task-actions" aria-label="任务动作">
          {detail.allowed_actions.map((action) => (
            <button
              className={
                action === "CANCEL" || action === "REJECT"
                  ? "danger"
                  : "primary"
              }
              disabled={working}
              key={action}
              onClick={() => void onCommand(action)}
            >
              {COMMAND_LABEL[action]}
            </button>
          ))}
          <button disabled={working} onClick={() => void onRefresh()}>
            刷新
          </button>
          {canReconcile && (
            <button disabled={working} onClick={() => void onReconcile()}>
              与 Temporal 对账
            </button>
          )}
        </div>
      </Panel>
      <Panel title={`执行步骤 · ${detail.steps.length}`}>
        <ol className="step-list">
          {detail.steps.map((step) => (
            <li key={step.id}>
              <span>{String(step.sequence).padStart(2, "0")}</span>
              <div>
                <strong>{step.step_key}</strong>
                <small>{step.message}</small>
              </div>
              <code>
                {step.status} · attempt {step.attempt}
              </code>
            </li>
          ))}
        </ol>
      </Panel>
      <Panel title={`不可变执行日志 · ${detail.events.length}`}>
        <ol className="event-log">
          {[...detail.events].reverse().map((event) => (
            <li key={event.id}>
              <time>{formatDate(event.occurred_at)}</time>
              <strong>{event.event_type}</strong>
              <span>{event.message}</span>
            </li>
          ))}
        </ol>
      </Panel>
    </>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <header>
        <h2>{title}</h2>
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

function Metric({
  value,
  label,
  detail,
}: {
  value: number;
  label: string;
  detail: string;
}) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function readTaskId() {
  const [, id] = location.pathname.match(/^\/compile\/([^/]+)$/) ?? [];
  return id ?? "";
}

function typeLabel(value: WorkflowType) {
  return TYPES.find(([type]) => type === value)?.[1] ?? value;
}

function messageOf(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "任务中心发生未知错误，请重试。";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}
