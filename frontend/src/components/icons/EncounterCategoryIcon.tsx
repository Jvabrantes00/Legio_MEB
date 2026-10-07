interface EncounterCategoryIconProps {
  className?: string;
  label?: string;
}

export function EncounterCategoryIcon({ className = "h-5 w-5", label }: EncounterCategoryIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={label ? "img" : undefined}
      aria-hidden={label ? undefined : true}
    >
      {label ? <title>{label}</title> : null}
      <path d="M3.5 18.5 9.2 9l2.7 4.2 2.5-3.3 6.1 8.6" />
      <path d="m7.7 11.5 1.5-2.5 1.4 2.2" />
      <path d="M5 18.5h14" />
      <path d="M16.9 5.2v4.1" />
      <path d="M16.9 5.2h3l-1 1.2 1 1.2h-3" />
    </svg>
  );
}
