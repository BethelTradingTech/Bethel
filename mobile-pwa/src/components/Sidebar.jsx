import { NavLink } from "react-router-dom";

function Sidebar() {
  return (
    <aside className="sidebar">

      <div className="sidebar-header">

        <h2>BETHEL</h2>

        <p>Trading Technologies</p>

        <small>Investor Portal</small>

      </div>

      <nav>

        <NavLink to="/">Dashboard</NavLink>

        <NavLink to="/portfolio">Portfolio</NavLink>

        <NavLink to="/copy-trading">Copy Trading</NavLink>

        <NavLink to="/analytics">Analytics</NavLink>

        <NavLink to="/subscribers">Subscribers</NavLink>

        <NavLink to="/settings">Settings</NavLink>

      </nav>

    </aside>
  );
}

export default Sidebar;