/**
 * AstroHealth's own mark: a pulse trace that leaves the baseline and climbs to a point.
 * The trace is NASA Blue and the point NASA Red, on a white tile so both keep their contrast.
 * It is not the NASA insignia and does not imitate it.
 */
export function BrandMark({ size = 32 }: { size?: number }) {
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="7" fill="#FFFFFF" />
      <path
        d="M4.5 19.5h5.6l2.6-7.2 4 12.2 2.9-8.4h2.2l3.2-5.6"
        fill="none"
        stroke="#0032A0"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="25.6" cy="9.2" r="2.9" fill="#E4002B" />
    </svg>
  )
}
