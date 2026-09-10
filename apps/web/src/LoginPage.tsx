import { useState, type FormEvent } from "react";

import { isDeveloperEnvironment, messageOf, NexweaveApi } from "./api";

export function LoginPage({
  initialError,
  onSession,
}: {
  initialError: string;
  onSession: (token: string) => void;
}) {
  const [subject, setSubject] = useState("local-admin");
  const [error, setError] = useState(initialError);
  const [working, setWorking] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setError("");
    try {
      const session = await new NexweaveApi().login(subject);
      onSession(session.access_token);
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
        <label htmlFor="subject">账号</label>
        <input
          id="subject"
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          required
        />
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <button className="primary" disabled={working} type="submit">
          {working ? "正在验证…" : "验证身份并进入"}
        </button>
        {isDeveloperEnvironment() && (
          <details className="technical-details">
            <summary>开发环境说明</summary>
            <div>当前登录入口连接本地身份服务，仅用于开发验证。</div>
          </details>
        )}
      </form>
    </main>
  );
}
