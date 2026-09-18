<!-- coldsession-scout template: inventory version: 1 params: symbol -->
Task: list every place in scope that references `{{symbol}}`.

- `searched` is required. List each exact pattern with the paths it covered. The runtime reruns every pattern, and any match that no evidence item covers rejects the whole report.
- Choose patterns that match only the references you cite. Narrow the paths rather than exceed the evidence budget.
- If there are no references, use status `not_found` and still fill `searched`.
