export function LoadingState({ message = "Running the computational prediction…" }: { message?: string }) {
  return (
    <section className="loading-state" role="status" aria-live="polite">
      <p>{message}</p>
      <div className="skeleton-lines" aria-hidden="true"><span /><span /><span /></div>
    </section>
  );
}
