import { useEffect, useState } from "react";

import {
getSubscribers,
getCopyOrders,
getMT5Account,
getMT5Positions
} from "../services/api";


function CopyTrading(){


const [subscribers,setSubscribers] = useState([]);
const [orders,setOrders] = useState([]);
const [account,setAccount] = useState(null);
const [positions,setPositions] = useState([]);



useEffect(()=>{


getSubscribers()
.then(setSubscribers)
.catch(console.error);



getCopyOrders()
.then(data=>{

setOrders(
data?.orders || data || []
);

})
.catch(console.error);



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



},[]);



return (

<div>


<h1>
Copy Trading
</h1>


<div className="dashboard-grid">


<div className="metric-card">

<h4>
MT5 Status
</h4>

<p>
Connected
</p>

</div>



<div className="metric-card">

<h4>
Subscribers
</h4>

<p>
{subscribers.length}
</p>

</div>



<div className="metric-card">

<h4>
Open Positions
</h4>

<p>
{positions.length}
</p>

</div>


</div>





<div className="card">

<h3>
Master Account
</h3>


{
account ?

<pre>
{JSON.stringify(account,null,2)}
</pre>

:

<p>
Loading account...
</p>

}


</div>





<div className="card">

<h3>
Subscribers
</h3>


<table>

<thead>

<tr>
<th>Name</th>
<th>Email</th>
<th>Status</th>
</tr>

</thead>


<tbody>


{
subscribers.map((sub)=>(

<tr key={sub.id}>

<td>{sub.name}</td>

<td>{sub.email}</td>

<td>{sub.status}</td>

</tr>


))
}


</tbody>


</table>


</div>





<div className="card">

<h3>
Copy Execution Orders
</h3>


<table>

<thead>

<tr>

<th>Symbol</th>
<th>Direction</th>
<th>Volume</th>
<th>Status</th>

</tr>

</thead>


<tbody>


{
orders.slice(0,20).map((order,index)=>(

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



</div>

);


}


export default CopyTrading;