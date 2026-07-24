from apscheduler.schedulers.background import BackgroundScheduler

from api.services.mt5_snapshot import save_snapshot

from services.master_trade_listener import MasterTradeListener


scheduler = BackgroundScheduler()


listener = MasterTradeListener()



def start_scheduler():


    scheduler.add_job(

        save_snapshot,

        "interval",

        minutes=1

    )


    scheduler.add_job(

        listener.scan,

        "interval",

        seconds=5

    )


    scheduler.start()