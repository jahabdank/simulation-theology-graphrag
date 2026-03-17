export const ST = {
  blue: "#6B8CFF",
  coral: "#F07050",
  orange: "#F28C50",
  peach: "#F9B870",
  lightPeach: "#F5C4A0",

  navy: "#181A2E",
  navyLight: "#1E2040",
  cream: "#FAF5F0",
  white: "#FFFFFF",

  textDark: "#1A1A2E",
  textGrey: "#6B7280",
  textLight: "#E5E7EB",

  success: "#10B981",
  warning: "#FFD700",
  error: "#FF4444",

  inactive: "#555555",
  border: "#2A2D4A",
} as const;

export const TYPE_COLORS: Record<string, string> = {
  axiom: ST.coral,
  entity: ST.orange,
  concept: ST.blue,
  architectural_component: "#8B9FFF",
  biblical_figure: ST.success,
  religious_concept: "#B07CFF",
  st_term: ST.peach,
  scripture_mapping: "#9CA3AF",
  UNKNOWN: ST.textGrey,
};

export const TYPE_LABELS: Record<string, string> = {
  axiom: "Axiom",
  entity: "Entity",
  concept: "Concept",
  architectural_component: "Architecture",
  biblical_figure: "Biblical Figure",
  religious_concept: "Religious Concept",
  st_term: "ST Term",
  scripture_mapping: "Scripture Mapping",
  UNKNOWN: "Unknown",
};
