# NEXWEAVE Project Status

- Current Release: R1（M0—M9）
- Current Milestone: M9.5 Stage D trusted-read consolidation completed local technical verification on 2026-09-10 (11F / ADR-0036). Query/Graph guards, source navigation and key browser flows verified; 162 Python and 33 Web tests passed. Runtime 0.9.5-d1. M9 expert/industrial acceptance remains open; stop at D, no M10.
- Business implementation: M1—M8 are formally accepted; M9 adds a declarative signed Equipment RCA Pack, admitted NTSB corpus and four-source Pack→Source→Compile technical pilot without claiming expert acceptance, customer applicability or GridCrew integration
- Git repository: `https://github.com/yingerfeng-cloud/NEXWEAVE.git`, local `main` preserves the remote initial commit without force-push
- Git baseline before the M1/M2 delivery commit: `727811f`; the user authorized and pushed the M1/M2 delivery and CI closeout on 2026-08-25. Functional gate commit `ddbcc6e` is on `origin/main` and GitHub Actions run `32808198635` passed
- M0: Explicitly dispatched by the user on 2026-08-23
- M1: Explicitly dispatched by the user on 2026-08-24
- M1: Formally accepted by the user on 2026-08-24
- M2: Explicitly dispatched by the user on 2026-08-24
- M2: Formally accepted by the user on 2026-08-25
- M3: Formally dispatched by the user on 2026-08-25 with an explicit sequence of M0—M2-aligned taskbook calibration, formal implementation and independent post-implementation review; formally accepted by the user on 2026-08-29
- M4: Formally dispatched by the user on 2026-08-29; M4-0 is frozen by ADR-0023, implementation/local acceptance completed on 2026-08-30, and the user formally accepted M4 on 2026-08-30 without dispatching M5
- M5: Formally dispatched, locally technically accepted and formally accepted by the user on 2026-08-30; disclosed remote-CI/external-provider/crash-window risks remain tracked
- M6: Formally dispatched by the user on 2026-08-30; ADR-0025, implementation and local technical verification completed, and formally accepted by the user on 2026-08-31; M7 was subsequently dispatched and accepted separately
- M7: Formally dispatched, implemented, locally technically verified and formally accepted by the user on 2026-08-31
- M8: Formally dispatched, implemented, locally technically verified and formally accepted by the user on 2026-08-31; GridCrew remains deferred and M9 was not dispatched
- M9: Formally dispatched by the user on 2026-09-01; signed Pack delivery, 9-report admission and a four-report audited Source→Compile technical pilot are implemented. GridCrew is deferred; expert identity, approved thresholds and real review/release evidence still block acceptance
- M9-FE: Formally dispatched by the user on 2026-09-01 as an M9/R1 frontend-only supplement; the 2026-09-07 UX/UI System Refactor closed all taskbook P0 items and passed four desktop viewport checks, while explicitly retaining route-level PARTIAL items without entering M10 or changing backend contracts

## M8 implementation result

- ADR-0027 freezes the read-only Connector authorization, explicit outbound allowlist, non-secret credential reference, Raw-to-SourceVersion path, Obsidian stable identity and three-way conflict boundary. ADR-0028 freezes the bounded Wiki bidirectional-link graph as a navigation projection separate from the M7 Release graph.
- Additive `0009_m8_connector_obsidian` was applied successfully during the local API deployment; no historical migration, Release, Evidence, SourceAnchor or GridCrew contract was changed.
- Authenticated Connector/Obsidian APIs, generated contracts and Python/TypeScript SDK access are implemented. Connector sync is read-only, follows explicit allowlists, records auditable execution facts and feeds the existing M3 source/parse path.
- The native Wiki graph reads existing page links and reverse references under `page.read`, tenant/space isolation, 1—3 hop and 10—500 node limits. Its 2D Web experience includes page-type colouring, search/filter, pan/zoom, focused link highlighting and navigation back to Wiki pages; it does not depend on a locally installed Obsidian application.
- M8 local verification passed the targeted contract/API/frontend checks, frontend format/lint/type/build and 18 web tests. API deployment rebuilt the API service, applied `0009_m8_connector_obsidian`, and reported ready dependencies. External Secret Provider, production OIDC, per-target network approval and real GridCrew integration remain outside this acceptance.

## M9 execution status

