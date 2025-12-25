from domain.aggregates.topology.specifications import (
    ValidTopologySpecification, DeviceExistsSpecification, 
    ConnectionValidSpecification, CompleteTopologySpecification
)
from domain.aggregates.topology.exceptions import TopologyValidationException
from domain.aggregates.topology.events import TopologyValidatedEvent, TopologyValidationFailedEvent
from domain.common.events.event_bus import EventBus
from typing import Dict, List, Any

class TopologyValidationService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
    
    def validate(self, topology) -> Dict[str, Any]:
        validation_results = {
            "is_valid": True,
            "errors": [],
            "checks": {
                "valid_topology": False,
                "complete_topology": False,
                "all_devices_connected": False
            }
        }
        
        # 检查拓扑是否有效
        valid_topology_spec = ValidTopologySpecification()
        validation_results["checks"]["valid_topology"] = valid_topology_spec.is_satisfied_by(topology)
        if not validation_results["checks"]["valid_topology"]:
            validation_results["errors"].append("Topology is invalid: missing devices or invalid connections")
            validation_results["is_valid"] = False
        
        # 检查拓扑是否完整
        complete_topology_spec = CompleteTopologySpecification()
        validation_results["checks"]["complete_topology"] = complete_topology_spec.is_satisfied_by(topology)
        
        # 检查所有连接是否有效
        for connection in topology.connections:
            connection_valid_spec = ConnectionValidSpecification()
            if not connection_valid_spec.is_satisfied_by(connection):
                validation_results["errors"].append(f"Invalid connection {connection.id}: source and target devices are the same")
                validation_results["is_valid"] = False
        
        # 发布验证事件
        if validation_results["is_valid"]:
            self._event_bus.publish(TopologyValidatedEvent(
                topology_id=str(topology.id),
                is_valid=True,
                validation_results=validation_results
            ))
        else:
            self._event_bus.publish(TopologyValidationFailedEvent(
                topology_id=str(topology.id),
                errors=validation_results["errors"]
            ))
            raise TopologyValidationException(f"Topology validation failed: {validation_results['errors']}")
        
        return validation_results
    
    def validate_device_exists(self, topology, device_id: str) -> bool:
        spec = DeviceExistsSpecification(device_id)
        return spec.is_satisfied_by(topology)
    
    def validate_connection(self, connection: Any) -> bool:
        spec = ConnectionValidSpecification()
        return spec.is_satisfied_by(connection)
