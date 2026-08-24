import { useEffect, useState } from "react";

type ComponentState = {
  status: "up" | "down";
  detail?: string;
};

type Readiness = {
  status: "ready" | "not_ready";
  components: Record<string, ComponentState>;
};

type Version = {
  product: string;
  release: string;
  milestone: string;
  build_version: string;
};

const INITIAL_VERSION: Version = {
  product: "NEXWEAVE",
  release: "R1",
  milestone: "M0",
  build_version: "checking",
};

export function App() {
  const [version, setVersion] = useState<Version>(INITIAL_VERSION);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [connectionError, setConnectionError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPlatformStatus() {
      try {
        const [versionResponse, readinessResponse] = await Promise.all([
          fetch("/api/v1/version", { signal: controller.signal }),
          fetch("/api/v1/health/ready", { signal: controller.signal }),
        ]);
        if (!versionResponse.ok) {
          throw new Error("version endpoint is unavailable");
        }
        setVersion((await versionResponse.json()) as Version);
        setReadiness((await readinessResponse.json()) as Readiness);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setConnectionError(true);
      }
    }

    void loadPlatformStatus();
    return () => controller.abort();
  }, []);

  const isReady = readiness?.status === "ready";
  const overallLabel = connectionError
    ? "无法连接"
    : isReady
      ? "工程骨架就绪"
      : "正在检查";

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="/" aria-label="NEXWEAVE 首页">
          <span className="brand-mark">N</span>
          <span>NEXWEAVE</span>
        </a>
        <span className="phase-badge">R1 · M0</span>
      </header>

      <section className="hero" aria-labelledby="page-title">
        <div className="eyebrow">TRUSTED KNOWLEDGE PLATFORM</div>
        <h1 id="page-title">终局架构，已经开始落地。</h1>
        <p>
          当前页面只验证 NEXWEAVE
          的工程底座。知识业务能力尚未进入开发，静态原型也不作为真实功能展示。
        </p>
        <div
          className={`overall ${isReady ? "ready" : "pending"}`}
          role="status"
        >
          <span className="pulse" aria-hidden="true" />
          <span>{overallLabel}</span>
          <small>{version.build_version}</small>
        </div>
      </section>

      <section className="status-section" aria-labelledby="status-title">
        <div className="section-heading">
          <div>
            <span className="section-index">01</span>
            <h2 id="status-title">基础服务</h2>
          </div>
          <span>
            {readiness
              ? `${Object.keys(readiness.components).length} services`
              : "checking"}
          </span>
        </div>

        <div className="service-grid">
          {readiness ? (
            Object.entries(readiness.components).map(([name, state]) => (
              <article className="service-card" key={name}>
                <span
                  className={`service-state ${state.status}`}
                  aria-label={state.status}
                />
                <h3>{serviceLabel(name)}</h3>
                <p>
                  {state.status === "up"
                    ? "连接正常"
                    : state.detail || "连接失败"}
                </p>
              </article>
            ))
          ) : (
            <article className="service-card skeleton">
              <span />
              <span />
            </article>
          )}
        </div>
      </section>

      <section className="boundary" aria-labelledby="boundary-title">
        <span className="section-index">02</span>
        <h2 id="boundary-title">M0 边界</h2>
        <div className="boundary-grid">
          <p>
            已包含：公共契约、健康 API、Worker、迁移、Web 外壳、可复现基础环境。
          </p>
          <p>
            未包含：资料、Schema、编译、审核、发布、问答及 GridCrew 业务集成。
          </p>
        </div>
      </section>

      <footer>
        <span>{version.product}</span>
        <span>
          {version.release} / {version.milestone}
        </span>
      </footer>
    </main>
  );
}

function serviceLabel(name: string) {
  const labels: Record<string, string> = {
    postgresql: "PostgreSQL",
    redis: "Redis",
    object_storage: "RustFS / S3",
    temporal: "Temporal",
  };
  return labels[name] ?? name;
}
