class DeviceRegisteredEvent:
    def __init__(self, device_id, device_info, registration_time):
        self.device_id = device_id
        self.device_info = device_info
        self.registration_time = registration_time
        self.event_type = "DeviceRegistered"


class DeviceStatusChangedEvent:
    def __init__(self, device_id, new_status, status_timestamp):
        self.device_id = device_id
        self.new_status = new_status
        self.status_timestamp = status_timestamp
        self.event_type = "DeviceStatusChanged"