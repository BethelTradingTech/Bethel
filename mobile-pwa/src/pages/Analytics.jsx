import { useEffect, useState } from "react";

import {
  getAnalytics
} from "../services/api";


function Analytics(){


const [data,setData] = useState(null);



useEffect(()=>{

getAnalytics()
.then(setData)
.catch(console.error);


},[]);



return (

<div>


<h1>
Analytics
</h1>



{
data ? (

<div className="dashboard-grid">


<div className="metric-card">
<h4>Total Return</h4>
<p>{data.total_return_percent || 0}%</p>
</div>


<div className="metric-card">
<h4>Profit Factor</h4>
<p>{data.profit_factor || 0}</p>
</div>


<div className="metric-card">
<h4>Sharpe Ratio</h4>
<p>{data.sharpe_ratio || 0}</p>
</div>


<div className="metric-card">
<h4>Sortino Ratio</h4>
<p>{data.sortino_ratio || 0}</p>
</div>


<div className="metric-card">
<h4>Max Drawdown</h4>
<p>{data.max_drawdown || 0}</p>
</div>


<div className="metric-card">
<h4>Risk Level</h4>
<p>{data.risk_level || "--"}</p>
</div>


<div className="metric-card">
<h4>Consistency Score</h4>
<p>{data.consistency_score || 0}</p>
</div>


<div className="metric-card">
<h4>Grade</h4>
<p>{data.performance_grade || "--"}</p>
</div>


</div>

)

:

<p>
Loading analytics...
</p>

}



</div>

);


}


export default Analytics;