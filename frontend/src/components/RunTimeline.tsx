import { type ReactElement } from "react";

type RunTimelineProps = {
  events: string[];
};

export default function RunTimeline({ events }: RunTimelineProps): ReactElement {
  return (
    <section aria-label="Run timeline">
      <h2>Timeline</h2>
      <ul>
        {events.map((event) => (
          <li key={event}>{event}</li>
        ))}
      </ul>
    </section>
  );
}
