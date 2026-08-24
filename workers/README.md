# Workers

M0 只实现独立的 `health` Worker 和无 I/O 的确定性 `PlatformHealthWorkflow`。Parse、Compile、Review、Evaluate、Release 等 Worker 必须等待对应 Milestone；其外部操作只能通过可重试、可观测、幂等的 Activity/Task 实现。
