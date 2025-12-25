class PowerAnomalyDetectedEvent:
    def __init__(self, device_id, timestamp, anomaly_type, severity):
        self.device_id = device_id
        self.timestamp = timestamp
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.event_type = "PowerAnomalyDetected"


class PowerOptimizationEvent:
    def __init__(self, device_id, optimization_parameters, expected_impact):
        self.device_id = device_id
        self.optimization_parameters = optimization_parameters
        self.expected_impact = expected_impact
        self.event_type = "PowerOptimization"