- User dispatch was received on 2026-09-01. ADR-0029 freezes the declarative Pack and pilot-evidence boundary without changing platform objects, APIs, events, Workflow or database semantics.
- Signed `equipment-rca-pack@1.0.0` contains the domain schema, governed identifiers/terminology, evidence-aware causal relations, templates, constrained assistant prompt, lint policy, safe UI metadata and six-behavior/seven-case question set.
- Local verification passed signature/checksum, deterministic core/RCA/maintenance composition, Pack-absent platform operation, global quality gates, migration replay and selected real Temporal/parser integration tests.
- ADR-0030 records 9 official NTSB reports/610 pages as a checksummed, Git-ignored public corpus. All 9 passed text/layout admission; third-party visual pages are excluded and external-model use remains disabled by default.
- Four representative reports completed real signed Pack installation, Raw-preserving/text-derivative Source ingestion and deterministic Compile: 368 ClaimCandidate, 377 EvidenceCandidate and 9 RelationCandidate. Formal Claim, ReviewCase and Release remain zero.
- The pilot exposed and closed the Web 1 MB upload limit and the M4/M7 `evaluation_suites.created_by` persistence incompatibility; targeted tests and isolated-tenant runtime installation now pass.
- GridCrew is explicitly deferred and no longer a M9 P0 or acceptance item; it remains unimplemented and cannot be claimed as completed.
- M9 remains not accepted and cannot enter M10: expert identity, approved thresholds, real Review/Evaluation/Release/Query records remain outstanding. Public-source admission and Source→Compile technical E2E are no longer blockers.

## M9-FE execution status

- The versioned frontend baseline freezes route-to-prototype/API/state mappings, design tokens, component contracts, dependency strategy, migration batches and intentional deviations.
- Login plus all 17 protected routes now share the deep-black, violet, cyan and lime NEXWEAVE shell and responsive component system; the previously orphaned real Task Center is reachable at `/tasks` with legacy `/compile/:id` deep-link compatibility retained.
- Browser verification covers 1440×900, 1024×768 and 390×844 with real local API state, including back/forward navigation, visible keyboard focus and a clean runtime console. The Compose Web image was rebuilt after final review and rebuilt again after the 2026-09-02 frontend quality pass; the replacement `8080` container is healthy and was verified through a real local-admin login.
- Frontend format, lint, strict typecheck, all 22 Vitest tests and production build pass. No dependency, database migration, API, Workflow, Release or Evidence semantic changed.
- M9-FE is locally technically accepted and stopped. This does not constitute user acceptance of M9 or authorize M10.
- The 2026-09-07 system-refactor follow-up uses desktop Web as the acceptance scope, passes 1366×768/1440×900/1920×1080/2560×1440 overflow and prohibited-label checks, and records remaining Schema/Graph/Workspace/Admin workflow depth as PARTIAL rather than claiming complete product coverage.

## M7 implementation result

- ADR-0026 freezes versioned Evaluation facts, explicit ReleaseCandidate item locks, independent Publisher approval, immutable Release manifest/items, pointer-only rollback and single-Release query semantics.
- Additive `0008_m7` adds quality, Release, pointer/history, pgvector/FTS projection, Relation, QuerySession/Answer/Citation facts and immutable guards without modifying historical migrations.
- `nexweave.quality-evaluation.v2` and `nexweave.knowledge-release.v2` keep I/O in Activities and preserve earlier Workflow definitions.
- Real isolated E2E verified two immutable Releases, 100% traceability/Schema gates, independent approval, reproducible evidence citations, insufficient-evidence refusal, JSON export, projection rebuild and pointer-only rollback.
- Existing accepted M6 data was only copied into an isolated temporary database; the temporary database and dump were removed after verification. No shared Release pointer was changed.

## M6 implementation result

- ADR-0025 freezes Evidence-gated formal Claim semantics, clustered ConflictCase/append-only decisions, policy-configured staged review and high-risk duty separation.
- Additive `0007_m6` adds ReviewPolicy/Case/Task/Action, formal Claim/Evidence and ConflictCase/Item/Decision tables with immutable fact guards; it does not modify M0—M5 migrations.
- `nexweave.human-review.v2` materializes its review projection and waits for the final audited decision; historical `v1` remains registered unchanged.
- API/SDK/OpenAPI/JSON Schema and deep-linkable Claim, Conflict and Review web centers are real-service driven. Synthetic local E2E has verified a three-person high-risk review produces a formal Claim with accepted Evidence.

## M5 implementation result

