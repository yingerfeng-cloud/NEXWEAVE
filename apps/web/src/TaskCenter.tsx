import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  Metric,
  PageHeader,
  Panel,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type {
  Principal,
  WorkflowCommand,
  WorkflowTask,
  WorkflowTaskDetail,
  WorkflowType,
} from "./types";

const TYPES: Array<[WorkflowType, string]> = [
  ["SOURCE_INGESTION", "资料接入"],
  ["KNOWLEDGE_COMPILE", "知识编译"],
  ["HUMAN_REVIEW", "人工审核"],
  ["QUALITY_EVALUATION", "质量评估"],
  ["KNOWLEDGE_RELEASE", "知识发布"],
  ["DOMAIN_PACK_INSTALL", "领域包安装"],
  ["GRIDCREW_FEEDBACK_INGESTION", "外部反馈接入"],
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

  const refresh = useCallback(
    async (requestedId?: string) => {
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
        const target = requestedId === undefined ? readTaskId() : requestedId;
        if (target) {
          const value = await api.workflowTask(target);
          setDetail(value);
          setSelectedId(target);
        } else {
          setDetail(null);
          setSelectedId("");
        }
      } catch (nextError) {
        setError(messageOf(nextError));
      } finally {
        setLoading(false);
      }
    },
    [api, spaceId],
  );

  useEffect(() => void refresh(readTaskId()), [refresh]);
  useEffect(() => {
    const restore = () => {
      const routeId = readTaskId();
      setSelectedId(routeId);
      void refresh(routeId);
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
    history.pushState({}, "", `/tasks/${id}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
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
      <PageHeader
        title="任务中心"
        description="跟踪资料接入、知识编译、人工审核和发布任务的进度与待处理事项。"
      />
      {error && (
        <div className="form-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => void refresh()}>
            重试
          </button>
        </div>
      )}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="任务列表需要读取当前知识空间的可靠执行记录。"
        />
      )}
      <div className="metric-grid task-metrics">
        <Metric value={tasks.length} label="全部任务" detail="当前知识空间" />
        <Metric value={counts.active} label="执行中" detail="正在处理" />
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
        <Panel title="启动任务">
          <form className="inline-form task-create" onSubmit={create}>
            <label>
              任务类型
              <select name="workflow_type">
                {TYPES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              业务标识
              <input
                name="business_key"
                placeholder="例如 equipment-review-001"
                pattern="[A-Za-z0-9][A-Za-z0-9._:-]*"
                required
              />
            </label>
            <label>
              任务名称
              <input name="display_name" placeholder="任务名称" required />
            </label>
            <label className="check-field">
              <input name="start_paused" type="checkbox" /> 启动后暂停
            </label>
            <button className="primary" type="submit" disabled={working}>
              启动
            </button>
          </form>
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
                <StatusPill value={task.status} />
                <strong>{task.display_name}</strong>
                <small>{typeLabel(task.workflow_type)}</small>
                <progress value={task.progress} max="100" />
                <small>创建于 {formatDate(task.created_at)}</small>
              </button>
            ))}
            {!tasks.length && (
              <EmptyState
                title={loading ? "正在读取任务" : "当前没有任务"}
                description={
                  loading
                    ? "正在获取最新运行状态。"
                    : "启动资料接入、知识编译或审核任务后，进度会显示在这里。"
                }
              />
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
              <EmptyState
                title="选择一个任务"
                description="查看处理进度、执行步骤、日志和可用操作。"
              />
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
            <StatusPill value={task.status} />
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
            <span>人工介入</span>
            <strong>
              {detail.allowed_actions.length ? "可处理" : "无需介入"}
            </strong>
          </div>
        </div>
        <div className="task-actions" aria-label="任务动作">
          {detail.allowed_actions.map((action) => (
            <button
              type="button"
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
          <button
            type="button"
            disabled={working}
            onClick={() => void onRefresh()}
          >
            刷新
          </button>
          {canReconcile && (
            <button
              type="button"
              disabled={working}
              onClick={() => void onReconcile()}
            >
              校准任务状态
            </button>
          )}
        </div>
      </Panel>
      <TechnicalDetails>
        <code>Workflow {task.workflow_id}</code>
        <code> · Run {task.temporal_run_id ?? "等待启动"}</code>
      </TechnicalDetails>
      <Panel title={`执行步骤 · ${detail.steps.length}`}>
        <ol className="step-list">
          {detail.steps.map((step) => (
            <li key={step.id}>
              <span>{String(step.sequence).padStart(2, "0")}</span>
              <div>
                <strong>{step.step_key}</strong>
                <small>{step.message}</small>
              </div>
              <span className="step-status">
                <StatusPill value={step.status} /> · attempt {step.attempt}
              </span>
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

function readTaskId() {
  const [, id] =
    location.pathname.match(/^\/(?:tasks|compile)\/([^/]+)$/) ?? [];
  return id ?? "";
}

function typeLabel(value: WorkflowType) {
  return TYPES.find(([type]) => type === value)?.[1] ?? value;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}
