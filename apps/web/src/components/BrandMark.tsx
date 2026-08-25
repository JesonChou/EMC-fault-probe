export function BrandMark({ large = false }: { large?: boolean }) {
  return (
    <span className={large ? "brand-mark brand-mark--large" : "brand-mark"} aria-hidden="true">
      <img src="./emc_fault_probe.ico" alt="" />
    </span>
  );
}
