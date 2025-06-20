import numpy as np
import pickle
from flask import Flask, request, render_template
import lime
import lime.lime_tabular
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import os
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
BASE_DIR = current_file.parent
# Add the repository root to Python path
REPO_ROOT = BASE_DIR.parent
sys.path.append(str(REPO_ROOT))

# Load trained RandomForestClassifier model
model_path = BASE_DIR / "RFC_Model"
model = pickle.load(open(model_path, "rb"))



# Define features
numerical_features = ['tenure', 'MonthlyCharges', 'TotalCharges']
categorical_features = ['Contract', 'TechSupport', 'OnlineSecurity', 'InternetService',
                        'PaymentMethod', 'DeviceProtection',
                        'OnlineBackup', 'StreamingMovies', 'StreamingTV']
feature_names = numerical_features + categorical_features

# Load raw training data
X_train_raw = pd.read_csv("Telco-Customer-Churn.csv")

X_train_raw['TotalCharges'] = pd.to_numeric(X_train_raw['TotalCharges'], errors='coerce')

# Initialize LabelEncoders using actual data
label_encoders = {}
for col in categorical_features:
    le = LabelEncoder()
    le.fit(X_train_raw[col].astype(str))
    label_encoders[col] = le

# Preprocess training data for LIME
X_train_processed = X_train_raw[feature_names].copy()
X_train_processed[numerical_features] = X_train_processed[numerical_features].apply(pd.to_numeric, errors='coerce')
X_train_processed.dropna(inplace=True)
for col in categorical_features:
    X_train_processed[col] = label_encoders[col].transform(X_train_processed[col].astype(str))

# Rule-based logic function
def rule_based_risk(form_data):
    high_risk_conditions = [
        form_data['Contract'] == 'Month-to-month',
        form_data['TechSupport'] == 'No',
        form_data['OnlineSecurity'] == 'No',
        form_data['InternetService'] == 'Fiber optic',
        form_data['PaymentMethod'] == 'Electronic check',
        form_data['DeviceProtection'] == 'No',
        form_data['OnlineBackup'] == 'No',
        form_data['StreamingMovies'] == 'Yes',
        form_data['StreamingTV'] == 'Yes',
        float(form_data['tenure']) < 6,
        float(form_data['MonthlyCharges']) > 80,
        float(form_data['TotalCharges']) < 200,
    ]

    medium_risk_conditions = [
        form_data['Contract'] == 'One year',
        form_data['TechSupport'] == 'No',
        form_data['OnlineSecurity'] == 'No',
        form_data['InternetService'] == 'DSL',
        form_data['DeviceProtection'] == 'No',
        6 <= float(form_data['tenure']) < 12,
        60 <= float(form_data['MonthlyCharges']) <= 80,
        200 <= float(form_data['TotalCharges']) < 500,
    ]

    high_score = sum(high_risk_conditions)
    medium_score = sum(medium_risk_conditions)

    if high_score >= 6:
        return "High"
    elif medium_score >= 4:
        return "Medium"
    else:
        return "Low"

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    try:
        input_data = []
        for feature in feature_names:
            value = request.form[feature]
            if feature in numerical_features:
                input_data.append(float(value))
            else:
                encoder = label_encoders[feature]
                if value in encoder.classes_:
                    input_data.append(encoder.transform([value])[0])
                else:
                    return f"Invalid value '{value}' for feature '{feature}'"

        input_df = pd.DataFrame([input_data], columns=feature_names)

        # Model-based risk prediction
        risk_score = model.predict_proba(input_df)[0][1]
        risk_category = "High" if risk_score > 0.7 else "Medium" if risk_score > 0.3 else "Low"


        if risk_score > 0.7:
            retention_action =['Grant loyalty benefits','Offer cashback offers','Schedule agent call to customer']
        elif risk_score >0.3:
            retention_action=['Grant loyalty points']
        else:
            retention_action=['No Action Required']


        
        # Rule-based category
        rule_based_category = rule_based_risk(request.form)

        # LIME explanation
        explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=np.array(X_train_processed),
            feature_names=feature_names,
            class_names=['No Churn', 'Churn'],
            mode='classification'
        )

        explanation = explainer.explain_instance(
            input_df.values[0],
            model.predict_proba,
            num_features=4
        )
        lime_html = explanation.as_html()

        return render_template("index.html",
                               risk_score=round(risk_score * 100, 2),
                               risk_category=risk_category,
                               retention_actions=retention_action,
                               rule_based_category=rule_based_category,
                               lime_html=lime_html)

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
print(f"BASE_DIR: {BASE_DIR}")
print(f"Files in BASE_DIR: {list(BASE_DIR.glob('*'))}")
print(f"REPO_ROOT: {REPO_ROOT}")
print(f"Files in REPO_ROOT: {list(REPO_ROOT.glob('*'))}")