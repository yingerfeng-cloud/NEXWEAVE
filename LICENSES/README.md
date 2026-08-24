# Third-party dependency governance

M0 introduces exact-pinned runtime and development dependencies. The reviewed direct inventory, purposes, licenses, alternatives and supply-chain boundaries are maintained in `docs/governance/DEPENDENCY_BASELINE.md`; Python requirements, pnpm lockfile and Compose versions are the machine-readable version evidence.

Before adding a dependency, record:

- package, ecosystem and exact version;
- purpose and owning module;
- license and notice obligations;
- source, checksum/signature or lockfile evidence;
- known vulnerabilities and update policy;
- approved alternative and removal plan;
- whether it processes Raw content, credentials or model data.

Strong-copyleft, source-unknown, unmaintained or critical-vulnerability dependencies require explicit architecture and legal approval.
