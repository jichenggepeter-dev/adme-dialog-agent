export function ValidationMessage({ message }: { message: string }) {
  return <p id="prediction-error" className="validation-message" role="alert">{message}</p>;
}
