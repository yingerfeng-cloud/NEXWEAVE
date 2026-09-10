/** Local, code-native navigation symbols; no external fonts or assets. */
export function Icon({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  const paths: Record<string, string> = {
    overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    spaces: "m12 3 9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5",
    sources: "M14 3H5v18h14V8z M14 3v5h5 M8 12h8 M8 16h6",
    tasks: "M9 5h12 M9 12h12 M9 19h12 M3 5l1 1 2-2 M3 12l1 1 2-2 M3 19l1 1 2-2",
    compile: "m13 2-9 12h7l-1 8 10-12h-7z",
    wiki: "M12 6C9 3 5 3 2 4v15c4-1 7-1 10 2 3-3 6-3 10-2V4c-3-1-7-1-10 2z M12 6v15",
    schemas: "M8 3H4v18h4 M16 3h4v18h-4 M9 8l-3 4 3 4 M15 8l3 4-3 4",
    "domain-packs": "m12 2 9 5v10l-9 5-9-5V7z M3 7l9 5 9-5 M12 12v10 M7 4l10 5",
    graph:
      "M9 5a3 3 0 1 0 6 0 3 3 0 1 0-6 0 M2 18a3 3 0 1 0 6 0 3 3 0 1 0-6 0 M16 18a3 3 0 1 0 6 0 3 3 0 1 0-6 0 M10 8l-4 7 M14 8l4 7 M8 18h8",
    claims: "m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6z M8 12l3 3 5-6",
    conflicts: "m12 3 10 18H2z M12 9v5 M12 17v1",
    reviews: "M14 3H4v18h16v-7 M8 9h3 M8 14h3 M14 9l3 3 5-7",
    quality: "M3 21V11h4v10 M10 21V6h4v15 M17 21V2h4v19",
    releases: "M12 16V3 M7 8l5-5 5 5 M4 14v7h16v-7",
    ask: "M3 4h18v13H8l-5 4z M7 9h10 M7 13h6",
    integrations: "M8 2v5 M16 2v5 M6 7h12v4a6 6 0 0 1-12 0z M12 17v5",
    admin: "M4 6h16 M4 12h16 M4 18h16 M8 3v6 M16 9v6 M10 15v6",
    search: "M16 16l5 5 M3 10a7 7 0 1 0 14 0 7 7 0 1 0-14 0",
  };
  return (
    <svg
      className={`nw-icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] ?? paths.spaces} />
    </svg>
  );
}
