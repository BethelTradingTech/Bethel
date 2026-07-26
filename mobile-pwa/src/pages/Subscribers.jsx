import { useEffect, useState } from "react";

import {
  getSubscribers
} from "../services/api";


function Subscribers(){


const [subscribers,setSubscribers] = useState([]);


useEffect(()=>{


getSubscribers()
.then(setSubscribers)
.catch(console.error);


},[]);



return (

<div>


<h1>
Subscribers
</h1>



<div className="dashboard-grid">


<div className="metric-card">

<h4>
Total Subscribers
</h4>

<p>
{subscribers.length}
</p>

</div>


<div className="metric-card">

<h4>
Active Subscribers
</h4>

<p>
{
subscribers.filter(
(item)=>item.status==="ACTIVE"
).length
}
</p>

</div>


</div>





<div className="card">


<h3>
Subscriber List
</h3>


<table>


<thead>

<tr>

<th>Name</th>
<th>Email</th>
<th>MT5 Account</th>
<th>Status</th>

</tr>

</thead>


<tbody>


{
subscribers.map((subscriber)=>(

<tr key={subscriber.id}>

<td>
{subscriber.name}
</td>


<td>
{subscriber.email}
</td>


<td>
{subscriber.mt5_account || "--"}
</td>


<td>
{subscriber.status}
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


export default Subscribers;