from ..value_objects.timestamp import Timestamp


class PowerData:
    def __init__(self, data_id: str, node_id: str, timestamp: Timestamp):
        self.data_id = data_id
        self.node_id = node_id
        self.timestamp = timestamp
        self.active_power = 0.0
        self.reactive_power = 0.0
        self.voltage = 0.0
        self.current = 0.0
    
    def update_power_values(self, active_power: float, reactive_power: float) -> None:
        pass
    
    def update_voltage_current(self, voltage: float, current: float) -> None:
        pass