const STEPS = [
  { name: "Track", detail: "SAM 3.1 follows every hazard across the walkaround video." },
  { name: "Measure", detail: "A printed scale marker turns pixels into feet, with ranges." },
  { name: "Check", detail: "A deterministic rules engine cites each California rule." },
  { name: "Plan", detail: "A Muse Spark agent builds the fix plan from those results." },
];

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-12">
      <header className="flex flex-col gap-3">
        <p className="text-sm font-semibold uppercase tracking-wider text-stone-500">
          EmberScan · in development
        </p>
        <h1 className="text-3xl font-bold text-stone-900">
          A walkaround video in, a measured wildfire fix plan out.
        </h1>
        <p className="text-stone-600">
          Built during the Meta Global AI Developer Hackathon, Oct 26 – Nov 4, 2026.
        </p>
      </header>
      <ol className="flex flex-col gap-3">
        {STEPS.map((step, i) => (
          <li key={step.name} className="flex gap-4 rounded-xl border border-stone-200 bg-white p-4">
            <span className="font-mono text-stone-400">{i + 1}</span>
            <div>
              <p className="font-semibold text-stone-900">{step.name}</p>
              <p className="text-stone-600">{step.detail}</p>
            </div>
          </li>
        ))}
      </ol>
      <p className="text-sm text-stone-500">
        EmberScan flags likely wildfire hazards and suggests fixes. It is not an inspection and
        does not certify that any property is safe or compliant.
      </p>
    </main>
  );
}
