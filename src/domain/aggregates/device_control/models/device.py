from ..value_objects.device_type import DeviceType


class Device:
    def __init__(self, device_id: str, device_type: DeviceType, node_id: str):
        self.device_id = device_id
        self.device_type = device_type
        self.node_id = node_id