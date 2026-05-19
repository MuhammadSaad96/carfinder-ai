interface FilterBadgesProps {
  filters: Record<string, unknown>;
}

const FILTER_LABELS: Record<string, string> = {
  max_price: "Max Budget",
  min_price: "Min Price",
  city: "City",
  transmission: "Transmission",
  fuel_type: "Fuel",
  max_mileage: "Max Mileage",
  min_year: "From Year",
  make: "Brand",
  model_name: "Model",
};

function formatValue(key: string, value: unknown): string {
  if (key === "max_price" || key === "min_price") {
    const num = Number(value);
    return `PKR ${(num / 100_000).toFixed(0)} Lacs`;
  }
  if (key === "max_mileage") return `${Number(value).toLocaleString()} km`;
  return String(value);
}

export default function FilterBadges({ filters }: FilterBadgesProps) {
  const active = Object.entries(filters).filter(
    ([k, v]) => v !== null && v !== undefined && k !== "search_keywords"
  );

  if (active.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {active.map(([key, value]) => (
        <span
          key={key}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-purple-950/60 border border-purple-500/25 text-sm text-purple-300"
        >
          <span className="text-purple-500 text-xs font-medium">
            {FILTER_LABELS[key] || key}:
          </span>
          {formatValue(key, value)}
        </span>
      ))}
    </div>
  );
}
