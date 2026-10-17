import type { ReviewTarget } from "./types";

export function targetText(target: ReviewTarget) {
  const value = target.content;
  return String(
    value.statement ??
      value.summary ??
      value.markdown ??
      value.relation_type_key ??
      value.proposal_type ??
      target.target_type,
  );
}
