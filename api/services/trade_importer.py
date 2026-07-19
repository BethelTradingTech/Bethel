"""
Bethel Trading Technologies
MT5 Trade Matching Engine
"""


from datetime import datetime


from api.database import SessionLocal

from api.models import Trade


from mt5_connector.history import MT5History





def import_mt5_history(account_id=1):


    db = SessionLocal()


    try:


        history = MT5History().get_history()



        if history.get("status") != "success":


            return history





        deals = history["history"]





        positions = {}





        # Group deals by MT5 position_id

        for deal in deals:


            position_id = deal.get("position_id")



            if not position_id:


                continue



            if position_id not in positions:


                positions[position_id] = []



            positions[position_id].append(deal)







        imported = 0





        for position_id, trade_deals in positions.items():



            exists = db.query(Trade).filter(


                Trade.ticket == str(position_id)


            ).first()



            if exists:


                continue





            entry_deals = [

                d for d in trade_deals

                if d.get("entry") == 0

            ]



            exit_deals = [

                d for d in trade_deals

                if d.get("entry") == 1

            ]





            if len(entry_deals) == 0 or len(exit_deals) == 0:


                continue






            entry = entry_deals[0]


            exit = exit_deals[-1]





            profit = sum(

                float(d.get("profit",0))

                for d in trade_deals

            )





            trade = Trade(



                account_id=account_id,


                ticket=str(position_id),



                symbol=entry["symbol"],



                direction=str(entry["type"]),



                lot_size=float(entry["volume"]),



                entry_price=float(entry["price"]),



                exit_price=float(exit["price"]),



                profit=profit,



                status="CLOSED",



                opened_at=datetime.fromisoformat(

                    entry["time"]

                ),



                closed_at=datetime.fromisoformat(

                    exit["time"]

                )


            )



            db.add(trade)


            imported += 1






        db.commit()





        return {


            "status":"success",


            "imported":imported,


            "positions_found":len(positions)


        }





    except Exception as e:



        db.rollback()



        return {


            "status":"failed",


            "message":str(e)


        }





    finally:


        db.close()