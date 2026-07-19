import type { SVGProps } from "react";

export function Icon({
  name,
  className = "h-5 w-5",
}: {
  name: string;
  className?: string;
}) {
  const props: SVGProps<SVGSVGElement> = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };
  const paths: Record<string, React.ReactNode> = {
    dashboard: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    compare: (
      <>
        <path d="M8 3H5a2 2 0 0 0-2 2v3" />
        <path d="m3 8 3-3" />
        <path d="m3 8 3 3" />
        <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
        <path d="m21 16-3 3" />
        <path d="m21 16-3-3" />
        <rect x="8" y="8" width="8" height="8" rx="2" />
      </>
    ),
    people: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),
    briefcase: (
      <>
        <rect x="3" y="7" width="18" height="13" rx="2" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        <path d="M3 12h18" />
      </>
    ),
    history: (
      <>
        <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
        <path d="M3 3v5h5" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    sliders: (
      <>
        <path d="M4 21v-7" />
        <path d="M4 10V3" />
        <path d="M12 21v-9" />
        <path d="M12 8V3" />
        <path d="M20 21v-5" />
        <path d="M20 12V3" />
        <path d="M1 14h6" />
        <path d="M9 8h6" />
        <path d="M17 16h6" />
      </>
    ),
    key: (
      <>
        <circle cx="7.5" cy="15.5" r="4.5" />
        <path d="m10.7 12.3 8.8-8.8" />
        <path d="m15 8 3 3" />
        <path d="m17 6 2 2" />
      </>
    ),
    shield: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    docs: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M9 13h6" />
        <path d="M9 17h6" />
      </>
    ),
    sparkle: (
      <>
        <path d="m12 3-1.1 3.2a3 3 0 0 1-1.9 1.9L6 9.2l3 1.1a3 3 0 0 1 1.9 1.9L12 15.5l1.1-3.3a3 3 0 0 1 1.9-1.9l3-1.1-3-1.1a3 3 0 0 1-1.9-1.9Z" />
        <path d="m5 15-.5 1.4a2 2 0 0 1-1.2 1.2L2 18l1.3.4a2 2 0 0 1 1.2 1.2L5 21l.5-1.4a2 2 0 0 1 1.2-1.2L8 18l-1.3-.4a2 2 0 0 1-1.2-1.2Z" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="m13 6 6 6-6 6" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    eyeoff: (
      <>
        <path d="m3 3 18 18" />
        <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
        <path d="M9.9 4.2A10.5 10.5 0 0 1 12 4c7 0 10 8 10 8a18 18 0 0 1-2.1 3.2" />
        <path d="M6.6 6.6C3.4 8.4 2 12 2 12s3 8 10 8a10 10 0 0 0 5.4-1.5" />
      </>
    ),
    alert: (
      <>
        <path d="M10.3 2.9 1.8 17a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 2.9a2 2 0 0 0-3.4 0Z" />
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
      </>
    ),
    upload: (
      <>
        <path d="M12 16V4" />
        <path d="m7 9 5-5 5 5" />
        <path d="M20 16v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3" />
      </>
    ),
  };
  return <svg {...props}>{paths[name]}</svg>;
}
