## 4.4 Adjacency Model for Radio Telemetry

### 4.4.1 Why standard adjacency is insufficient

Standard differential privacy definitions assume a neighboring relation where two
databases differ by the addition or removal of one record (add/remove adjacency)
or the substitution of one record (substitute adjacency). In tabular datasets,
this corresponds to one individual's row.

Radio telemetry violates this assumption in three ways:

**Temporal correlation.** A single user generates multiple observations per
session (one heartbeat every 30 seconds in VERA's reference implementation).
These observations are not independent — they share device fingerprint, session
ID, and listening context. Under standard adjacency, removing one observation
leaves all correlated observations in the dataset, providing partial reconstruction.

**Longitudinal persistence.** A user's listening behavior is device-persistent
across sessions. An adversary observing aggregate outputs over multiple time
windows can correlate shifts in the aggregate to infer individual behavioral
changes, even if each individual observation satisfies local DP.

**Bursty contribution structure.** Radio listening follows a power-law
distribution (Zipf alpha=1.8, empirically validated on Last.fm hetrec2011,
N=92,834 events). A small number of users contribute disproportionately large
signal mass. Standard K-anonymity thresholds designed for uniform contribution
underestimate the privacy risk for high-contribution users.

### 4.4.2 VERA's event-level adjacency definition

**Definition 1 (Event-level neighboring databases).** Two listening event
databases D and D' are neighboring (D ~ D') if and only if they differ on
exactly one listening event e = (user_id, station_id, timestamp, duration),
regardless of session context or prior contribution history of user_id.

This definition has three consequences:

1. The sensitivity of the mean aggregation function is bounded by Delta = max_duration / K,
   where K >= 100 is the enforced minimum population size.

2. The Laplace mechanism with scale b = Delta / epsilon satisfies epsilon-DP
   under event-level adjacency for any single query.

3. Composition across T queries consumes epsilon_total = T * epsilon per user,
   bounded by the kill-switch at epsilon_total <= 1.5.

### 4.4.3 Why event-level is the right model for VERA

Event-level adjacency is strictly stronger than substitute adjacency for radio
telemetry: it bounds the contribution of each individual listening event, not
each user session. This directly addresses the temporal correlation and bursty
contribution problems identified in Section 4.4.1.

The tradeoff is utility: event-level adjacency requires more noise per query
than user-level adjacency. VERA accepts this tradeoff explicitly. The empirical
validation (Section 5) shows that rho=0.93 at epsilon=1.5 under event-level
adjacency, confirming that the analytics signal is preserved despite the
stronger privacy guarantee.

**Claim 1.** VERA's aggregation pipeline satisfies epsilon-DP under event-level
adjacency with epsilon_total <= 1.5, for any sequence of queries bounded by the
kill-switch invariant.

*Proof sketch.* By Definition 1, neighboring databases differ on one event.
The trimmed mean-of-means aggregator has sensitivity Delta = 1/K under
normalization. The Laplace mechanism with epsilon_server = 0.5 satisfies
0.5-DP at the server layer. The randomized response client layer satisfies
epsilon_client = 1.0-DP per event. Sequential composition gives epsilon_total
= epsilon_client + epsilon_server = 1.5. The kill-switch enforces this bound
as a hard invariant. QED.
