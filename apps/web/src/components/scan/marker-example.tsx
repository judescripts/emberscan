/**
 * How the printed marker should look in the video: flat on the ground, the orange WALL EDGE strip
 * against the base of the wall, seen from about 6-10 ft back. Drawn (not a photo) so it matches the
 * real 6 x 8 sheet exactly.
 */

type P = [number, number];

// bilinear point inside a quad (far-left, far-right, near-right, near-left), u across, v toward camera
function q(quad: [P, P, P, P], u: number, v: number): P {
  const [fl, fr, nr, nl] = quad;
  const top: P = [fl[0] + (fr[0] - fl[0]) * u, fl[1] + (fr[1] - fl[1]) * u];
  const bot: P = [nl[0] + (nr[0] - nl[0]) * u, nl[1] + (nr[1] - nl[1]) * u];
  return [top[0] + (bot[0] - top[0]) * v, top[1] + (bot[1] - top[1]) * v];
}
const pts = (ps: P[]) => ps.map((p) => p.join(",")).join(" ");

function Sheet({ quad }: { quad: [P, P, P, P] }) {
  // sheet layout (fractions of the sheet, far edge = wall side): orange strip, then the 6 x 8 board
  const strip = 0.09;
  const b0 = 0.17;
  const b1 = 0.95;
  const bx0 = 0.12;
  const bx1 = 0.88;
  const cells = [];
  for (let r = 0; r < 8; r++)
    for (let c = 0; c < 6; c++) {
      if ((r + c) % 2) continue;
      const u0 = bx0 + ((bx1 - bx0) * c) / 6;
      const u1 = bx0 + ((bx1 - bx0) * (c + 1)) / 6;
      const v0 = b0 + ((b1 - b0) * r) / 8;
      const v1 = b0 + ((b1 - b0) * (r + 1)) / 8;
      cells.push(<polygon key={`${r}-${c}`} points={pts([q(quad, u0, v0), q(quad, u1, v0), q(quad, u1, v1), q(quad, u0, v1)])} fill="#1b1715" />);
    }
  return (
    <g>
      <polygon points={pts(quad)} fill="#ffffff" stroke="#c9beb6" strokeWidth={1} />
      <polygon points={pts([q(quad, 0, 0), q(quad, 1, 0), q(quad, 1, strip), q(quad, 0, strip)])} fill="#ff6a00" />
      {cells}
    </g>
  );
}

export function MarkerExample() {
  const base = 118; // wall base line (y)
  const good: [P, P, P, P] = [
    [118, base],
    [214, base],
    [236, 196],
    [92, 196],
  ];
  return (
    <figure className="mt-4">
      <svg viewBox="0 0 340 214" className="w-full rounded-xl" role="img" aria-labelledby="marker-ex-title">
        <title id="marker-ex-title">
          Example: the printed marker lying flat on the ground, its orange WALL EDGE strip touching the base of the wall
        </title>
        {/* wall: upper face and beige base band */}
        <rect x="0" y="0" width="340" height={base} fill="#e9e3dd" />
        <rect x="0" y="70" width="340" height={base - 70} fill="#cfc2b0" />
        <line x1="0" y1="70" x2="340" y2="70" stroke="#b9ab98" strokeWidth={1} />
        {/* ground */}
        <rect x="0" y={base} width="340" height={214 - base} fill="#8a6a4f" />
        <rect x="0" y={base} width="340" height={214 - base} fill="url(#soil)" opacity={0.35} />
        <defs>
          <pattern id="soil" width="9" height="7" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="0.9" fill="#3d2b1f" />
            <circle cx="6.5" cy="5" r="0.7" fill="#c9a882" />
          </pattern>
        </defs>
        <line x1="0" y1={base} x2="340" y2={base} stroke="#5b4636" strokeWidth={1.5} />
        {/* shrub against the wall, for context */}
        <g>
          <ellipse cx="286" cy={base + 2} rx="38" ry="10" fill="#3f5a2c" opacity={0.6} />
          <circle cx="270" cy="96" r="22" fill="#4d7036" />
          <circle cx="296" cy="88" r="25" fill="#5c8340" />
          <circle cx="314" cy="104" r="17" fill="#4a6b33" />
        </g>
        <Sheet quad={good} />
        {/* callouts */}
        <g fontFamily="inherit" fontSize="10.5" fontWeight={700} fill="#1b1715">
          <line x1="166" y1={base - 1} x2="166" y2="42" stroke="#ff6a00" strokeWidth={1.5} />
          <circle cx="166" cy={base - 1} r="3" fill="#ff6a00" />
          <rect x="70" y="20" width="192" height="26" rx="13" fill="#ffffff" stroke="#ff6a00" />
          <text x="166" y="37" textAnchor="middle">
            Orange edge touches the wall
          </text>
          <rect x="240" y="164" width="96" height="38" rx="10" fill="#ffffff" opacity={0.92} />
          <text x="290" y="180" textAnchor="middle">
            Flat on the
          </text>
          <text x="290" y="193" textAnchor="middle">
            ground
          </text>
        </g>
      </svg>
      <figcaption className="mt-2 grid grid-cols-3 gap-2 text-center text-[11px] leading-tight">
        <span className="rounded-lg bg-pass-soft px-2 py-1.5 font-semibold text-pass">✓ Flat, orange edge on the wall</span>
        <span className="rounded-lg bg-fail-soft px-2 py-1.5 font-semibold text-fail">✗ Gap between sheet and wall</span>
        <span className="rounded-lg bg-fail-soft px-2 py-1.5 font-semibold text-fail">✗ Leaning or standing up</span>
      </figcaption>
    </figure>
  );
}
