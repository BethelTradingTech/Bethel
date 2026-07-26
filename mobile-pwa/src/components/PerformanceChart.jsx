import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";


function PerformanceChart({ data }) {


  const chartData = data.slice(-180).map((item) => ({

  date: item.timestamp ? item.timestamp.substring(0, 10) : "",
    equity: item.equity

  }));


  return (

    <div className="card">

      <h3>
        Portfolio Growth
      </h3>


      <ResponsiveContainer
        width="100%"
        height={350}
      >

        <LineChart data={chartData}>


          <CartesianGrid />


          <XAxis
            dataKey="date"
          />


          <YAxis />


          <Tooltip />


          <Line
            type="monotone"
            dataKey="equity"
            strokeWidth={2}
            dot={false}
          />


        </LineChart>


      </ResponsiveContainer>


    </div>

  );

}


export default PerformanceChart;