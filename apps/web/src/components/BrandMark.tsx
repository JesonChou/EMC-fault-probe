import { RadioTower } from "lucide-react";

export function BrandMark({ large = false }: { large?: boolean }) {
  return (
    <span className={large ? "brand-mark brand-mark--large" : "brand-mark"} aria-hidden="true">
      <RadioTower size={large ? 25 : 16} strokeWidth={2.1} />
    </span>
  );
}
