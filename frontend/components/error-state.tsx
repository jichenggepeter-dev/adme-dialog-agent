interface ErrorStateProps { message: string; actionLabel?: string; onAction?: () => void }

export function ErrorState({ message, actionLabel, onAction }: ErrorStateProps) {
  return (
    <section className="error-state" role="alert">
      <p className="section-index">Request did not complete</p>
      <h2>Review the input or service status.</h2>
      <p>{message}</p>
      {actionLabel && onAction ? <button type="button" className="secondary-button" onClick={onAction}>{actionLabel}</button> : null}
    </section>
  );
}
