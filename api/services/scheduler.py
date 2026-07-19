from apscheduler.schedulers.background import BackgroundScheduler

from api.services.mt5_snapshot import save_snapshot



scheduler = BackgroundScheduler()



def start_scheduler():


    scheduler.add_job(

        save_snapshot,

        "interval",

        minutes=1

    )


    scheduler.start()