import { useEffect, useState } from "react";

import EquityChart from "../components/EquityChart";
import PerformanceChart from "../components/PerformanceChart";
import PerformanceSummary from "../components/PerformanceSummary";

import {
  getSubscriberPerformance,
  getOrders,
  getEquityHistory,
  getAnalytics
} from "../services/api";
import { getSubscriberId } from "../services/auth";


function Dashboard() {


const [performance, setPerformance] = useState(null);
const [analytics, setAnalytics] = useState(null);
const [orders, setOrders] = useState([]);
const [equityHistory, setEquityHistory] = useState([]);



useEffect(() => {


getSubscriberPerformance(getSubscriberId())
.then(setPerformance)
.catch(console.error);


getAnalytics()
.then(setAnalytics)
.catch(console.error);


getOrders()
.then(data => {

setOrders(
data?.orders
? data.orders.slice(0,10)
: []
);

})
.catch(console.error);



getEquityHistory()
.then(data => {

setEquityHistory(
data?.history || []
);

})
.catch(console.error);



}, []);



const latestEquity =
equityHistory.length > 0
?
equityHistory[equityHistory.length - 1]
:
null;



return (

<div>


<h1>
Bethel Trading Technologies
</h1>


<h2>
Investor Dashboard
</h2>



{
analytics &&
<PerformanceSummary
performance={analytics}
/>
}



<div className="dashboard-grid">


<div className="metric-card">

<h4>
Total Trades
</h4>

<p>
{performance?.performance?.total_trades || 0}
</p>

</div>



<div className="metric-card">

<h4>
Win Rate
</h4>

<p>
{performance?.performance?.win_rate_percent || 0}%
</p>

</div>



<div className="metric-card">

<h4>
Equity Snapshots
</h4>

<p>
{equityHistory.length}
</p>

</div>



</div>




<div className="card">

<h3>
Recent Copy Trades
</h3>


<table>

<thead>

<tr>

<th>
Symbol
</th>

<th>
Direction
</th>

<th>
Volume
</th>

<th>
Status
</th>

</tr>

</thead>


<tbody>


{
orders.map((order,index)=>(

<tr key={index}>

<td>{order.symbol}</td>

<td>{order.direction}</td>

<td>{order.volume}</td>

<td>{order.status}</td>

</tr>

))

}


</tbody>


</table>


</div>




{
latestEquity &&

<div className="card">

<h3>
Account Equity
</h3>


<p>
Balance: $
{Number(latestEquity.balance).toLocaleString()}
</p>


<p>
Equity: $
{Number(latestEquity.equity).toLocaleString()}
</p>


</div>

}



<EquityChart
data={equityHistory}
/>


<PerformanceChart
data={equityHistory}
/>



</div>

);


}


export default Dashboard;