- ADR-0024 freezes immutable Compile inputs, provider-neutral Model Gateway audit, stable Entity/Page identity, candidate-only semantics, protected Wiki sections and v1/v2 Workflow compatibility.
- Additive `0006_m5` implements CompileJob/source/step/model-invocation facts, stable candidate knowledge, append-only Wiki versions, links/comments/follows, Evidence/Conflict/Lint candidates and immutable database guards.
- `nexweave.knowledge-compile.v2` fixes exact Source/Schema/Prompt/Model inputs and performs model/database I/O only in Activities; v1 remains registered unchanged for historical replay.
- Authenticated APIs, generated OpenAPI/JSON Schemas/events, Python/TypeScript SDKs, API-driven Compile Center and Wiki Workbench are implemented. Failed work is retried as a new auditable CompileJob.
- Real M5 E2E passed Source parse→published Schema→Compile→stable Entity/Relation/Claim/Evidence/Conflict→Wiki version/protected section/link/comment/follow, audit/trace and consumer draft denial. The provider was explicitly the deterministic no-network `nexweave.local-structured/1`; no external LLM call is claimed.
- Full Python suite passed 106 tests; Web 13 tests/build, strict mypy, Ruff, contract snapshots, migration `0001→0006→0005→0006`, secret scan and M5 real E2E passed. Remote CI/image promotion was not run because no commit/push was authorized.

## M4 implementation result

- ADR-0022/0023 freeze SchemaVersion as the sole semantic authority, lower-case namespaced stable keys, JSON-only RFC8785-JCS/1 canonical artifacts, Ed25519 trust/revocation, preview-only migration DSL and the declarative UI allowlist.
- Additive `0005_m4` implements immutable Schema/semantic facts, exact Pack inputs, trust roots, signed Pack versions, revocations, installations, composition reports and migration previews with tenant/space composite integrity.
- Pure-domain deterministic composition validates dependency/type DAGs, references, inherited constraints, relation endpoints, term/mapping ambiguity and exact mappings; repeated and input-order-permuted composition produces the same checksum.
- `nexweave.domain-pack-install.v2` performs installation/upgrade/disable/rollback through retryable Activities while preserving M2 v1 registration and replay compatibility. Installation creates a DRAFT candidate and never publishes implicitly.
- Authenticated API, OpenAPI/JSON Schema/events, Python/TypeScript SDKs, real Schema Studio and Pack Center are implemented. Pack UI declarations reject executable, remote and dynamic content.
- Real PostgreSQL M0→M4→M3→M4, complete Compose M4 E2E, Temporal v1/v2 replay and M0—M3 regression all passed. The verified published composition checksum is `sha256:a71aca50382c18ca54c12f196337d7939ab49bcc35812685548d38a9c85f9931`.
- No M4 dependency was added; existing locked `cryptography` supplies Ed25519. Local secret/dependency/format/lint/type/unit/contract/Web/build checks are recorded in the M4 execution report. Remote multi-architecture CI/promotion is not claimed because no commit or push was authorized.

## M3 implementation status

