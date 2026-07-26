function Navbar() {

  return (

    <header className="navbar">

      <div>

        <h3 style={{margin:0}}>
          Bethel Trading Technologies
        </h3>

        <small>
          Investor Portal
        </small>

      </div>

      <div
        style={{
          display:"flex",
          alignItems:"center",
          gap:"8px",
          fontWeight:"bold"
        }}
      >

        <span
          style={{
            width:"10px",
            height:"10px",
            borderRadius:"50%",
            background:"#22c55e",
            display:"inline-block"
          }}
        ></span>

        MT5 Connected

      </div>

    </header>

  );

}

export default Navbar;