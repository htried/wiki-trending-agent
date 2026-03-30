import { type ReactElement } from "react";

type RunControlsProps = {
  disabled: boolean;
  topKPages: string;
  onTopKPagesChange: (value: string) => void;
  onRun: () => void;
};

export default function RunControls({
  disabled,
  topKPages,
  onTopKPagesChange,
  onRun,
}: RunControlsProps): ReactElement {
  return (
    <div>
      <label>
        Top k pages
        <input
          aria-label="Top k pages"
          type="number"
          min={1}
          value={topKPages}
          onChange={(event) => onTopKPagesChange(event.target.value)}
          placeholder="All"
        />
      </label>
      <button type="button" onClick={onRun} disabled={disabled}>
        Run analysis
      </button>
    </div>
  );
}
