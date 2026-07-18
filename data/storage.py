"""
Bethel Trading Technologies
Market Data Storage Engine
"""

from sqlalchemy import create_engine
from sqlalchemy import text
import pandas as pd


DATABASE = "sqlite:///bethel_trading.db"


engine = create_engine(DATABASE)


def save_market_data(dataframe, table_name="market_prices"):

    dataframe.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False
    )

    print(
        f"Saved {len(dataframe)} records to {table_name}"
    )



def load_market_data(table_name="market_prices"):

    query = text(
        f"SELECT * FROM {table_name}"
    )

    with engine.connect() as connection:

        data = pd.read_sql(
            query,
            connection
        )

    return data