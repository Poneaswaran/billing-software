import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# -------------------------------
# 1. Load Dataset
# -------------------------------
df = pd.read_csv("data.csv")

# -------------------------------
# 2. Basic Preprocessing
# -------------------------------

# Remove rows with missing values (or you can impute)
df = df.dropna()

# Assuming the last column is the target
X = df.iloc[:, :-1]    # all columns except last
y = df.iloc[:, -1]     # last column as label
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("Accuracy:", accuracy)
print("\nClassification Report:\n", classification_report(y_test, y_pred))
joblib.dump(model, "model.pkl")
print("\nModel saved as model.pkl")
