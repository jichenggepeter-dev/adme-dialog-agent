import type { PredictionCategoryName } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const REQUEST_TIMEOUT_MS = 120_000;

export const EXAMPLE_MOLECULES = [
  { name: "Aspirin", smiles: "CC(=O)OC1=CC=CC=C1C(=O)O" },
  { name: "Caffeine", smiles: "Cn1c(=O)c2c(ncn2C)n(C)c1=O" },
  { name: "Acetaminophen", smiles: "CC(=O)NC1=CC=C(C=C1)O" },
  { name: "Ibuprofen", smiles: "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O" },
] as const;

export const CATEGORY_LABELS: Record<PredictionCategoryName, string> = {
  absorption: "Absorption",
  distribution: "Distribution",
  metabolism: "Metabolism",
  excretion: "Excretion",
  toxicity: "Toxicity",
  physicochemical: "Physicochemical",
  drug_likeness: "Drug-likeness",
  benchmark: "Benchmark Percentiles",
  other: "Other",
};

export const CATEGORY_ORDER = Object.keys(CATEGORY_LABELS) as PredictionCategoryName[];
