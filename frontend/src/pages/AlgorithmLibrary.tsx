import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { algorithmsApi } from "../api/endpoints";
import type { AlgorithmInfo } from "../types";
import { LoadingState, ErrorState } from "../components/States";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";

export function AlgorithmLibrary() {
  const [algorithms, setAlgorithms] = useState<AlgorithmInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    algorithmsApi
      .list()
      .then((r) => setAlgorithms(r.data))
      .catch(() => setError("Failed to load algorithm library."));
  }, []);

  async function handleLoad(algorithmId: string) {
    setLoadingId(algorithmId);
    try {
      const resp = await algorithmsApi.load(algorithmId);
      navigate("/circuit-lab", { state: { preloadedCircuit: resp.data.circuit } });
    } catch {
      setError("Failed to load algorithm into the Circuit Lab.");
    } finally {
      setLoadingId(null);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!algorithms) return <LoadingState label="Loading algorithm library" />;

  return (
    <div>
      <PageHeader title="Algorithms" description="Prebuilt circuits, genuinely constructed and executed through the same engine as any user circuit." />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {algorithms.map((algo) => (
          <Card key={algo.id} className="flex flex-col">
            <h2 className="text-sm font-semibold text-[var(--text)]">{algo.name}</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{algo.description}</p>
            <p className="mt-2 text-xs text-[var(--text-secondary)]">
              <span className="font-medium text-[var(--text)]">Intuition — </span>
              {algo.math_intuition}
            </p>
            {algo.expected_distribution && (
              <p className="mt-2 font-mono-tech text-xs text-[var(--text-secondary)]">
                Expected outcome: {JSON.stringify(algo.expected_distribution)}
              </p>
            )}
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleLoad(algo.id)}
              disabled={loadingId === algo.id}
              className="mt-3 self-start"
            >
              {loadingId === algo.id ? "Loading..." : "Load into Circuit Lab"}
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
