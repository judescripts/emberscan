import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base({ size = 20, ...rest }: IconProps): SVGProps<SVGSVGElement> {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
    focusable: false,
    ...rest,
  };
}

export function IconBuildings(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="M3 21h18" />
      <path d="M5 21V9l7-5 7 5v12" />
      <path d="M9 21v-6h6v6" />
    </svg>
  );
}

export function IconScan(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" />
      <rect x="8" y="9" width="8" height="6" rx="1" />
      <path d="m16 11 2-1v4l-2-1" />
    </svg>
  );
}

export function IconReport(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="M7 3h7l5 5v13H7z" />
      <path d="M14 3v5h5" />
      <path d="M10 13h6M10 17h4" />
    </svg>
  );
}

export function IconTasks(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="m4 6 1.5 1.5L8 5M4 12l1.5 1.5L8 11M4 18l1.5 1.5L8 17" />
      <path d="M11 6h9M11 12h9M11 18h9" />
    </svg>
  );
}

export function IconSun(p: IconProps) {
  return (
    <svg {...base(p)}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

export function IconMoon(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
    </svg>
  );
}

export function IconExternal(p: IconProps) {
  return (
    <svg {...base({ size: 14, ...p })}>
      <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
    </svg>
  );
}

export function IconCheck(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="m5 12 4 4 10-10" />
    </svg>
  );
}

export function IconX(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export function IconBook(p: IconProps) {
  return (
    <svg {...base(p)}>
      <path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" />
      <path d="M4 19V5M8 7h7" />
    </svg>
  );
}

/** Logo mark: the only place ember orange appears. */
export function Flame({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden focusable={false}>
      <path
        d="M12.5 2.5c.6 3.2-1.6 4.9-3.2 6.8C7.6 11.2 6.5 13 6.5 15.2A5.5 5.5 0 0 0 12 21a5.5 5.5 0 0 0 5.5-5.6c0-2.3-1.1-3.8-2.2-5.1-.3 1.4-1 2.4-2 2.9.6-3.6-.1-7.4-.8-10.7Z"
        fill="var(--ember)"
      />
      <path d="M12 21a2.6 2.6 0 0 1-2.6-2.7c0-1.5 1.2-2.4 2.1-3.6.4 1 1.1 1.5 1.8 1.8.8.4 1.3 1 1.3 1.9A2.6 2.6 0 0 1 12 21Z" fill="#fff" opacity=".55" />
    </svg>
  );
}
