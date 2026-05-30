# Basic Data Exploration and Cleaning using Pandas

## Objective

The goal of this assignment was to learn the basics of data exploration and data cleaning using Pandas. A shopping dataset was used to understand how real-world data can be analyzed and prepared for further processing.

## Tools Used

* Databricks Free Edition
* Python
* Pandas
* NumPy

## Dataset

Shopping Dataset from Kaggle

## What I Did

### 1. Loaded the Dataset

I uploaded the dataset to Databricks and loaded it into a Pandas DataFrame using `read_csv()`. This allowed me to work with the data and perform various operations.

### 2. Explored the Data

Before cleaning the dataset, I explored it to understand its structure and contents. I used functions such as:

* `head()`
* `tail()`
* `shape`
* `columns`
* `dtypes`
* `info()`

This helped me understand the number of records, available features, and data types.

### 3. Handled Missing Values

I checked the dataset for missing values using `isnull().sum()`.

To handle them:

* Missing values in the `discount` column were filled using the median.
* Missing values in `seller_name` and `seller_information` were filled using the most frequent value (mode).
* Columns such as `videos`, `what_customers_said`, and `variations` were removed because they contained a large number of missing values and were not essential for this analysis.

### 4. Performed Basic Operations

To better understand the dataset, I performed several filtering and selection operations.

These included:

* Selecting important columns for analysis.
* Filtering highly rated products.
* Finding products with high discounts.
* Identifying premium products based on price.
* Combining multiple conditions to find products that had both high ratings and high discounts.

### 5. Checked for Duplicate Records

I checked the dataset for duplicate records using `duplicated()`.

No duplicate rows were found in the dataset. However, I still applied `drop_duplicates()` as a standard data-cleaning practice.

### 6. Created a Derived Column

The assignment required creating a derived column using:

`total_amount = price × quantity`

Since the dataset did not contain a quantity column, I created a meaningful alternative using the available pricing information.

Formula used:

`total_amount = initial_price - (initial_price × discount / 100)`

This represents the final amount payable after applying the discount.

### 7. Saved the Cleaned Dataset

After completing all cleaning and transformation steps, the dataset was saved as:

`cleaned_dataset.csv`

## Challenges Faced

This was my first time using Databricks for a complete data-cleaning task. Initially, understanding file management and working with datasets inside the platform took some time.

Another challenge was handling missing values correctly. Different columns required different approaches, so I used median, mode, and column removal based on the nature of the data.

The assignment also required a derived column based on quantity, but the dataset did not contain a quantity field. To address this, I created a practical alternative using the available price and discount columns.

## Conclusion

Through this assignment, I gained hands-on experience with Pandas, data cleaning techniques, and the Databricks environment. I learned how to explore a dataset, handle missing values, perform filtering operations, create derived features, and prepare a clean dataset for further analysis.
