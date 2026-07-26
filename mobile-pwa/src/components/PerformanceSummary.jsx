function PerformanceSummary({ performance }) {

  if (!performance) {
    return null;
  }


  return (

    <div className="dashboard-grid">


      <div className="metric-card">
        <h4>Starting Capital</h4>
        <p>
          $
          {Number(performance.starting_capital).toLocaleString()}
        </p>
      </div>



      <div className="metric-card">
        <h4>Current Equity</h4>
        <p>
          $
          {Number(performance.current_equity).toLocaleString()}
        </p>
      </div>



      <div className="metric-card">
        <h4>Total Return</h4>
        <p>
          {performance.total_return_percent}%
        </p>
      </div>



      <div className="metric-card">
        <h4>Profit Factor</h4>
        <p>
          {performance.profit_factor}
        </p>
      </div>



      <div className="metric-card">
        <h4>Sharpe Ratio</h4>
        <p>
          {performance.sharpe_ratio}
        </p>
      </div>



      <div className="metric-card">
        <h4>Sortino Ratio</h4>
        <p>
          {performance.sortino_ratio}
        </p>
      </div>



      <div className="metric-card">

        <h4>
          Max Drawdown
        </h4>


        <p>
          $
          {Number(
            performance.maximum_drawdown_amount || 0
          ).toLocaleString()}
        </p>


        <small>
          (
          {Number(
            performance.maximum_drawdown_percent || 0
          ).toFixed(2)}
          %)
        </small>

      </div>



      <div className="metric-card">
        <h4>Consistency Score</h4>
        <p>
          {performance.consistency_score}
        </p>
      </div>



      <div className="metric-card">
        <h4>Risk Level</h4>
        <p>
          {performance.risk_level}
        </p>
      </div>



      <div className="metric-card">
        <h4>Performance Grade</h4>
        <p>
          {performance.performance_grade}
        </p>
      </div>


    </div>

  );

}


export default PerformanceSummary;