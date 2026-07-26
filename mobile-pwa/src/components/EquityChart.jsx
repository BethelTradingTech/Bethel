import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";


function EquityChart({ data }) {


  const chartData = data
    .slice(-100)
    .map((item, index) => ({
      index: index + 1,
      time: item.timestamp,
      equity: Number(item.equity),
      balance: Number(item.balance)
    }));


  return (

    <div className="card">

      <h3>
        Equity Performance
      </h3>


      <ResponsiveContainer width="100%" height={350}>

        <LineChart
          data={chartData}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 20
          }}
        >


          <CartesianGrid />


          <XAxis
            dataKey="index"
            hide
          />


          <YAxis
            domain={[
              "auto",
              "auto"
            ]}
          />


          <Tooltip
            labelFormatter={(value) =>
              `Point ${value}`
            }
          />



          <Line
            type="monotone"
            dataKey="equity"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 5 }}
          />



          <Line
            type="monotone"
            dataKey="balance"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5 }}
          />


        </LineChart>


      </ResponsiveContainer>


    </div>

  );

}


export default EquityChart;