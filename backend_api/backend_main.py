from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
import io 

app = FastAPI(
    title="CSPDCL Smart Grid Analytics Core Engine",
    description="Production-grade REST API backend handling load forecasting and non-technical loss detection.",
    version="1.0.0"
)

# 🌐 SECURITY BRIDGE: Cross-Origin Resource Sharing middleware alignment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DEFENSIVE DATA ENGINEERING SECURITY FILTER ---
def validate_cspdcl_schema(df: pd.DataFrame):
    """
    Acts as an enterprise security filter. Checks the parsed DataFrame for layout format errors,
    missing info, or impossible electrical readings before running core ML computations.
    """
    required_columns = ["Feeder_ID", "DTR_ID", "Consumer_No", "Date", "Consumption_kWh"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, [f"Missing required grid columns: {missing_columns}. Check headers."]
        
    total_nulls = df[required_columns].isnull().sum().sum()
    if total_nulls > 0:
        return False, [f"Dataset contains {total_nulls} blank/missing value nodes. Clean cells first."]
        
    negative_values = (df["Consumption_kWh"] < 0).sum()
    if negative_values > 0:
        return False, [f"Grid Data Entry Error: Found {negative_values} rows with negative consumption values. Physically impossible."]
        
    if not pd.api.types.is_numeric_dtype(df["Consumption_kWh"]):
        return False, ["Data Type Error: The 'Consumption_kWh' target data stream must contain purely numbers."]
        
    return True, []


# Helper tool to parse uploaded files safely


def parse_network_file(file: UploadFile):
    try:
        # Read the raw incoming network stream buffer completely into memory
        file_bytes = file.file.read()
        
        # Wrap the byte blocks in an in-memory stream bytes container
        data_stream = io.BytesIO(file_bytes)

        if file.filename.endswith(".csv"):
            # 🌟 Linux/Render Fix: Explicitly specify UTF-8 encoding and handle hidden BOM tokens
            df = pd.read_csv(data_stream, encoding='utf-8', encoding_errors='ignore')
        elif file.filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(data_stream)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel.")
        
        # Clean white spaces from column headers that sometimes sneak into network packets
        df.columns = df.columns.str.strip()

        # Enforce structural validation schema constraints
        is_valid, validation_errors = validate_cspdcl_schema(df)
        if not is_valid:
            raise HTTPException(status_code=422, detail="; ".join(validation_errors))
            
        # 🌟 Linux/Render Fix: Force errors='coerce' so dates parse identically on Linux as on Windows
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        
        # Drop rows where dates failed to parse cleanly
        df = df.dropna(subset=["Date"])
        
        return df.sort_values("Date")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process data stream matrix: {str(e)}")

# --- ENDPOINT 1: THEFT DETECTION ENGINE (FIXED FOR DYNAMIC SELECTION) ---
@app.post("/api/v1/theft-detection")
async def detect_grid_theft(
    file: UploadFile = File(...),
    feeder_id: str = "All Feeders",
    dtr_id: str = "All DTRs"
):
    master_df = parse_network_file(file)
    
    # 🌟 FIXED: Dynamically extract dropdown arrays for theft matrix page view
    extracted_feeders = sorted(master_df["Feeder_ID"].dropna().unique().tolist())
    
    # Isolate dataframe slice using an independent local copy variable
    working_df = master_df.copy()
    if feeder_id and feeder_id != "All Feeders":
        working_df = working_df[working_df["Feeder_ID"] == feeder_id]
        
    extracted_dtrs = sorted(working_df["DTR_ID"].dropna().unique().tolist())
    
    if dtr_id and dtr_id != "All DTRs":
        working_df = working_df[working_df["DTR_ID"] == dtr_id]
        
    if working_df.empty:
        return {
            "status": "success", 
            "feeders": extracted_feeders, 
            "dtrs": extracted_dtrs, 
            "overview": {"total_nodes": 0, "flagged_suspects": 0, "peak_load": 0.0},
            "data": []
        }

    consumption_features = working_df[["Consumption_kWh"]].values
    
    # Run Unsupervised Spatial Isolation Trees
    iso_model = IsolationForest(n_estimators=200, contamination=0.1, random_state=42)
    working_df["Anomaly"] = iso_model.fit_predict(consumption_features)
    
    lof_model = LocalOutlierFactor(n_neighbors=min(20, len(working_df)), contamination=0.1)
    working_df["LOF_Anomaly"] = lof_model.fit_predict(consumption_features)
    
    # Calculate DTR Peer Group Analytics
    working_df["DTR_Baseline_Avg"] = working_df.groupby(["DTR_ID", "Date"])["Consumption_kWh"].transform("mean")
    working_df["DTR_Deviation_Pct"] = (abs(working_df["Consumption_kWh"] - working_df["DTR_Baseline_Avg"]) / working_df["DTR_Baseline_Avg"]) * 100
    
    working_df["Anomaly_Factor"] = working_df["Anomaly"].apply(lambda x: 100 if x == -1 else 15)
    working_df["Risk_Score"] = (0.6 * working_df["Anomaly_Factor"]) + (0.4 * working_df["DTR_Deviation_Pct"])
    working_df["Risk_Score"] = working_df["Risk_Score"].clip(0, 100)
    
    working_df["Risk_Level"] = working_df["Risk_Score"].apply(
        lambda x: "High Risk 🔴" if x >= 75 else ("Medium Risk 🟠" if x >= 45 else "Low Risk 🟢")
    )
    working_df["Status"] = working_df["Anomaly"].apply(lambda x: "Suspicious 🚩" if x == -1 else "Normal ✅")
    
    working_df["Date"] = working_df["Date"].dt.strftime("%Y-%m-%d")
    
    total_nodes = int(working_df["Consumer_No"].nunique())
    flagged_suspects = int((working_df["Status"] == "Suspicious 🚩").sum())
    peak_load = float(working_df["Consumption_kWh"].max())

    return {
        "status": "success",
        "feeders": extracted_feeders,
        "dtrs": extracted_dtrs,
        "selected_feeder": feeder_id,
        "selected_dtr": dtr_id,
        "overview": {
            "total_nodes": total_nodes,
            "flagged_suspects": flagged_suspects,
            "peak_load": peak_load
        },
        "data": working_df.to_dict(orient="records")
    }


# --- ENDPOINT 2: DEMAND FORECASTING ENGINE (FIXED BOTTLE-NECK LOOPS) ---
@app.post("/api/v1/demand-forecast")
async def generate_demand_forecast(
    file: UploadFile = File(...), 
    feeder_id: str = None, 
    dtr_id: str = "Aggregate Feeder Demand"
):
    master_df = parse_network_file(file)
    
    # Extract locations from unmutated file array
    extracted_feeders = sorted(master_df["Feeder_ID"].dropna().unique().tolist())
    
    if not feeder_id and extracted_feeders:
        feeder_id = extracted_feeders[0]
        
    # Isolate relevant regional distribution transformer nodes safely
    feeder_slice_df = master_df[master_df["Feeder_ID"] == feeder_id]
    extracted_dtrs = sorted(feeder_slice_df["DTR_ID"].dropna().unique().tolist())
    
    # 🌟 FIXED: Use local working dataframe instead of altering the function master object
    working_df = master_df.copy()
    if feeder_id:
        working_df = working_df[working_df["Feeder_ID"] == feeder_id]
    if dtr_id and dtr_id != "Aggregate Feeder Demand":
        working_df = working_df[working_df["DTR_ID"] == dtr_id]
        
    if working_df.empty:
        raise HTTPException(status_code=400, detail="The chosen location configuration holds zero data metrics inside this sheet.")

    forecast_target = working_df.groupby("Date")["Consumption_kWh"].sum().reset_index()
    forecast_target.columns = ["ds", "y"]
    
    if len(forecast_target) < 30:
        raise HTTPException(
            status_code=400, 
            detail="Insufficient timeline metrics. At least 30 distinct dates are required to establish a time-series forecast model."
        )
    
    # Split Data 80/20 for Validation evaluation
    train_size = int(len(forecast_target) * 0.8)
    train_df = forecast_target.iloc[:train_size]
    test_df = forecast_target.iloc[train_size:].copy()
    
    # Run validation Prophet
    m_eval = Prophet(yearly_seasonality=False, daily_seasonality=False)
    m_eval.fit(train_df)
    forecast_test = m_eval.predict(test_df[['ds']].copy())
    
    # Calculate errors
    mae = float(mean_absolute_error(test_df["y"], forecast_test["yhat"]))
    rmse = float(np.sqrt(mean_squared_error(test_df["y"], forecast_test["yhat"])))
    mape = float(np.mean(np.abs((test_df["y"].values - forecast_test["yhat"].values) / test_df["y"].values))) * 100
    
    # Run full production forecast
    final_model = Prophet(yearly_seasonality=False, daily_seasonality=False)
    final_model.fit(forecast_target)
    future_dates = final_model.make_future_dataframe(periods=7)
    forecast_future = final_model.predict(future_dates)
    
    historical_data = forecast_target.copy()
    historical_data["Date"] = historical_data["ds"].dt.strftime("%Y-%m-%d")
    
    future_data = forecast_future.tail(7).copy()
    future_data["Date"] = future_data["ds"].dt.strftime("%Y-%m-%d")
    
    current_load = float(forecast_target['y'].iloc[-1])
    historical_avg_load = float(forecast_target['y'].mean())
    projected_next_day = float(future_data['yhat'].iloc[0])
    
    return {
        "status": "success",
        "feeders": extracted_feeders,
        "dtrs": extracted_dtrs,
        "selected_feeder": feeder_id,
        "selected_dtr": dtr_id,
        "metrics": {
            "mae": mae, 
            "rmse": rmse, 
            "mape": mape,
            "current_load": current_load,
            "historical_avg_load": historical_avg_load,
            "projected_next_day": projected_next_day
        },
        "historical": historical_data[["Date", "y"]].to_dict(orient="records"),
        "predictions": future_data[["Date", "yhat", "yhat_lower", "yhat_upper"]].to_dict(orient="records"),
        "validation": {
            "dates": test_df["ds"].dt.strftime("%Y-%m-%d").tolist(),
            "actuals": test_df["y"].values.tolist(),
            "predicted": forecast_test["yhat"].values.tolist()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_main:app", host="127.0.0.1", port=8000, reload=True)
