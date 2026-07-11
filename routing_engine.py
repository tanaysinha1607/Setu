def route_credit_assessment(data: dict) -> tuple[str, str]:
    """
    Routes a borrower credit assessment record based on anomaly flags and confidence scores.
    
    Rules (Anomaly-First):
    1. If anomaly_flags is non-empty -> "escalate" (regardless of confidence)
    2. Else if confidence_score < 0.7 -> "escalate"
    3. Else -> "local"
    
    Returns:
        tuple[str, str]: (route, reason) where route is "local" or "escalate"
    """
    anomalies = data.get("anomaly_flags", [])
    confidence = data.get("confidence_score", 0.0)
    
    # 1. Anomaly-first check (even high-confidence anomalies must escalate)
    if anomalies:
        anomalies_str = ", ".join(anomalies)
        return "escalate", f"Escalated: anomaly detected ({anomalies_str})"
        
    # 2. Confidence threshold check
    if confidence < 0.7:
        return "escalate", f"Escalated: confidence {confidence} below threshold"
        
    # 3. Safe to handle locally
    return "local", f"Handled locally: confidence {confidence}, no anomalies"

def run_tests():
    print("Running Routing Engine Unit Tests...")
    
    # Test 1: High-confidence, clean (Expect: local)
    test_1 = {
        "daily_revenue_estimate": 4000.0,
        "revenue_variance": "low",
        "payment_consistency": "high",
        "confidence_score": 0.95,
        "anomaly_flags": []
    }
    route_1, reason_1 = route_credit_assessment(test_1)
    assert route_1 == "local", f"Test 1 failed: expected local, got {route_1}"
    print(f"  [PASS] Test 1 (High-Confidence Clean) -> Route: {route_1} | Reason: {reason_1}")

    # Test 2: Low-confidence, no anomaly (Expect: escalate)
    test_2 = {
        "daily_revenue_estimate": 3500.0,
        "revenue_variance": "medium",
        "payment_consistency": "medium",
        "confidence_score": 0.65,
        "anomaly_flags": []
    }
    route_2, reason_2 = route_credit_assessment(test_2)
    assert route_2 == "escalate", f"Test 2 failed: expected escalate, got {route_2}"
    print(f"  [PASS] Test 2 (Low-Confidence Clean) -> Route: {route_2} | Reason: {reason_2}")

    # Test 3: High-confidence, with anomaly (Expect: escalate)
    test_3 = {
        "daily_revenue_estimate": 22000.0,
        "revenue_variance": "high",
        "payment_consistency": "low",
        "confidence_score": 0.92,
        "anomaly_flags": ["revenue_spike"]
    }
    route_3, reason_3 = route_credit_assessment(test_3)
    assert route_3 == "escalate", f"Test 3 failed: expected escalate, got {route_3}"
    print(f"  [PASS] Test 3 (High-Confidence Anomaly) -> Route: {route_3} | Reason: {reason_3}")

    print("\nAll unit tests passed successfully!")

if __name__ == "__main__":
    run_tests()
