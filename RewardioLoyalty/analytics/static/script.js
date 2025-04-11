let pointsChart, activityChart;

function fetchData() {
    const shopId = document.getElementById('shop_id').value;
    const token = document.getElementById('token').value;
    const headers = { 'Authorization': `Bearer ${token}` }; 
    const baseUrl = 'http://127.0.0.1:8000/analytics/';

    fetch(`${baseUrl}analytics/${shopId}/`, { headers })
        .then(response => response.ok ? response.json() : Promise.reject(response.statusText))
        .then(data => displayAnalytics(data))
        .catch(error => console.error('Analytics Error:', error));

    fetch(`${baseUrl}dashboard/${shopId}/`, { headers })
        .then(response => response.ok ? response.json() : Promise.reject(response.statusText))
        .then(data => displayDashboard(data))
        .catch(error => console.error('Dashboard Error:', error));
}

function displayAnalytics(data) {
    document.getElementById('points-analytics').innerHTML = `
        <h5 class="card-title">Points Analytics</h5>
        <table class="table table-sm">
            <tr><th>Issued</th><td>${data.points_based_analytics.total_points_issued}</td></tr>
            <tr><th>Redeemed</th><td>${data.points_based_analytics.total_points_redeemed}</td></tr>
            <tr><th>Rate</th><td>${data.points_based_analytics.redemption_rate}%</td></tr>
        </table>
    `;
    document.getElementById('expiration-rate').innerHTML = `
        <h5 class="card-title">Expiration Rate</h5>
        <table class="table table-sm">
            <tr><th>Expired</th><td>${data.points_expiration_rate.expired_points}</td></tr>
            <tr><th>Rate</th><td>${data.points_expiration_rate.expiration_rate}%</td></tr>
        </table>
    `;
    document.getElementById('retention-rate').innerHTML = `
        <h5 class="card-title">Retention Rate</h5>
        <table class="table table-sm">
            <tr><th>Total</th><td>${data.customer_retention_rate.total_customers}</td></tr>
            <tr><th>Returning</th><td>${data.customer_retention_rate.returning_customers}</td></tr>
            <tr><th>Rate</th><td>${data.customer_retention_rate.retention_rate}%</td></tr>
        </table>
    `;
    document.getElementById('top-customers').innerHTML = `
        <h5 class="card-title">Top Customers</h5>
        <table class="table table-sm">
            <thead><tr><th>ID</th><th>Points</th></tr></thead>
            <tbody>${data.top_customers_by_points.map(c => `<tr><td>${c.customer_id}</td><td>${c.total_points}</td></tr>`).join('')}</tbody>
        </table>
    `;
    document.getElementById('customer-segment').innerHTML = `
        <h5 class="card-title">Customer Segments</h5>
        <table class="table table-sm">
            <tr><th>Active</th><td>${data.customer_segment.active_customers}</td></tr>
            <tr><th>Inactive</th><td>${data.customer_segment.inactive_customers}</td></tr>
            <tr><th>High-Value</th><td>${data.customer_segment.high_value_customers}</td></tr>
        </table>
    `;
    document.getElementById('purchase-rules').innerHTML = `
        <h5 class="card-title">Purchase Rules</h5>
        <table class="table table-sm">
            <thead><tr><th>ID</th><th>Points</th><th>Min</th><th>Max</th><th>Usage</th></tr></thead>
            <tbody>${data.purchase_rule_utilization.map(r => `<tr><td>${r.rule_id}</td><td>${r.points}</td><td>${r.min_amount}</td><td>${r.max_amount}</td><td>${r.usage_count}</td></tr>`).join('')}</tbody>
        </table>
    `;
    document.getElementById('churn-risk').innerHTML = `
        <h5 class="card-title">Churn Risk</h5>
        <table class="table table-sm">
            <tr><th>At-Risk</th><td>${data.predictive_analytics.churn_risk.at_risk_customers}</td></tr>
            <tr><th>Risk %</th><td>${data.predictive_analytics.churn_risk.churn_risk_percentage}%</td></tr>
        </table>
    `;

    // Bar Charts
    if (pointsChart) pointsChart.destroy();
    if (activityChart) activityChart.destroy();

    const pointsCtx = document.getElementById('points-over-time-chart').getContext('2d');
    pointsChart = new Chart(pointsCtx, {
        type: 'bar',
        data: {
            labels: data.time_based_analytics.points_over_time.wallet_points.map(p => p.period),
            datasets: [
                { label: 'Points Issued', data: data.time_based_analytics.points_over_time.wallet_points.map(p => p.issued), backgroundColor: '#007bff' },
                { label: 'Points Redeemed', data: data.time_based_analytics.points_over_time.wallet_points.map(p => p.redeemed), backgroundColor: '#dc3545' }
            ]
        },
        options: { scales: { y: { beginAtZero: true } } }
    });

    const activityCtx = document.getElementById('activity-trends-chart').getContext('2d');
    activityChart = new Chart(activityCtx, {
        type: 'bar',
        data: {
            labels: data.time_based_analytics.customer_activity_trends.map(t => t.month),
            datasets: [{ label: 'Transactions', data: data.time_based_analytics.customer_activity_trends.map(t => t.transactions), backgroundColor: '#28a745' }]
        },
        options: { scales: { y: { beginAtZero: true } } }
    });
}