- The M3 taskbook has been calibrated against the accepted M0—M2 code, migrations, Workflow, security and contract baselines; the user already authorized formal implementation after this calibration.
- ADR-0021 freezes Source/Parse failure, partial success, retry, reparse, version replacement, v1/v2 Workflow compatibility and SourceAnchor relocation semantics from existing authoritative principles.
- M2 `nexweave.source-ingestion.v1` remains a Kernel Stub and Replay baseline. It is not Source/parse evidence and will not be relabeled as M3 completion.
- `SourceDocument`, immutable `SourceVersion`/Raw registration, `ParseJob`, Segment/Anchor/Invalidation facts, upload batches, v2 Workflow, API/UI/SDK and additive `0004_m3_source_parsing` are implemented.
- Six real bounded adapters cover PDF, DOCX, Markdown, TXT, CSV and XLSX. Scanned PDF detection is real; no OCR Provider is configured, so affected pages truthfully report `OCR_REQUIRED/PARTIAL_FAILED`.
- A credentialed Activity coordinator performs trusted I/O; third-party document parsing runs in a separate non-root, read-only, resource-bounded, credential-free `parser-sandbox` container on a dedicated internal IPC network.
- Independent post-implementation review found permission, mixed-classification, concurrency, manifest, locator, upload-terminal and isolation defects. Those code paths have been remediated; local format/lint/type/unit/contract/UI/build/security regression passed. This status is not an acceptance claim.
- Real PostgreSQL `0001 → 0004 → 0003 → 0004` passed in an automatically generated disposable database, including checks for 10 M3 tables, 6 database guards and the replacement uniqueness constraint. Real Temporal v1/v2 newly-created history replay also passed; replay of an archived accepted-M2 history is not claimed.
- On 2026-08-29, the Docker Hub-only ClamAV pull obstruction was removed from the local acceptance path by a reproducible image built from the already accepted Debian 12 base and exact official Debian packages `clamav-daemon/freshclam=1.4.3+dfsg-1~deb12u2`. FreshClam loaded daily 28106, main 63 and bytecode 339 before clamd became healthy.
- The complete real Compose chain is running, every service that defines a healthcheck is healthy, and both `.venv/bin/python scripts/verify_m1.py` and `.venv/bin/python scripts/verify_m3.py` passed, covering RustFS, the real clean/EICAR ClamAV gate, the credentialed coordinator, credential-free parser sandbox IPC, Temporal, PostgreSQL and API/Web. The local ClamAV image also has zero fixable HIGH/CRITICAL findings under Trivy 0.74.0. The local M3 P0 is closed; GitHub Actions run `33253911959` passed all ten jobs with remote dual-architecture promotion, SBOM, CVE and Cosign evidence; M3 was formally accepted by the user on 2026-08-29.

## M2 implementation result

- Dedicated `nexweave-dev` Temporal namespace, separate Workflow/Activity task queues and a non-root kernel Worker now run the seven named Workflow definitions;
- Stable business/Workflow/Run mapping, Update/Signal control, durable approval wait, timeout escalation, Activity timeout/retry/heartbeat, cancellation compensation and duplicate-command handling are implemented without direct Workflow I/O;
- PostgreSQL `WorkflowTask`, `WorkflowStep` and append-only `WorkflowTaskEvent` projections, audit/Outbox, lag indication and Temporal reconciliation/repair are exposed through authenticated APIs and typed SDKs;
- The Web task center is driven by real APIs and supports list/detail/steps/logs/actions, deep links, refresh recovery and truthful M2 Stub boundaries;
- Real Compose verification passed all seven Workflow types, transient retry, approval, pause/resume, cancellation compensation, duplicate Update, projection repair, Worker restart and replay; isolated PostgreSQL `base → head → base → head` migration verification passed;
- The official Temporal SDK time-skipping test now runs as an independent Linux x64 CI gate; local execution passed and the remote `temporal-time-skipping` job passed in run `32808198635`;
- GitHub Actions run `32808198635` passed all eight quality, time-skipping, Compose integration, four application-image and RustFS approval jobs. Dual-architecture SBOM/CVE evidence and Cosign signature verification were uploaded successfully;
- M2 was formally accepted by the user on 2026-08-25 and remains stopped. M3 was subsequently dispatched, calibrated, implemented, independently reviewed, locally P0-verified, remotely promoted and formally accepted by the user on 2026-08-29.

## M-1 result

治理、资料归档、产品/架构/领域/数据/API/事件/Workflow/Pack/GridCrew/安全/质量/需求追踪、ADR 和 Spike 基线已建立。用户于 2026-08-23 正式验收通过 M-1。开放问题和 Proposed ADR 作为 M0 评审输入保留，不代表已被静默批准。

## M0 scope

- 冻结终局架构、公共契约、状态/版本/权限/错误/事件/幂等边界；
- 建立 Python/TypeScript Monorepo、最小健康检查 API/Web/Worker、基础迁移、Compose、CI 与测试；
- 仅建立通用身份、空间、审计、Outbox、配置和版本骨架，不建立知识业务表或业务 API；
- 继续保持高保真原型为静态参考，不把 Mock 或固定 JSON 冒充业务功能。

## M0 verification status

