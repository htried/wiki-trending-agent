import { type ReactElement } from "react";

type PageReason = {
  title: string;
  reason: string;
};

type PageResultsListProps = {
  results: PageReason[];
};

export default function PageResultsList({ results }: PageResultsListProps): ReactElement {
  return (
    <section aria-label="Page results">
      <h2>Page Results</h2>
      <ul>
        {results.map((item) => (
          <li key={item.title}>
            <strong>{item.title}</strong>: {item.reason}
          </li>
        ))}
      </ul>
    </section>
  );
}