function displayDashboard(data) {
    document.getElementById('shop-details').innerHTML = `
        <h5 class="card-title">Shop Details</h5>
        <table class="table table-sm">
            <tr><th>ID</th><td>${data.shop_details.id}</td></tr>
            <tr><th>Name</th><td>${data.shop_details.name}</td></tr>
            <tr><th>API Key</th><td>${data.shop_details.api_key}</td></tr>
        </table>
    `;
    document.getElementById('max-points').innerHTML = `
        <h5 class="card-title">Max Points</h5>
        <p class="fs-5">${data.maximum_points || 'Not set'}</p>
    `;
    document.getElementById('used-points').innerHTML = `
        <h5 class="card-title">Used Points</h5>
        <table class="table table-sm">
            <tr><th>Issued</th><td>${data.used_points.total_points_issued}</td></tr>
            <tr><th>Redeemed</th><td>${data.used_points.total_points_redeemed}</td></tr>
        </table>
    `;
    document.getElementById('currency-details').innerHTML = `
        <h5 class="card-title">Currency Details</h5>
        <table class="table table-sm">
            <tr><th>Currency</th><td>${data.currency_details?.currency || 'N/A'}</td></tr>
            <tr><th>Points/Currency</th><td>${data.currency_details?.points_per_currency || 'N/A'}</td></tr>
        </table>
    `;
    document.getElementById('purchase-rules-dash').innerHTML = `
        <h5 class="card-title">Purchase Rules</h5>
        <table class="table table-sm">
            <thead><tr><th>ID</th><th>Min</th><th>Max</th><th>Points</th><th>Redeemable</th></tr></thead>
            <tbody>${data.shop_purchase_rules.map(r => `<tr><td>${r.id}</td><td>${r.min_purchase_amount}</td><td>${r.max_purchase_amount}</td><td>${r.points}</td><td>${r.redeemable}</td></tr>`).join('')}</tbody>
        </table>
    `;
    document.getElementById('direct-rewards').innerHTML = `
        <h5 class="card-title">Direct Rewards</h5>
        <table class="table table-sm">
            <thead><tr><th>ID</th><th>Points</th><th>Type</th><th>Redeemed</th></tr></thead>
            <tbody>${data.direct_rewards.list.map(dr => `<tr><td>${dr.id}</td><td>${dr.points}</td><td>${dr.reward_type_name}</td><td>${dr.redeemed_at || 'No'}</td></tr>`).join('')}</tbody>
        </table>
        <p><strong>Total Points:</strong> ${data.direct_rewards.total_direct_points}</p>
    `;
    document.getElementById('shop-tiers').innerHTML = `
        <h5 class="card-title">Shop Tiers</h5>
        <table class="table table-sm">
            <thead><tr><th>ID</th><th>Name</th><th>Min</th><th>Max</th></tr></thead>
            <tbody>${data.shop_tiers.list.map(t => `<tr><td>${t.id}</td><td>${t.name}</td><td>${t.min_points}</td><td>${t.max_points}</td></tr>`).join('')}</tbody>
        </table>
        <h6>Customer Summary</h6>
        <table class="table table-sm">
            <thead><tr><th>Tier</th><th>Count</th></tr></thead>
            <tbody>${data.shop_tiers.customer_summary.map(s => `<tr><td>${s.tier_name}</td><td>${s.customer_count}</td></tr>`).join('')}</tbody>
        </table>
    `;
}