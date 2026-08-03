//! Retry logic with exponential backoff and jitter.

use std::time::Duration;
use tracing::warn;

/// Retry policy for oracle transactions.
#[derive(Debug, Clone)]
pub struct RetryPolicy {
    /// Maximum number of retry attempts.
    pub max_retries: u32,
    /// Base delay between retries (milliseconds).
    pub base_delay_ms: u64,
    /// Maximum delay cap (milliseconds).
    pub max_delay_ms: u64,
}

impl RetryPolicy {
    pub fn new(max_retries: u32, base_delay_ms: u64) -> Self {
        Self {
            max_retries,
            base_delay_ms,
            max_delay_ms: 60_000, // 60 seconds cap
        }
    }

    /// Calculate delay for the given attempt (0-indexed) with exponential backoff + jitter.
    pub fn delay_for_attempt(&self, attempt: u32) -> Duration {
        let exponential = self.base_delay_ms * 2u64.saturating_pow(attempt);
        let capped = exponential.min(self.max_delay_ms);
        // Add 0-25% jitter to avoid thundering herd
        let jitter = capped / 4;
        let jittered = capped + (rand_jitter(jitter));
        Duration::from_millis(jittered)
    }

    /// Execute an async closure with retries.
    ///
    /// Calls `f` up to `max_retries + 1` times. If `f` returns `Err` and
    /// `should_retry` returns true for the error, waits and retries.
    pub async fn execute<F, Fut, T, E, R>(
        &self,
        mut f: F,
        should_retry: R,
        label: &str,
    ) -> Result<T, E>
    where
        F: FnMut() -> Fut,
        Fut: std::future::Future<Output = Result<T, E>>,
        R: Fn(&E) -> bool,
        E: std::fmt::Display,
    {
        let total_attempts = self.max_retries + 1;

        for attempt in 0..total_attempts {
            match f().await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    if attempt == total_attempts - 1 {
                        // Last attempt — give up
                        warn!(
                            label = %label,
                            attempt = attempt + 1,
                            max = total_attempts,
                            error = %e,
                            "All retry attempts exhausted"
                        );
                        return Err(e);
                    }

                    if !should_retry(&e) {
                        warn!(
                            label = %label,
                            attempt = attempt + 1,
                            error = %e,
                            "Error is not retryable — giving up"
                        );
                        return Err(e);
                    }

                    let delay = self.delay_for_attempt(attempt);
                    warn!(
                        label = %label,
                        attempt = attempt + 1,
                        max = total_attempts,
                        error = %e,
                        delay_ms = delay.as_millis() as u64,
                        "Attempt failed — retrying after delay"
                    );
                    tokio::time::sleep(delay).await;
                }
            }
        }

        unreachable!()
    }
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self::new(3, 2000)
    }
}

/// Simple deterministic jitter — not cryptographically secure, fine for backoff.
fn rand_jitter(max: u64) -> u64 {
    if max == 0 {
        return 0;
    }
    // Use nanosecond timestamp as a cheap pseudo-random source
    let ns = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .subsec_nanos() as u64;
    ns % max
}

/// Determine if an ethers error is retryable (network/nonce issues).
pub fn is_retryable_error(e: &ethers::providers::ProviderError) -> bool {
    let msg = e.to_string();
    // Retryable conditions:
    // - Nonce too low (another tx may have been mined)
    // - Network timeout / connection reset
    // - Rate limited by RPC provider
    // - Transaction underpriced (can retry with higher gas)
    msg.contains("nonce too low")
        || msg.contains("nonce is too low")
        || msg.contains("NETWORK_ERROR")
        || msg.contains("timeout")
        || msg.contains("connection")
        || msg.contains("SERVER_ERROR")
        || msg.contains("rate limit")
        || msg.contains("too many requests")
        || msg.contains("ECONNRESET")
        || msg.contains("underpriced")
        || msg.contains("replacement transaction underpriced")
}

/// Determine if a pending transaction error is retryable.
pub fn is_retryable_pending_error(e: &ethers::providers::PendingTransactionError) -> bool {
    let msg = e.to_string();
    msg.contains("timeout") || msg.contains("dropped") || msg.contains("replaced")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_delay_exponential_backoff() {
        let policy = RetryPolicy::new(3, 1000);

        // Attempt 0: ~1000ms + jitter
        let d0 = policy.delay_for_attempt(0);
        assert!(d0.as_millis() >= 1000 && d0.as_millis() < 1500);

        // Attempt 1: ~2000ms + jitter
        let d1 = policy.delay_for_attempt(1);
        assert!(d1.as_millis() >= 2000 && d1.as_millis() < 3000);

        // Attempt 2: ~4000ms + jitter
        let d2 = policy.delay_for_attempt(2);
        assert!(d2.as_millis() >= 4000 && d2.as_millis() < 6000);
    }

    #[test]
    fn test_delay_cap() {
        let policy = RetryPolicy {
            max_retries: 10,
            base_delay_ms: 1000,
            max_delay_ms: 5000,
        };

        // Attempt 10 would be 1024000ms without cap — should be capped to ~5000ms
        let d = policy.delay_for_attempt(10);
        assert!(d.as_millis() < 7000); // 5000 + 25% jitter max
    }
}
