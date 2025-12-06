"""
Generate Ground Truth Results for AutoInsight Test Suite
Calculates actual answers for all test questions using the Superstore dataset.
"""

import pandas as pd
import os


def generate_ground_truth(data_file_path: str = 'test_data/superstore.csv'):
    """
    Generate ground truth answers for all test questions.
    
    Args:
        data_file_path: Path to the superstore.csv file
    """
    # Load Data (Adjust encoding if necessary)
    print(f"Loading data from: {data_file_path}")
    try:
        df = pd.read_csv(data_file_path, encoding='utf-8', on_bad_lines='skip')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(data_file_path, encoding='latin-1', on_bad_lines='skip')
        except:
            try:
                df = pd.read_csv(data_file_path, encoding='windows-1252', on_bad_lines='skip')
            except:
                df = pd.read_csv(data_file_path, encoding='utf-8', errors='ignore', on_bad_lines='skip')
    
    # Ensure dates are datetime objects
    if 'Order Date' in df.columns:
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
    
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns\n")
    print("="*80)
    print("GROUND TRUTH RESULTS FOR SUPERSTORE TEST SUITE")
    print("="*80)
    
    # ========================================================================
    # LEVEL 1: Basic Questions
    # ========================================================================
    print("\n--- LEVEL 1: Basic Questions ---\n")
    
    # Q1: Total Sales Revenue
    total_sales = df['Sales'].sum()
    print(f"Q1. Total Sales Revenue: ${total_sales:,.2f}")
    print(f"    Expected: {int(total_sales)}")
    
    # Q2: Average Discount
    avg_discount = df['Discount'].mean()
    print(f"\nQ2. Average Discount: {avg_discount:.4f} ({avg_discount:.2%})")
    print(f"    Expected: {avg_discount:.3f}")
    
    # Q3: Unique Orders
    unique_orders = df['Order ID'].nunique()
    print(f"\nQ3. Total Unique Orders: {unique_orders}")
    print(f"    Expected: {unique_orders}")
    
    # Q4: Total Quantity in East Region
    east_quantity = df[df['Region'] == 'East']['Quantity'].sum()
    print(f"\nQ4. Total Quantity in 'East' Region: {east_quantity}")
    print(f"    Expected: {east_quantity}")
    
    # Q5: Total profit by Technology category
    tech_profit = df[df['Category'] == 'Technology']['Profit'].sum()
    print(f"\nQ5. Total Profit by Technology Category: ${tech_profit:,.2f}")
    print(f"    Expected: {int(tech_profit)}")
    
    # Q6: Unique Product Names
    unique_products = df['Product Name'].nunique()
    print(f"\nQ6. Unique Product Names: {unique_products}")
    print(f"    Expected: {unique_products}")
    
    # Q7: Average sales per order
    avg_sales_per_order = df.groupby('Order ID')['Sales'].sum().mean()
    print(f"\nQ7. Average Sales per Order: ${avg_sales_per_order:,.2f}")
    print(f"    Expected: {int(avg_sales_per_order)}")
    
    # Q8: Earliest order date
    if 'Order Date' in df.columns and df['Order Date'].notna().any():
        earliest_date = df['Order Date'].min()
        print(f"\nQ8. Earliest Order Date: {earliest_date}")
        print(f"    Expected: '{earliest_date}'")
    else:
        print(f"\nQ8. Earliest Order Date: Date column not available")
        print(f"    Expected: None")
    
    # Q9: State with lowest total sales
    state_sales = df.groupby('State')['Sales'].sum()
    lowest_state = state_sales.idxmin()
    lowest_sales = state_sales.min()
    print(f"\nQ9. State with Lowest Total Sales: {lowest_state} (${lowest_sales:,.2f})")
    print(f"    Expected: '{lowest_state}'")
    
    # Q10: Orders with Second Class shipping
    second_class_orders = df[df['Ship Mode'] == 'Second Class']['Order ID'].nunique()
    print(f"\nQ10. Orders with Second Class Shipping: {second_class_orders}")
    print(f"    Expected: {second_class_orders}")
    
    # Q11: Maximum discount
    max_discount = df['Discount'].max()
    print(f"\nQ11. Maximum Discount: {max_discount:.4f} ({max_discount:.2%})")
    print(f"    Expected: {max_discount:.3f}")
    
    # Q12: Top 3 sub-categories by sales
    top_subcats = df.groupby('Sub-Category')['Sales'].sum().nlargest(3)
    print(f"\nQ12. Top 3 Sub-Categories by Sales:")
    for i, (subcat, sales) in enumerate(top_subcats.items(), 1):
        print(f"    {i}. {subcat}: ${sales:,.2f}")
    print(f"    Expected: {top_subcats.index.tolist()}")
    
    # ========================================================================
    # LEVEL 2: Complex Questions
    # ========================================================================
    print("\n" + "="*80)
    print("--- LEVEL 2: Complex Questions ---\n")
    
    # Q1: Top 5 Profitable Customers in Technology
    tech_df = df[df['Category'] == 'Technology']
    if len(tech_df) > 0:
        tech_customers = tech_df.groupby('Customer Name')['Profit'].sum().nlargest(5)
        print(f"Q1. Top 5 Tech Customers:")
        for i, (customer, profit) in enumerate(tech_customers.items(), 1):
            print(f"    {i}. {customer}: ${profit:,.2f}")
        print(f"    Expected (Top 1): '{tech_customers.index[0]}'")
        print(f"    Expected (All Top 5): {tech_customers.index.tolist()}")
    else:
        print("Q1. Top 5 Tech Customers: No Technology category found")
        print("    Expected: None")
    
    # Q2: Profit difference (East - South)
    east_prof = df[df['Region'] == 'East']['Profit'].sum()
    south_prof = df[df['Region'] == 'South']['Profit'].sum()
    profit_diff = east_prof - south_prof
    print(f"\nQ2. East vs South Profit Difference: ${profit_diff:,.2f}")
    print(f"    East Profit: ${east_prof:,.2f}")
    print(f"    South Profit: ${south_prof:,.2f}")
    print(f"    Expected: {int(profit_diff)}")
    
    # Q3: Profit margin (Profit / Sales) for each Category
    print(f"\nQ3. Profit Margin by Category:")
    category_margins = df.groupby('Category').apply(
        lambda x: (x['Profit'].sum() / x['Sales'].sum()) if x['Sales'].sum() != 0 else 0,
        include_groups=False
    )
    margins_dict = category_margins.to_dict()
    for category, margin in margins_dict.items():
        print(f"    {category}: {margin:.4f} ({margin:.2%})")
    print(f"    Expected: {margins_dict}")
    
    # Q4: Average profit for Consumer segment in most recent year
    if 'Order Date' in df.columns and df['Order Date'].notna().any():
        most_recent_year = df['Order Date'].dt.year.max()
        consumer_profit_avg = df[(df['Segment'] == 'Consumer') & (df['Order Date'].dt.year == most_recent_year)]['Profit'].mean()
        print(f"\nQ4. Average Profit for Consumer Segment in {most_recent_year}: ${consumer_profit_avg:,.2f}")
        print(f"    Expected: {int(consumer_profit_avg)}")
    else:
        print(f"\nQ4. Average Profit for Consumer Segment (Most Recent Year): Date column not available")
        print(f"    Expected: None")
    
    # Q5: Customers with more than 10 orders
    customer_orders = df.groupby('Customer Name')['Order ID'].nunique()
    customers_10plus = (customer_orders > 10).sum()
    print(f"\nQ5. Customers with More than 10 Orders: {customers_10plus}")
    print(f"    Expected: {customers_10plus}")
    
    # Q6: West region sales excluding California
    west_no_ca_sales = df[(df['Region'] == 'West') & (df['State'] != 'California')]['Sales'].sum()
    print(f"\nQ6. West Region Sales (Excluding California): ${west_no_ca_sales:,.2f}")
    print(f"    Expected: {int(west_no_ca_sales)}")
    
    # Q7: Month with highest average sales
    if 'Order Date' in df.columns and df['Order Date'].notna().any():
        monthly_avg = df.groupby(df['Order Date'].dt.month)['Sales'].mean()
        best_month = monthly_avg.idxmax()
        best_avg = monthly_avg.max()
        print(f"\nQ7. Month with Highest Average Sales: Month {best_month} (${best_avg:,.2f})")
        print(f"    Expected: {best_month}")
    else:
        print(f"\nQ7. Month with Highest Average Sales: Date column not available")
        print(f"    Expected: None")
    
    # Q8: Profit margin for Furniture category
    furniture_sales = df[df['Category'] == 'Furniture']['Sales'].sum()
    furniture_profit = df[df['Category'] == 'Furniture']['Profit'].sum()
    furniture_margin = furniture_profit / furniture_sales if furniture_sales != 0 else 0
    print(f"\nQ8. Profit Margin for Furniture Category: {furniture_margin:.4f} ({furniture_margin:.2%})")
    print(f"    Expected: {furniture_margin:.4f}")
    
    # Q9: Product with highest loss (lowest negative profit)
    min_profit = df['Profit'].min()
    if min_profit < 0:
        worst_product = df.loc[df['Profit'].idxmin(), 'Product Name']
        print(f"\nQ9. Product with Highest Loss: {worst_product} (${min_profit:,.2f})")
        print(f"    Expected: '{worst_product}'")
    else:
        print(f"\nQ9. Product with Highest Loss: No negative profits found")
        print(f"    Expected: None")
    
    # ========================================================================
    # LEVEL 3: Visualization Questions
    # ========================================================================
    print("\n" + "="*80)
    print("--- LEVEL 3: Visualization Questions ---\n")
    print("Note: These tests check for visualization creation, not specific values.")
    print("Expected: 'visualization_created' (boolean check)\n")
    
    print("Q1. Plot the monthly sales trend for the last 2 years of data.")
    print("    Expected: 'visualization_created'")
    
    print("\nQ2. Show me the distribution of discounts given. Are there any outliers?")
    print("    Expected: 'visualization_created'")
    
    print("\nQ3. Visualize the share of total sales contributed by each Segment (Consumer, Corporate, Home Office).")
    print("    Expected: 'visualization_created'")
    
    print("\nQ4. Is there a relationship between the discount amount and the profit?")
    print("    Expected: 'visualization_created'")
    
    # ========================================================================
    # SUMMARY FOR TEST CONFIGURATION
    # ========================================================================
    print("\n" + "="*80)
    print("SUMMARY - GROUND TRUTH VALUES:")
    print("="*80)
    print("\n# Level 1")
    print(f"Total Sales: {int(total_sales)}")
    print(f"Average Discount: {avg_discount:.3f}")
    print(f"Unique Orders: {unique_orders}")
    print(f"East Region Quantity: {east_quantity}")
    print(f"Technology Category Profit: {int(tech_profit)}")
    print(f"Unique Product Names: {unique_products}")
    print(f"Average Sales per Order: {int(avg_sales_per_order)}")
    if 'Order Date' in df.columns and df['Order Date'].notna().any():
        print(f"Earliest Order Date: '{earliest_date}'")
    print(f"State with Lowest Sales: '{lowest_state}'")
    print(f"Second Class Orders: {second_class_orders}")
    print(f"Maximum Discount: {max_discount:.3f}")
    print(f"Top 3 Sub-Categories: {top_subcats.index.tolist()}")
    
    print(f"\n# Level 2")
    if len(tech_df) > 0:
        print(f"Top 5 Tech Customers: {tech_customers.index.tolist()}")
    print(f"East-South Profit Difference: {int(profit_diff)}")
    print(f"Profit Margin by Category: {margins_dict}")
    if 'Order Date' in df.columns and df['Order Date'].notna().any():
        print(f"Consumer Segment Avg Profit ({most_recent_year}): {int(consumer_profit_avg)}")
    print(f"Customers with >10 Orders: {customers_10plus}")
    print(f"West Region Sales (No CA): {int(west_no_ca_sales)}")
    if 'Order Date' in df.columns and df['Order Date'].notna().any():
        print(f"Month with Highest Avg Sales: {best_month}")
    print(f"Furniture Profit Margin: {furniture_margin:.4f}")
    if min_profit < 0:
        print(f"Product with Highest Loss: '{worst_product}'")
    
    print(f"\n# Level 3")
    print("All visualization questions: Expected 'visualization_created'")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    import sys
    
    data_file = 'test_data/superstore.csv'
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    
    if not os.path.exists(data_file):
        print(f"❌ Error: Data file not found: {data_file}")
        print(f"Usage: python generate_ground_truth.py [path_to_superstore.csv]")
        sys.exit(1)
    
    generate_ground_truth(data_file)

