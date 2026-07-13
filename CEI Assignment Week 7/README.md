# Delta Lake MERGE Implementation – Week 7

**Celebal Technologies Excellence Internship – Week 7 Assignment**

## Project Overview

This project demonstrates how Delta Lake can be used to perform incremental data processing in Databricks. The implementation includes loading a dataset, cleaning and transforming data, creating an incremental dataset, performing MERGE operations, implementing Slowly Changing Dimension (SCD Type 2), and validating the final results.

---

## Objective

The main objective of this assignment is to:

- Load the Superstore dataset into Delta Lake.
- Clean and prepare the dataset.
- Simulate an incremental data load.
- Perform Delta Lake MERGE operations.
- Implement SCD Type 2 for historical data tracking.
- Validate the final merged dataset.

---

## Technologies Used

- Databricks Community Edition
- Apache Spark (PySpark)
- Delta Lake
- Python
- SQL

---

## Project Structure

```
delta-lake-assignment/
│
├── data/
│   ├── superstore_master.csv
│   └── superstore_incremental.csv
│
├── notebooks/
│   └── delta_scd_assignment.ipynb
│
├── screenshots/
│   ├── data_loading/
│   ├── data_cleaning/
│   ├── scd1/
│   ├── scd2/
│   ├── validation/
│   └── final_output/
│
├── report/
│   └── assignment_summary.md
│
└── README.md
```

---

## Workflow

### Step 1 – Load Dataset

- Loaded the Superstore dataset into a Spark DataFrame.
- Standardized column names for Delta Lake compatibility.
- Created the `superstore_raw` Delta table.

---

### Step 2 – Data Cleaning

- Checked for duplicate records.
- Handled missing values.
- Demonstrated the cleaning process using a synthetic dirty dataset.
- Created the cleaned Delta table `superstore_master`.

---

### Step 3 – Incremental Dataset

- Loaded the incremental dataset.
- Standardized column names.
- Created the `superstore_incremental` Delta table.

---

### Step 4 – Delta MERGE

Implemented Delta Lake MERGE using **Row_ID** as the primary key.

- Updated existing records.
- Inserted new records automatically.

---

### Step 5 – SCD Type 2

Implemented Slowly Changing Dimension Type 2 using:

- effective_date
- end_date
- is_current

to preserve historical versions of changed records.

---

### Step 6 – Validation

Validated the final output by:

- Checking row counts
- Verifying unique Row_ID values
- Confirming updates and new inserts
- Reviewing Delta transaction history

---

## Challenges Faced

During implementation, the following issues were encountered:

- Delta Lake rejected column names containing spaces and special characters.
- MERGE failed because the master and incremental tables had inconsistent schemas.
- Existing Delta tables retained previous schemas after modifications.

These issues were resolved by:

- Renaming all columns using underscores.
- Recreating Delta tables with consistent schemas.
- Using `overwriteSchema` while writing Delta tables.

---

## Results

- Successfully loaded the dataset into Delta tables.
- Performed incremental MERGE operations.
- Implemented SCD Type 2 successfully.
- Validated the merged dataset without duplicate Row_ID values.
- Verified all operations using `DESCRIBE HISTORY`.

---

## Screenshots

Screenshots for each stage of the implementation are available inside the **screenshots/** folder.

---

## Author

**Siga Nithin**

B.Tech – Computer Science and Engineering

CVR College of Engineering

Celebal Technologies Excellence Internship – Week 7