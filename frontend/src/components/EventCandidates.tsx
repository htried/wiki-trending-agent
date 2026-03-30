import { type ReactElement } from "react";

type EventCandidatesProps = {
  events: string[];
};

export default function EventCandidates({ events }: EventCandidatesProps): ReactElement {
  return (
    <section aria-label="Event candidates">
      <h2>Event Candidates</h2>
      <ul>
        {events.map((event) => (
          <li key={event}>{event}</li>
        ))}
      </ul>
    </section>
  );
}
