class AnalysisStartedEvent:
    def __init__(self, analysis_id, analysis_type, start_time, parameters):
        self.analysis_id = analysis_id
        self.analysis_type = analysis_type
        self.start_time = start_time
        self.parameters = parameters
        self.event_type = "AnalysisStarted"


class AnalysisCompletedEvent:
    def __init__(self, analysis_id, analysis_type, end_time, results):
        self.analysis_id = analysis_id
        self.analysis_type = analysis_type
        self.end_time = end_time
        self.results = results
        self.event_type = "AnalysisCompleted"