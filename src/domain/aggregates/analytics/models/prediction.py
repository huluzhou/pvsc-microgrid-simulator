from typing import Dict

from ..value_objects.timestamp import Timestamp


class Prediction:
    def __init__(self, prediction_id: str, target_entity_id: str, prediction_type: str, forecast_timestamp: Timestamp):
        self.prediction_id = prediction_id
        self.target_entity_id = target_entity_id
        self.prediction_type = prediction_type
        self.forecast_timestamp = forecast_timestamp
        self.predicted_value = 0.0
        self.confidence_level = 0.0
        self.status = "pending"
    
    def update_predicted_value(self, value: float) -> None:
        pass
    
    def set_confidence_level(self, level: float) -> None:
        pass
    
    def mark_as_complete(self) -> None:
        pass
    
    def get_prediction_summary(self) -> Dict:
        pass