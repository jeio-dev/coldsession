<!-- coldsession-scout template: trace version: 1 params: from, to -->
Task: trace how control or data flows from `{{from}}` to `{{to}}` in this repository.

- Put the chain in `steps`, in order. Each step is one line of text plus the IDs of the evidence that shows it.
- A step you cannot show with evidence ends the chain: make it the last step, give it no evidence, and use status `partial`.
- Status `answered` requires every step to cite evidence.
- If no path exists, use status `not_found` and list every pattern you searched, with its paths, in `searched`.
