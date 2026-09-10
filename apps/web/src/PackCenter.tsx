import { useCallback, useEffect, useState, type FormEvent } from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type {
  DomainPackInstallation,
  DomainPackVersion,
  SchemaVersion,
} from "./types";

const installationKey = (spaceId: string) =>
  `nexweave.m4.installation.${spaceId}`;

export function PackCenter({
  api,
  spaceId,
  developerMode = false,
}: {
  api: NexweaveApi;
  spaceId: string;
  developerMode?: boolean;
}) {
  const [packs, setPacks] = useState<DomainPackVersion[]>([]);
  const [schemas, setSchemas] = useState<SchemaVersion[]>([]);
  const [packId, setPackId] = useState("");
  const [schemaId, setSchemaId] = useState("");
  const [semanticVersion, setSemanticVersion] = useState("0.2.0");
  const [installation, setInstallation] =
    useState<DomainPackInstallation | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const busy =
    saving ||
    installation?.status === "PLANNED" ||
    installation?.status === "INSTALLING";

  const load = useCallback(async () => {
    if (!spaceId) {
      setPacks([]);
      setSchemas([]);
      setPackId("");
      setSchemaId("");
      setInstallation(null);
      setError("");
      return;
    }
    try {
      const [packResult, schemaResult] = await Promise.all([
        api.domainPacks(),
        api.schemas(spaceId),
      ]);
      const visiblePacks = developerMode
        ? packResult.items
        : packResult.items.filter((pack) => !isDeveloperFixture(pack));
      setPacks(visiblePacks);
      setSchemas(schemaResult.items);
      setPackId((current) =>
        visiblePacks.some((pack) => pack.id === current)
          ? current
          : visiblePacks[0]?.id || "",
      );
      setSchemaId((current) =>
        schemaResult.items.some(
          (schema) => schema.schema_definition_id === current,
        )
          ? current
          : schemaResult.items[0]?.schema_definition_id || "",
      );
      const saved = localStorage.getItem(installationKey(spaceId));
      if (saved) setInstallation(await api.domainPackInstallation(saved));
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "无法读取领域包。"));
    }
  }, [api, developerMode, spaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!busy || !installation) return;
    const timer = window.setInterval(() => {
      void api
        .domainPackInstallation(installation.id)
        .then(setInstallation)
        .catch(() => undefined);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [api, busy, installation]);

  async function install(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setSaving(true);
    try {
      const result = await api.installDomainPack(spaceId, {
        domain_pack_version_id: packId,
        schema_definition_id: schemaId,
        semantic_version: semanticVersion,
      });
      localStorage.setItem(installationKey(spaceId), result.id);
      setInstallation(result);
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "安装启动失败。"));
    } finally {
      setSaving(false);
    }
  }

  async function control(operation: "disable" | "rollback") {
    if (!installation) return;
    if (busy) return;
    if (
      operation === "rollback" &&
      !confirm("回滚会创建新的安装记录，确认继续？")
    )
      return;
    setSaving(true);
    try {
      const result =
        operation === "disable"
          ? await api.disableDomainPack(spaceId, installation.id)
          : await api.rollbackDomainPack(
              spaceId,
              installation.previous_installation_id || installation.id,
            );
      localStorage.setItem(installationKey(spaceId), result.id);
      setInstallation(result);
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "领域包操作失败。"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="content-page">
      <PageHeader
        title="领域包"
        description="查看、安装和升级经过签名验证的声明式知识扩展；安装不会自动发布知识模型。"
      />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="领域包安装会生成当前空间的候选模型版本。"
        />
      )}
      <form className="inline-form" onSubmit={install}>
        <label>
          领域包版本
          <select
            value={packId}
            onChange={(event) => setPackId(event.target.value)}
            required
          >
            {packs.map((pack) => (
              <option key={pack.id} value={pack.id}>
                {pack.pack_key} · {pack.pack_version}
              </option>
            ))}
          </select>
        </label>
        <label>
          目标知识模型
          <select
            value={schemaId}
            onChange={(event) => setSchemaId(event.target.value)}
            required
          >
            {schemas.map((schema) => (
              <option key={schema.id} value={schema.schema_definition_id}>
                {schema.schema_key}
              </option>
            ))}
          </select>
        </label>
        <label>
          候选版本
          <input
            value={semanticVersion}
            onChange={(event) => setSemanticVersion(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={!packId || !schemaId || busy}>
          安装
        </button>
      </form>
      <div className="data-card">
        <h2>可信制品</h2>
        {!packs.length ? (
          <EmptyState
            title="当前没有可安装的领域包"
            description="已通过签名与兼容性检查的领域包会出现在这里；也可查看领域包规范准备新的制品。"
          />
        ) : (
          <table>
            <thead>
              <tr>
                <th>领域包</th>
                <th>发布者</th>
                <th>签名状态</th>
                <th>兼容范围</th>
              </tr>
            </thead>
            <tbody>
              {packs.map((pack) => (
                <tr key={pack.id}>
                  <td>
                    {pack.pack_key} · {pack.pack_version}
                  </td>
                  <td>{pack.publisher}</td>
                  <td>
                    <StatusPill value={pack.status} />
                  </td>
                  <td>
                    {pack.key_namespace}
                    <TechnicalDetails>
                      <code>{pack.content_checksum}</code>
                    </TechnicalDetails>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {installation && (
        <div className="data-card" aria-live="polite">
          <h2>最近安装</h2>
          <p>
            <strong>{operationLabel(installation.operation)}</strong> ·{" "}
            <StatusPill value={installation.status} />
          </p>
          <p>安装状态已由可靠任务记录。</p>
          {installation.candidate_schema_version_id && (
            <p>已生成候选知识模型版本。</p>
          )}
          <div className="button-row">
            <button
              type="button"
              disabled={busy || installation.status !== "ACTIVE"}
              onClick={() => void control("disable")}
            >
              禁用并重组
            </button>
            <button
              type="button"
              disabled={busy || !installation.previous_installation_id}
              onClick={() => void control("rollback")}
            >
              回滚
            </button>
          </div>
          <TechnicalDetails>
            {installation.candidate_schema_version_id && (
              <code>候选模型 {installation.candidate_schema_version_id}</code>
            )}
            <code>{installation.workflow_id}</code>
          </TechnicalDetails>
        </div>
      )}
    </section>
  );
}

function isDeveloperFixture(pack: DomainPackVersion) {
  return /NEXWEAVE test fixtures|failure-|synthetic|stub|isolat(?:ed|ion)|technical pilot/i.test(
    `${pack.publisher} ${pack.pack_key} ${pack.pack_version}`,
  );
}

function operationLabel(value: string) {
  return (
    {
      INSTALL: "安装",
      UPGRADE: "升级",
      DISABLE: "停用",
      ROLLBACK: "回滚",
    }[value] ?? value
  );
}
