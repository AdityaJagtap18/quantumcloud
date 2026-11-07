import { useEffect, useState } from "react";
import { backendsApi } from "../api/endpoints";
import type { BackendInfo } from "../types";
import { LoadingState, ErrorState } from "../components/States";
import { PageHeader } from "../components/ui/PageHeader";
import { Table, THead, Th, Td, Tr } from "../components/ui/Table";

export function Backends() {
  const [backends, setBackends] = useState<BackendInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    backendsApi
      .list()
      .then((r) => setBackends(r.data))
      .catch(() => setError("Failed to load backends."));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!backends) return <LoadingState label="Loading backends" />;

  return (
    <div>
      <PageHeader
        title="Backends"
        description="Simulation backends available for job execution. None of these are physical quantum hardware."
      />
      <Table>
        <THead>
          <Th>Name</Th>
          <Th>Type</Th>
          <Th>Description</Th>
          <Th>Requires measurement</Th>
        </THead>
        <tbody>
          {backends.map((b) => (
            <Tr key={b.id}>
              <Td mono>{b.name}</Td>
              <Td mono>{b.backend_type}</Td>
              <Td>{b.description}</Td>
              <Td>{b.requires_measurements ? "Yes" : "No"}</Td>
            </Tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
