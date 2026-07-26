import { useEffect, useState } from "react";

import {
  getMT5Account,
  getMT5Positions,
  getAnalytics
} from "../services/api";


function Portfolio(){

const [account,setAccount] = useState(null);
const [positions,setPositions] = useState([]);
const [analytics,setAnalytics] = useState(null);


useEffect(()=>{


getMT5Account()
.then(setAccount)
.catch(console.error);


getMT5Positions()
.then(data=>{

setPositions(
data?.positions || data || []
);

})
.catch(console.error);


getAnalytics()
.then(setAnalytics)
.catch(console.error);


},[]);



return (

<div>


<h1>
Portfolio
</h1>


<div className="dashboard-grid">


<div className="metric-card">

<h4>
Equity
</h4>

<p>
{account?.equity || "--"}
</p>

</div>



<div className="metric-card">

<h4>
Balance
</h4>

<p>
{account?.balance || "--"}
</p>

</div>



<div className="metric-card">

<h4>
Return
</h4>

<p>
{analytics?.total_return_percent || 0}%
</p>

</div>



<div className="metric-card">

<h4>
Risk
</h4>

<p>
{analytics?.risk_level || "--"}
</p>

</div>


</div>





<div className="card">

<h3>
Current Holdings
</h3>


<table>

<thead>

<tr>
<th>Symbol</th>
<th>Direction</th>
<th>Volume</th>
<th>Profit</th>
</tr>

</thead>


<tbody>


{
positions.map((position,index)=>(

<tr key={index}>

<td>
{position.symbol}
</td>

<td>
{position.type || position.direction}
</td>

<td>
{position.volume}
</td>

<td>
{position.profit}
</td>


</tr>

))
}


</tbody>


</table>


</div>


</div>

);


}


export default Portfolio;