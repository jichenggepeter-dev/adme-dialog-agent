from pathlib import Path


sample = Path("examples/batch/sample_mixed.csv").resolve()
print("ADME batch demo (non-destructive)")
print("1. Start mock development mode in this directory:")
print("   ADME_MOCK_MODE=true make dev")
print("2. Open http://localhost:3000/batch")
print(f"3. Upload: {sample}")
print("4. Accept the suggested column mapping, review validation, and run the job.")
print("5. Results are stored under data/jobs/ and can be removed when no longer needed.")
