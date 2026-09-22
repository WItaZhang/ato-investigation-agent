"""Transparent demo rules, not a trained fraud or account-takeover detector."""


def decide(event, policy):
    if event.failed_attempts >= policy["review_failure_threshold"]:
        return "review", "Repeated failed logins require review"
    if event.new_device and not event.mfa_passed:
        return "require_mfa", "New device without a completed MFA challenge"
    return None, "No demo policy trigger"
