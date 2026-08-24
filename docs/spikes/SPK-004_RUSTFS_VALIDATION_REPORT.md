# SPK-004 RustFS / SourceVersion 对象存储验证报告

- Date: 2026-08-24
- Environment: macOS Apple Silicon, Docker Desktop, real RustFS Compose service
- Image: `quay.io/rustfs/rustfs:1.0.0-rc.3@sha256:800cf3f352a0a27e3275ca854a51f0027975d7acc7a0d52089a35bcc9fcbf0b5`
- Result: M0 S3/provider compatibility, single-node recovery and dual-architecture supply-chain gates **PASSED**
- Scope boundary: no Source business API, DB aggregate or scanning engine was implemented in M0

## Reproduction

1. Start the accepted M0 Compose environment.
2. Install the exact development lock and run `make PYTHON=.venv/bin/python rustfs-spike`.
3. The script creates two random, versioned, synthetic buckets, runs the matrix below, restarts only RustFS, performs a provider-neutral logical restore, writes an ignored local JSON receipt and removes all temporary versions/buckets.

The script automatically bypasses a host-wide proxy only for a loopback endpoint. It does not disable or modify the user's global proxy settings. Credentials are read from the ignored local environment and are never written to the report or logs.

## S3 compatibility matrix

| Capability | Method / invariant | Result |
|---|---|---|
| PUT/GET/HEAD/list | 1 MiB synthetic Raw object; length, metadata SHA-256 and downloaded bytes checked | PASS |
| Checksum | `Content-MD5`, `ChecksumSHA256`, application SHA-256 metadata and post-download SHA-256 | PASS |
| Range | `bytes=1024-4095` compared byte-for-byte | PASS |
| Same-key protection | `If-None-Match: *` must return 409/412 class denial | PASS |
| Versioning | two writes produce distinct version IDs; first version remains readable | PASS |
| Anonymous access | direct object URL denied | PASS |
| Wrong credentials | signed request with invalid access/secret denied | PASS |
| Presigned GET | authorized URL returns expected bytes; one-second URL denied after expiry | PASS |
| Multipart | 5 MiB + 1 MiB parts; repeated part has stable ETag; complete checksum matches | PASS |
| Abort | abandoned multipart upload removed from active upload listing | PASS |
| Lifecycle | abort-incomplete rule round-trips through S3 API | PASS |
| Restart recovery | RustFS container restart; object and checksum preserved | PASS |
| Logical backup/restore | list/get/put into a second bucket; every restored object SHA-256 checked | PASS |
| Cleanup | all object versions, delete markers and both temporary buckets removed | PASS |

## Evidence

- Local receipt SHA-256: `5256918ff5150c4b9945ae2f9d4dd53081b670ffea0784ffd4a0a703620b0f86`.
- RustFS ARM64 CycloneDX SBOM SHA-256: `33d202fef59e4e326cd7037eec12d82a624c3cd8e47e4e4370b2c53da85d2f87`.
- RustFS ARM64 Trivy JSON SHA-256: `0774ef10a49a4d6ce9d9c4693cc58b8922d7d7648dcc3b03218765ab402f7b69`; fixed-version HIGH/CRITICAL count: **0**.
- Scanner: official `ghcr.io/aquasecurity/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969`, DB `ghcr.io/aquasecurity/trivy-db:2`, policy `HIGH,CRITICAL + ignore-unfixed + exit-code 1`.
- Upstream signature check: Cosign v3.0.2 found no signature/SBOM artifacts on the fixed RustFS Quay index. NEXWEAVE therefore mirrors the exact digest only after checks and signs it as an internal approval artifact; the result must not be described as upstream provenance.

The full local JSON/SBOM/scan files remain ignored because they are generated artifacts. GitHub Actions run `32702688049` for commit `e03efd9949914740761ecca9a1a6380ddee891c1` completed successfully: quality, Compose integration, API/Worker/Web dual-architecture images and the RustFS approval image all passed. Evidence artifacts are `container-evidence-api`, `container-evidence-worker-health`, `container-evidence-web` and `container-evidence-rustfs`; CI also verified every Cosign certificate identity against the main workflow.

## Object, state and error conclusions

ADR-0018 freezes the recommended Raw key, conditional write, checksum, idempotency, download authorization, multipart compensation and logical backup rules. It also resolves the old state-document conflict: upload sessions have separate transient states, while SourceVersion uses only the accepted `STORED/PARSING/PARTIAL/PARSED/FAILED/SUPERSEDED` vocabulary. Scanning is a SourceIngestion Workflow gate before parsing; business implementation and malware-engine validation remain M1/M3 work and are not falsely counted as M0 functionality.

## Residual limits

- This run validates single-node RustFS and the approved S3 subset. It does not validate distributed mode, rolling upgrade/downgrade, storage-node loss, RPO/RTO, throughput or large-data lifecycle execution.
- RustFS remains an RC. R1 pilot promotion must consume the approved signed digest backed by run `32702688049`; production HA/DR claims remain gated by M7/M12 tests.
- No real customer file, confidential data, SourceVersion row or Release object was created.
