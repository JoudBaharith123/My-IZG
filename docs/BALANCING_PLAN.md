# Workload Balancing Approach

## Goal
Redistribute customer assignments across zones so each zone stays within the ±20% tolerance defined in the product specification, using customer count as the primary metric (future extension: revenue, visit time).

## Strategy
1. Compute per-zone statistics from the zoning result.
2. Determine average load and tolerance bounds: `avg = total_customers / zones`, `lower = avg * (1 - tolerance)`, `upper = avg * (1 + tolerance)`.
3. While zones exceed bounds:
   - Identify the most overloaded zone (> upper) and the most underloaded zone (< lower).
   - Choose a customer from the overloaded zone to transfer. Selection heuristic: customer closest (Haversine) to the underloaded zone centroid to minimise disruption.
   - Update assignments, counts, and centroids; record the transfer.
   - Stop after max iterations (e.g., number of customers) to avoid loops.
4. Produce metadata summarising final counts, original vs. balanced counts, and transfer log so planners can review.

## Integration
- Extend `ZoningRequest` with optional `balance` and `balance_tolerance` parameters.
- After strategy-specific assignments are generated, optionally invoke the balancing routine.
- Persist updated assignments and include balancing metadata in response.
- Document in tracker that balancing is applied only when the user requests it.

## Limitations & Future Enhancements
- Current implementation balances on customer count only; hook for other metrics is prepared but requires additional data.
- Zone centroids are derived from customer coordinates; when a zone has zero customers, fall back to depot coordinates.
- Transfers ignore route-level impacts; after balancing, routes should be recomputed.
- Manual review recommended: balancing metadata highlights changes for stakeholders before finalising agent reassignments.
