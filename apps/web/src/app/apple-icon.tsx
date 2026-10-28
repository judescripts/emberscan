import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

// Home-screen icon: the logo flame on the nav color (same as icon.svg, without rounded corners;
// iOS rounds it).
export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#2b2421",
        }}
      >
        <svg width="132" height="132" viewBox="0 0 24 24">
          <path
            d="M12.5 2.5c.6 3.2-1.6 4.9-3.2 6.8C7.6 11.2 6.5 13 6.5 15.2A5.5 5.5 0 0 0 12 21a5.5 5.5 0 0 0 5.5-5.6c0-2.3-1.1-3.8-2.2-5.1-.3 1.4-1 2.4-2 2.9.6-3.6-.1-7.4-.8-10.7Z"
            fill="#d9541e"
          />
          <path
            d="M12 21a2.6 2.6 0 0 1-2.6-2.7c0-1.5 1.2-2.4 2.1-3.6.4 1 1.1 1.5 1.8 1.8.8.4 1.3 1 1.3 1.9A2.6 2.6 0 0 1 12 21Z"
            fill="#fff"
            opacity={0.55}
          />
        </svg>
      </div>
    ),
    size,
  );
}
