def __getattr__(name):
    if name == "TopologyValidationService":
        from .topology_validation_service import TopologyValidationService
        return TopologyValidationService
    if name == "TopologyConnectivityService":
        from .topology_connectivity_service import TopologyConnectivityService
        return TopologyConnectivityService
    if name == "TopologyOptimizationService":
        from .topology_optimization_service import TopologyOptimizationService
        return TopologyOptimizationService
    raise AttributeError(name)
