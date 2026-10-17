import { useEffect, useRef, useState, type FormEvent } from "react";

import { isDeveloperEnvironment, messageOf, NexweaveApi } from "./api";
import type { Session } from "./types";

export function LoginPage({
  initialError,
  onSession,
}: {
  initialError: string;
  onSession: (token: string, expiresIn?: number) => void;
}) {
  const [subject, setSubject] = useState("local-admin");
  const [error, setError] = useState(initialError);
  const [working, setWorking] = useState(false);
  const [config, setConfig] = useState<Awaited<
    ReturnType<NexweaveApi["authConfig"]>
  > | null>(null);
  const exchange = useRef<Promise<Session> | null>(null);
  const [retry, setRetry] = useState(0);
  const [callback] = useState(() =>
    location.pathname === "/auth/callback"
      ? new URLSearchParams(location.search)
      : null,
  );
  useEffect(() => {
    let active = true;
    void new NexweaveApi()
      .authConfig()
      .then((c) => {
        if (active) setConfig(c);
      })
      .catch((cause) => {
        if (active) setError(messageOf(cause, "无法读取身份入口。"));
      });
    if (callback) {
      history.replaceState({}, "", "/");
      const code = callback.get("code"),
        state = callback.get("state");
      if (!code || !state || callback.has("error")) {
        setError("企业身份验证未完成，请重新开始登录。");
      } else {
        setWorking(true);
        exchange.current ??= new NexweaveApi().exchangeOidc(code, state);
        void exchange.current
          .then((session) => {
            if (active) onSession(session.access_token, session.expires_in);
          })
          .catch(() => {
            if (active)
              setError("登录响应未通过校验或已过期，请重新开始企业登录。");
          })
          .finally(() => {
            if (active) setWorking(false);
          });
      }
    }
    return () => {
      active = false;
    };
  }, [callback, onSession, retry]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (working || config?.provider !== "local" || !config.login_enabled)
      return;
    setWorking(true);
    setError("");
    try {
      const session = await new NexweaveApi().login(subject);
      onSession(session.access_token, session.expires_in);
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand">
          <span className="brand-mark">N</span>
          <span className="brand-copy">
            <strong>NEXWEAVE</strong>
            <small>Trusted Knowledge OS</small>
          </span>
        </div>
        <h1>把证据边界，变成知识可信的起点。</h1>
        <p>从资料、知识模型、证据到不可变发布，让每一步都有据可查。</p>
      </section>
      <form className="login-card" onSubmit={submit}>
        <h2>进入平台</h2>
        <p>使用已获授权的账号进入可信知识工作台。</p>
        {config?.provider === "local" && config.login_enabled && (
          <>
            <label htmlFor="subject">开发验证账号</label>
            <input
              id="subject"
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              required
            />
          </>
        )}
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        {!config && <p>正在读取身份入口…</p>}
        {config?.provider === "oidc" &&
          (config.login_enabled && config.login_url ? (
            <a
              className="btn primary"
              href={config.login_url}
              aria-disabled={working}
            >
              {working ? "正在完成企业登录…" : "使用企业 OIDC 登录"}
            </a>
          ) : (
            <p>企业登录尚未配置，请由平台管理员配置已批准的身份服务。</p>
          ))}
        {config?.provider === "local" && config.login_enabled && (
          <button className="primary" disabled={working} type="submit">
            {working ? "正在验证…" : "验证身份并进入"}
          </button>
        )}
        {config && !config.login_enabled && config.provider === "local" && (
          <p>当前环境未启用开发登录。</p>
        )}
        {!config && error && (
          <button
            type="button"
            onClick={() => {
              setError("");
              setRetry((v) => v + 1);
            }}
          >
            重试读取登录入口
          </button>
        )}
        {isDeveloperEnvironment() && config?.provider === "local" && (
          <details className="technical-details">
            <summary>开发环境说明</summary>
            <div>当前登录入口连接本地身份服务，仅用于开发验证。</div>
          </details>
        )}
      </form>
    </main>
  );
}
