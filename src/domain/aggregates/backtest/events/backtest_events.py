class BacktestStartedEvent:
    def __init__(self, backtest_id, strategy_id, start_time, parameters):
        self.backtest_id = backtest_id
        self.strategy_id = strategy_id
        self.start_time = start_time
        self.parameters = parameters
        self.event_type = "BacktestStarted"


class BacktestCompletedEvent:
    def __init__(self, backtest_id, strategy_id, end_time, results):
        self.backtest_id = backtest_id
        self.strategy_id = strategy_id
        self.end_time = end_time
        self.results = results
        self.event_type = "BacktestCompleted"