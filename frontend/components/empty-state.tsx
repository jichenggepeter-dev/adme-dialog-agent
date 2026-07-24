export function EmptyState() {
  return (
    <section className="empty-state" aria-labelledby="empty-heading">
      <div className="empty-plot" aria-hidden="true"><span /><span /><span /><span /></div>
      <div>
        <p className="section-index">02 / Results</p>
        <h2 id="empty-heading">Prediction output will appear here.</h2>
        <p>Start with aspirin or paste a SMILES string to populate the six ADME/ADMET sections.</p>
      </div>
    </section>
  );
}
