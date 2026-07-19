"""
Bethel Trading Technologies
Scheduler Runner
"""


from services.scheduler import EquityScheduler



scheduler = EquityScheduler()


scheduler.start(
    interval_seconds=3600
)