import { type ReactElement } from "react";

type HourSelectorProps = {
  hours: string[];
  selectedHour: string;
  onSelect: (hour: string) => void;
};

export default function HourSelector({
  hours,
  selectedHour,
  onSelect,
}: HourSelectorProps): ReactElement {
  return (
    <label>
      Select hour
      <select
        aria-label="Select hour"
        value={selectedHour}
        onChange={(event) => onSelect(event.target.value)}
      >
        <option value="">Choose an hour</option>
        {hours.map((hour) => (
          <option key={hour} value={hour}>
            {hour}
          </option>
        ))}
      </select>
    </label>
  );
}
