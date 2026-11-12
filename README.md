# WasteWise AI
### AI-Powered Food Waste Prediction & Inventory Optimization

**Author: Sameer Dhanjode**

WasteWise AI is an intelligent inventory management and food-waste reduction application. It helps businesses monitor inventory, identify expiry risks, review recommendations, plan replenishment, and understand inventory performance through an interactive dashboard.

## Project Overview

Food businesses face challenges such as product expiry, excess inventory, poor demand planning, and unnecessary food waste.

WasteWise AI combines inventory management, machine-learning predictions, stock movement tracking, and analytics to support better inventory decisions.

### Project Objectives
- Monitor products and inventory batches.
- Identify batches at risk of expiry.
- Support demand forecasting and reorder planning.
- Track incoming stock and inventory movements.
- Generate inventory recommendations.
- Monitor model performance and data quality.
- Reduce avoidable food waste.

## Key Features

### 1. Dashboard
- Total products and inventory batches.
- High-risk and expired batch KPIs.
- Remaining stock and inventory cost value.
- Inventory priority and expiry-risk charts.
- Stock movement KPIs and recent movement history.

### 2. Product Management
- Product information and categories.
- Product-level inventory details.

### 3. Inventory Management
- Inventory batch tracking.
- Remaining stock quantities.
- Expiry date monitoring.
- Unknown expiry-date identification.
- Stock movement recording and history.
- Inventory report export.

### 4. Purchase Orders
- Purchase order management.
- Incoming stock receipts.
- Inventory batch creation after receiving stock.
- Receipt history and stock movement tracking.
- Support for unknown expiry dates.

### 5. Suppliers
- Supplier information and management.

### 6. Sales Analytics
- Sales-related inventory analytics.
- Inventory performance insights.

### 7. Demand Forecasting
- Demand forecast analysis.
- Forecast outputs to support purchasing decisions.

### 8. Reorder Planning
- Inventory replenishment planning.
- Reorder recommendations.

### 9. Expiry Tracking and Recommendations
- Expiry-risk identification.
- Inventory risk predictions.
- Recommended inventory actions.

### 10. Waste Insights
- Waste-related summaries.
- Insights to support waste reduction.

### 11. Model Monitoring
- Data drift monitoring.
- Prediction quality reports.
- Model performance monitoring.

### 12. Settings
- Application configuration and settings.

## Technology Stack

| Category | Technologies |
|---|---|
| Programming | Python |
| Frontend | Streamlit |
| Database | MySQL |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly |
| Machine Learning | Scikit-learn |
| Model Tracking | MLflow integration |
| Database Connectivity | SQLAlchemy |
| Testing | Pytest |
| IDE | Visual Studio Code |
| Version Control | Git and GitHub |

## Project Architecture

```text
WasteWise-AI/
│
├── app/
│   ├── assets/
│   │   └── style.css
│   ├── components/
│   │   ├── dashboard_view.py
│   │   ├── data_service.py
│   │   ├── products_view.py
│   │   ├── inventory_view.py
│   │   ├── purchase_orders_view.py
│   │   ├── suppliers_view.py
│   │   ├── sales_analytics_view.py
│   │   ├── demand_forecast_view.py
│   │   ├── reorder_planning_view.py
│   │   ├── recommendations_view.py
│   │   ├── waste_insights_view.py
│   │   ├── settings_view.py
│   │   └── ui.py
│   ├── monitoring_dashboard.py
│   └── streamlit_app.py
│
├── models/
├── monitoring/
│   ├── drift_monitor.py
│   ├── performance_monitor.py
│   ├── prediction_monitor.py
│   ├── plots/
│   └── reports/
│
├── notebooks/
├── reports/
├── src/
│   ├── database/
│   ├── models/
│   └── recommendations/
│
├── tests/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation and Setup

### Prerequisites
- Python 3.11
- MySQL Server 8.x
- Git
- Visual Studio Code

### 1. Clone the Repository

```bash
git clone https://github.com/SameerD14/WasteWise-AI.git
cd WasteWise-AI
```

### 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a local `.env` file using `.env.example` as a template.

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=wastewise_ai
DB_USER=root
DB_PASSWORD=your_mysql_password
```

Replace the placeholder with your own MySQL password.

**Security:** Never upload `.env` or real database credentials to GitHub.

### 5. Configure MySQL

1. Start MySQL Server.
2. Create the `wastewise_ai` database if required.
3. Configure your local `.env` file.
4. Use the project's database initialization workflow for a new database.

**Important:** Back up existing database records before running initialization or data-loading scripts. Review scripts before running any operation that may replace existing data.

### 6. Run the Application

```powershell
python -m streamlit run app/streamlit_app.py
```

Open:

`http://localhost:8501`

## Running Tests

Run all automated tests:

```powershell
python -m pytest tests -q
```

Run Python syntax checks:

```powershell
python -m compileall -q app src monitoring
```

The project includes tests for database operations, predictions, recommendations, and inventory movements.

## Inventory Movement Safety

The stock movement workflow includes:
- Positive movement quantity validation.
- Prevention of negative stock.
- Mandatory movement reasons.
- Expired-stock restrictions for sales and consumption.
- Waste write-off support.
- Database transactions for stock updates and movement history.

Purchase receipts are also recorded as incoming stock movements.

## Machine Learning and Monitoring

The project includes an expiry-risk model artifact and supporting feature information in the `models/` directory.

The prediction and recommendation workflows help identify inventory batches that may need attention.

Monitoring outputs include:
- Data drift reports.
- Model performance reports.
- Prediction data quality.
- Prediction status summaries.
- Risk probability summaries.

Model predictions are decision-support estimates and should be reviewed alongside verified inventory and expiry information.

## Database Safety

- Store database credentials in local environment variables.
- Never commit `.env`.
- Back up the database before schema changes or data reloads.
- Review data initialization scripts before execution.
- Do not publish sensitive business or customer data.

## Future Improvements

- User authentication and role-based access.
- Automated scheduled demand forecasting.
- Advanced supplier analytics.
- Additional model validation.
- Cloud deployment.
- Expanded end-to-end testing.

## Author

**Sameer Dhanjode**

GitHub: https://github.com/SameerD14

Project: https://github.com/SameerD14/WasteWise-AI

## License

No license has been specified yet. All rights are reserved by the author unless a license is added to this repository.