- 本地 format、lint、typecheck、Python 单元/契约/架构测试、Web 测试与生产构建通过；
- Python 与 JavaScript 生产依赖审计均为零已知漏洞，Secret scan 与 Compose 配置解析通过；
- `PlatformHealthWorkflow` 已在 Temporal 官方测试服务上真实执行通过；
- 用户于 2026-08-24 批准对象存储完整切换为 RustFS；ADR-0017、活动架构、Compose、健康检查和开发配置已同步，不保留旧 Provider 回退；
- RustFS 官方 Quay `1.0.0-rc.3` 多架构 digest 已核实，Apple Silicon 原生镜像成功拉取并通过真实 Compose `Healthy` 与宿主 `/health` 验证；
- 用户将 Veee 调整为全局模式后，pgvector、Redis、Temporal、Python、Node、Nginx 官方镜像均已成功拉取，API/Worker/Web 项目镜像构建成功；Docker Hub 原 P0 已解除，但首次认证请求仍出现过一次 IPv6 超时，需继续观察稳定性；
- Temporal 1.29.6 动态配置已改用镜像实际提供的 `config/dynamicconfig/docker.yaml`；Compose 健康检查、API 依赖探测和真实 Worker Workflow 均通过；
- Web 已改用完整非 root Nginx 主配置，健康检查固定到实际 IPv4 回环监听地址；`make dev-up` 已使 PostgreSQL、Redis、RustFS、Temporal、API、Worker、Web 全部启动并通过健康等待；
- `make verify` 已通过 Web → API → PostgreSQL/Redis/RustFS/Temporal → Worker 的真实链路；`make migration-check` 已通过基础迁移升级、回滚和再次升级；
- RustFS SPK-004 已在固定真实镜像上通过 S3 子集、条件写、版本、鉴权、multipart、生命周期、重启与逻辑备份恢复；对象 key、状态、补偿和供应链规则由 ADR-0018 冻结；
- API、Worker、Web、RustFS 镜像本地复扫的可修复 HIGH/CRITICAL 均为 0；主分支 CI 对四类镜像构建/验证 amd64 与 arm64、生成 CycloneDX/CVE artifacts 并以 GitHub OIDC/Cosign 签名不可变 digest；
- GitHub Actions run `32702688049` 对提交 `e03efd9` 的 quality、Compose integration、API/Worker/Web images、RustFS approval image 六个 job 全部成功；外部 CI、容器供应链与 SPK-004 的 M0 P1 收尾已闭环；
- 当前 M0 P0/P1 阻塞均为零。用户于 2026-08-24 已正式验收通过 M0，并于同日正式下发 M1。

## M1 implementation result

- OIDC-compatible/local development identity、服务身份、audience 校验、默认拒绝 RBAC+ABAC 和 tenant/space/classification 隔离已实现；
- KnowledgeSpace 创建/编辑/归档、成员授权/撤销、治理配置、审计/Outbox/幂等、OpenTelemetry 和受控 RustFS 对象链路已形成真实 API/DB 闭环；
- Web 已实现登录态、空间恢复、16 个深链接路由、权限守卫、空间与管理真实页面；后续模块只陈述边界且无 Mock；
- `0002_m1_platform_services` 真实 PostgreSQL 升级/回滚/再升级通过；最终 Compose 七服务均运行，六个带 healthcheck 的服务为 healthy，Worker Workflow 通过，真实 E2E 两次通过；
- `make check` 通过 Python 28 项、契约 14 项、Web 5 项及 format/lint/typecheck/SDK/build；Secret/SCA/Compose/diff 门禁通过；
- M1 验收时独立 Temporal SDK time-skipping 下载未取得结果；该历史披露已在 M2 收尾中由本地真实通过及远程独立门禁关闭，不改变 M1 无长业务 Workflow 的验收边界；
- M1 无新增 P0。远程 CI 与镜像供应链重跑已由 run `32808198635` 关闭；P1 保留生产 OIDC/Secret Provider/HTTPS 部署联调，P2 保留 OTel contrib `0.65b0` 兼容观察和后续 RLS 纵深评估。

## Hard boundaries

- 当前已验收至 M8；M9 已下发并完成声明式 Pack、公开资料准入和四份代表性 Source→Compile 技术试点；GridCrew 按用户指令延期且未实现，专家 Review/Evaluation/Release/Query 仍未完成。M2 v1 同名 Workflow 仍仅为历史可靠内核 Stub；
- 高保真原型仍是静态演示，不是已完成功能；
- 未提供合规脱敏 RCA 试点资料；
- M8 已由用户正式验收；M9 已正式下发但尚未验收。GridCrew 为延期项而非 P0；公开资料准入和 Source→Compile 已完成，专家/阈值/真实评审与 Release 为剩余 P0。
- ADR-0022—0024 与 M4/M5 公共契约已经实现；任何后续语义改义仍须新 ADR 和明确 Milestone 授权。
