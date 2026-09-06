// Identidad de marca Tridenty (tomada de los SVG oficiales de tridenty.io):
// el tridente cian y el wordmark "TRIDENTY". El wordmark usa `currentColor`
// en las letras para adaptarse a modo claro/oscuro; el tridente y el acento
// de la "E" van siempre en el cian de marca (#5bc2e7).

type SvgProps = { className?: string; title?: string };

/** Tridente de marca — símbolo cian, autocontenido (sirve en cualquier fondo). */
export function TridentMark({ className, title = "Tridenty" }: SvgProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 298.95 450"
      role="img"
      aria-label={title}
      xmlns="http://www.w3.org/2000/svg"
    >
      <g fill="#5bc2e7">
        <polygon points="113.84 341.87 113.84 411.52 87.91 392.13 87.91 354.92 28.95 311.19 38.31 97.05 62.25 143.11 55.45 298.57 113.84 341.87" />
        <polygon points="183.75 411.55 183.75 341.87 242.17 298.57 235.37 143.14 235.37 143.11 259.28 97.05 268.67 311.19 209.67 354.92 209.67 392.13 183.75 411.55" />
        <polygon points="173.38 91.96 161.77 101.32 161.77 448.78 135.85 448.78 135.85 101.32 124.24 91.96 148.81 1.22 173.38 91.96" />
      </g>
      <g fill="#2f9ec2">
        <polygon points="113.84 411.52 113.84 443.61 24.28 377.18 25.58 345.9 113.84 411.52" />
        <polygon points="273.3 377.21 183.75 443.61 183.75 411.55 272.01 345.93 273.3 377.21" />
      </g>
    </svg>
  );
}

/** Wordmark "TRIDENTY" — letras en currentColor, crossbar de la "E" en cian. */
export function TridentyWordmark({ className, title = "TRIDENTY" }: SvgProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 1110.71 189.63"
      role="img"
      aria-label={title}
      xmlns="http://www.w3.org/2000/svg"
    >
      <g fill="currentColor">
        <path d="M2.48,42.98h127.78v18.88h-55.18v84.95h-23.23V61.85H2.48v-18.88Z" />
        <path d="M276.78,97.87c4.35-5.33,6.54-12.68,6.54-22.07,0-11.04-2.99-19.26-8.94-24.7-5.94-5.42-14.3-8.13-25.04-8.13h-86.98v18.89h84.22c4.26,0,7.53,1.04,9.8,3.12,2.28,2.07,3.42,5.69,3.42,10.82s-1.14,8.61-3.42,10.74c-2.27,2.13-5.54,3.2-9.8,3.2l-84.22-.14v57.19h23.23v-38.18h47.92l22.22,38.18h26.42l-23.96-38.9c8.04-1.37,14.24-4.7,18.59-10.02Z" />
        <path d="M316.13,146.8V42.98h23.23v103.82h-23.23Z" />
        <path d="M375.08,146.8V42.98h17.13l46.47-.15c18.78,0,33.35,4.41,43.71,13.21,10.36,8.81,15.54,21.73,15.54,38.77s-5.18,29.96-15.54,38.77c-10.36,8.81-24.93,13.21-43.71,13.21h-63.6ZM437.08,61.71h-38.77v66.21h38.77c12.2,0,21.44-2.66,27.74-7.99,6.29-5.32,9.44-13.7,9.44-25.12s-3.15-19.92-9.44-25.19c-6.29-5.28-15.54-7.91-27.74-7.91Z" />
        <path d="M527.83,42.97v18.89h113.85v-18.89h-113.85ZM551.07,127.92v-24.25h-23.24v43.12h113.85v-18.87h-90.61Z" />
        <path d="M673.04,146.8V42.98h23.52l73.47,74.64V42.98h23.23v103.82h-23.52l-73.48-74.78v74.78h-23.23Z" />
        <path d="M825.36,61.87v-18.9h127.78v18.88h-55.18v84.95h-23.23V61.85h-25.85l-23.52.02Z" />
        <path d="M1030.1,146.8v-37.03l-55.03-66.79h28.75l37.9,47.05,37.75-47.05h28.75l-54.74,66.65v37.17h-23.38Z" />
      </g>
      <rect fill="#5bc2e7" x="527.83" y="84.8" width="75.26" height="18.87" />
    </svg>
  );
}
