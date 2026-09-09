## T2 handoff

Queue rows are append-only; dequeue marks a row sent rather than deleting it,
so a retried sync after a crash can't double-count. Nothing else deviated
from the plan.
