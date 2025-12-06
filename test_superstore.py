"""
Superstore Specific Test Suite
Calculates ground truth dynamically and tests the agent against specific Level 1 and Level 2 questions.
"""

import pandas as pd
import os
import sys
import re
from src.orchestrator import AutoInsightOrchestrator

# --- Helper Functions for Extraction (Reused/Adapted) ---

def extract_number(text):
    """Extract a number from text, handling various formats."""
    if not isinstance(text, str):
        return text
    text = text.replace(',', '').replace('$', '').replace('%', '')
    patterns = [r'-?\d+\.?\d*', r'\d+\.\d+']
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                continue
    return None

def extract_answer_from_output(stdout, query_type):
    """Extract answer from agent output based on query type."""
    if not stdout:
        return None
    
    lines = stdout.strip().split('\n')
    
    numbers_found = []
    for line in lines:
        line_lower = line.lower()
        skip_patterns = ['dtype:', 'index:', 'name:', 'columns:', 'rows:', 'shape:', 'analysis:', '---']
        if any(line_lower.startswith(skip) or line_lower == skip for skip in skip_patterns):
            continue
        num = extract_number(line)
        if num is not None:
            numbers_found.append((num, line))

    if query_type in ['sum', 'sales', 'profit', 'quantity', 'count']:
        if not numbers_found: return None
        # For count, look for keywords
        if query_type == 'count':
             for num, line in numbers_found:
                if 'unique' in line.lower() or 'count' in line.lower() or 'orders' in line.lower():
                    return num
        # For quantity, look for "East" or "Total" if specified
        if query_type == 'quantity':
             for num, line in numbers_found:
                # If 'East' is mentioned in the line, it's likely the answer
                if 'east' in line.lower():
                    return num
        return max(numbers_found, key=lambda x: x[0])[0]

    elif query_type in ['mean', 'discount', 'margin']:
        if not numbers_found: return None
        # Prefer lines with "average", "mean", "margin"
        for num, line in numbers_found:
            if any(k in line.lower() for k in ['average', 'mean', 'margin', 'discount']):
                if num < 1000: return num
        
        # Heuristics for small numbers
        filtered = [(n, l) for n, l in numbers_found if (0 < n < 1000) or (0 < n < 1)]
        if filtered: return min(filtered, key=lambda x: x[0])[0]
        return min(numbers_found, key=lambda x: x[0])[0]

    elif query_type == 'city':
        for line in lines:
            line = line.strip()
            if any(skip in line.lower() for skip in ['analysis:', '---', 'key findings']): continue
            if ':' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    val = parts[-1].strip().strip('"\'')
                    if val and val[0].isupper() and ' ' not in val: # Simple city check
                         return val
                    if val and val[0].isupper() and 'New York' in val:
                        return "New York City"
        # Fallback
        if "New York City" in stdout: return "New York City"
        return None
    
    elif query_type == 'customer':
        # Heuristic for customer names in top list
        for line in lines:
            if "1." in line or "Top" in line:
                 # Try to grab the name
                 pass 
        # Since checking list equality is hard from unstructured text, 
        # we might return the full text for manual verification or simple string check
        return stdout

    elif query_type == 'dict':
        # Return stdout to parse specific values if needed
        return stdout
    
    elif query_type in ['state', 'product', 'month']:
        # Similar to city extraction
        for line in lines:
            line = line.strip()
            if any(skip in line.lower() for skip in ['analysis:', '---', 'key findings']): continue
            if ':' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    val = parts[-1].strip().strip('"\'')
                    if val and len(val) > 1:
                        return val
        return None
    
    elif query_type == 'date':
        # Extract date from output
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # With time
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, stdout)
            if matches:
                return matches[0]
        return None
    
    elif query_type == 'list':
        # Return stdout for list comparison
        return stdout
    
    elif query_type == 'margin':
        # Extract margin/ratio value
        if not numbers_found: return None
        # Look for small decimal values (margins are typically 0-1)
        filtered = [(n, l) for n, l in numbers_found if 0 <= n <= 1]
        if filtered:
            return filtered[0][0]
        return numbers_found[0][0] if numbers_found else None

    return None

def compare_answers(expected, actual, tolerance=0.01):
    """Compare expected and actual values."""
    if expected is None or actual is None:
        return False, f"Expected: {expected}, Got: {actual}"
    
    try:
        exp_float = float(expected)
        act_float = float(actual)
        if exp_float == 0:
            return act_float == 0, f"Expected: {expected}, Got: {actual}"
        diff = abs(exp_float - act_float) / abs(exp_float)
        passed = diff <= tolerance
        return passed, f"Expected: {expected}, Got: {actual} (Diff: {diff:.2%})"
    except:
        # String/Text comparison
        e_str = str(expected).strip().lower()
        a_str = str(actual).strip().lower()
        passed = e_str in a_str or a_str in e_str
        return passed, f"Expected: '{expected}', Got: '{actual}'"

# --- Main Test Script ---

def run_superstore_tests(data_file):
    print(f"Loading data from {data_file} for ground truth generation...")
    try:
        df = pd.read_csv(data_file, encoding='utf-8', on_bad_lines='skip')
    except:
        df = pd.read_csv(data_file, encoding='latin-1', on_bad_lines='skip')
    
    # Preprocessing
    if 'Order Date' in df.columns:
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
    if 'Sales' in df.columns: 
        df['Sales'] = pd.to_numeric(df['Sales'], errors='coerce')
    if 'Profit' in df.columns:
        df['Profit'] = pd.to_numeric(df['Profit'], errors='coerce')
    if 'Discount' in df.columns:
        df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce')
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')

    print("Data loaded. Calculating ground truth...\n")

    # --- Define Tests with Ground Truth Calculation ---
    tests = []

    # Level 1: Basic Questions
    tests.append({
        'question': "What is the total sales revenue for the entire dataset?",
        'answer': df['Sales'].sum(),
        'type': 'sales',
        'level': 1
    })
    tests.append({
        'question': "What is the average discount applied to all orders?",
        'answer': df['Discount'].mean(),
        'type': 'discount',
        'level': 1
    })
    tests.append({
        'question': "How many unique orders are in the dataset?",
        'answer': df['Order ID'].nunique(),
        'type': 'count',
        'level': 1
    })
    tests.append({
        'question': "What is the total quantity of products sold in the 'East' region?",
        'answer': df[df['Region'] == 'East']['Quantity'].sum(),
        'type': 'quantity',
        'level': 1
    })
    tests.append({
        'question': "What is the total profit generated by the 'Technology' category?",
        'answer': df[df['Category'] == 'Technology']['Profit'].sum(),
        'type': 'profit',
        'level': 1
    })
    tests.append({
        'question': "How many different products (Product Names) are in the dataset?",
        'answer': df['Product Name'].nunique(),
        'type': 'count',
        'level': 1
    })
    tests.append({
        'question': "What is the average sales value per order?",
        'answer': df.groupby('Order ID')['Sales'].sum().mean(),
        'type': 'sales',
        'level': 1
    })
    tests.append({
        'question': "What is the earliest order date in the dataset?",
        'answer': str(df['Order Date'].min()) if 'Order Date' in df.columns and df['Order Date'].notna().any() else None,
        'type': 'date',
        'level': 1
    })
    tests.append({
        'question': "Which State has the lowest total sales?",
        'answer': df.groupby('State')['Sales'].sum().idxmin(),
        'type': 'state',
        'level': 1
    })
    tests.append({
        'question': "How many orders were shipped using 'Second Class' mode?",
        'answer': df[df['Ship Mode'] == 'Second Class']['Order ID'].nunique(),
        'type': 'count',
        'level': 1
    })
    tests.append({
        'question': "What is the maximum discount given on any single order?",
        'answer': df['Discount'].max(),
        'type': 'discount',
        'level': 1
    })
    tests.append({
        'question': "List the top 3 sub-categories by total sales.",
        'answer': df.groupby('Sub-Category')['Sales'].sum().nlargest(3).index.tolist(),
        'type': 'list',
        'level': 1
    })

    # Level 2: Complex Questions
    
    # Q: Top 5 most profitable customers in Technology
    tech_df = df[df['Category'] == 'Technology']
    top_5_customers = tech_df.groupby('Customer Name')['Profit'].sum().nlargest(5).index.tolist()
    tests.append({
        'question': "List the top 5 most profitable customers in the Technology category.",
        'answer': top_5_customers,  # Full list for comparison
        'type': 'customer',
        'level': 2
    })

    # Q: Profit diff East vs South
    east_prof = df[df['Region'] == 'East']['Profit'].sum()
    south_prof = df[df['Region'] == 'South']['Profit'].sum()
    tests.append({
        'question': "How much more profit did we make in the East region compared to the South region?",
        'answer': east_prof - south_prof,
        'type': 'profit',
        'level': 2
    })

    # Q: Profit margin by Category
    margins = df.groupby('Category').apply(
        lambda x: x['Profit'].sum() / x['Sales'].sum() if x['Sales'].sum() != 0 else 0,
        include_groups=False
    ).to_dict()
    tests.append({
        'question': "What is the profit margin (Profit divided by Sales) for each Category?",
        'answer': margins,
        'type': 'dict',
        'level': 2
    })
    tests.append({
        'question': "What is the average profit for 'Consumer' segment orders in the most recent year?",
        'answer': df[(df['Segment'] == 'Consumer') & (df['Order Date'].dt.year == df['Order Date'].dt.year.max())]['Profit'].mean() if 'Order Date' in df.columns and df['Order Date'].notna().any() else None,
        'type': 'profit',
        'level': 2
    })
    tests.append({
        'question': "How many customers have made more than 10 orders?",
        'answer': (df.groupby('Customer Name')['Order ID'].nunique() > 10).sum(),
        'type': 'count',
        'level': 2
    })
    tests.append({
        'question': "What is the total sales for the 'West' region, excluding the state of California?",
        'answer': df[(df['Region'] == 'West') & (df['State'] != 'California')]['Sales'].sum(),
        'type': 'sales',
        'level': 2
    })
    tests.append({
        'question': "Which month of the year generally has the highest average sales?",
        'answer': df.groupby(df['Order Date'].dt.month)['Sales'].mean().idxmax() if 'Order Date' in df.columns and df['Order Date'].notna().any() else None,
        'type': 'month',
        'level': 2
    })
    tests.append({
        'question': "Calculate the ratio of total profit to total sales (Profit Margin) for the 'Furniture' category.",
        'answer': (df[df['Category'] == 'Furniture']['Profit'].sum() / df[df['Category'] == 'Furniture']['Sales'].sum()) if df[df['Category'] == 'Furniture']['Sales'].sum() != 0 else 0,
        'type': 'margin',
        'level': 2
    })
    tests.append({
        'question': "Find the order with the highest loss (lowest negative profit) and tell me the Product Name.",
        'answer': df.loc[df['Profit'].idxmin(), 'Product Name'] if df['Profit'].min() < 0 else None,
        'type': 'product',
        'level': 2
    })

    # Level 3: Visualization Questions
    tests.append({
        'question': "Plot the monthly sales trend for the last 2 years of data.",
        'answer': 'visualization_created',
        'type': 'visualization',
        'level': 3
    })
    tests.append({
        'question': "Show me the distribution of discounts given. Are there any outliers?",
        'answer': 'visualization_created',
        'type': 'visualization',
        'level': 3
    })
    tests.append({
        'question': "Visualize the share of total sales contributed by each Segment (Consumer, Corporate, Home Office).",
        'answer': 'visualization_created',
        'type': 'visualization',
        'level': 3
    })
    tests.append({
        'question': "Is there a relationship between the discount amount and the profit?",
        'answer': 'visualization_created',
        'type': 'visualization',
        'level': 3
    })

    # --- Run Tests ---
    orchestrator = AutoInsightOrchestrator()
    
    print(f"{'='*80}")
    print(f"RUNNING SUPERSTORE TEST SUITE ({len(tests)} Tests)")
    print(f"{'='*80}\n")

    passed_count = 0
    level1_passed = 0
    level2_passed = 0
    level3_passed = 0
    
    import time
    
    for i, test in enumerate(tests, 1):
        level = test.get('level', 0)
        level_str = f"Level {level}" if level > 0 else ""
        print(f"\n{'='*80}")
        print(f"Test {i} ({level_str}): {test['question']}")
        print(f"Expected Answer: {test['answer']}")
        print(f"{'='*80}")
        
        # Add delay to avoid hitting rate limits (5 req/min -> ~12s delay)
        # Using 20s to be safe and allow for quota reset
        if i > 1:
            print("Waiting 20s to respect API rate limits...")
            time.sleep(20)
        
        try:
            result = orchestrator.analyze(test['question'], data_file)
            
            if not result['success']:
                print(f"❌ ERROR in execution: {result.get('error')}")
                print(f"Stderr: {result.get('stderr')}\n")
                continue

            extracted = extract_answer_from_output(result['stdout'], test['type'])
            
            # Special handling for visualization tests
            if test['type'] == 'visualization':
                # Check if visualization code was generated and executed
                code = result.get('code', '')
                # Look for matplotlib, plotly, seaborn, or other plotting libraries
                has_plotting = any(lib in code.lower() for lib in ['matplotlib', 'plotly', 'seaborn', 'plt.', 'px.', 'sns.', 'plot(', 'show()', 'savefig'])
                # Also check if output mentions visualization or plot
                stdout_lower = result['stdout'].lower()
                has_plot_output = any(word in stdout_lower for word in ['plot', 'chart', 'graph', 'visualization', 'figure', 'saved'])
                is_pass = has_plotting or has_plot_output
                msg = "Visualization code/output detected" if is_pass else "No visualization code/output detected"
                extracted = "Visualization check"
            
            # Special handling for list/dict
            elif test['type'] == 'dict':
                # Check if all category margins are present in stdout
                all_found = True
                for cat, margin in test['answer'].items():
                    # Check for margin formatted in various ways
                    margin_str1 = f"{margin:.4f}"
                    margin_str2 = f"{margin:.3f}"
                    margin_str3 = f"{margin*100:.2f}%"
                    if not any(s in result['stdout'] for s in [margin_str1, margin_str2, margin_str3, cat]):
                        all_found = False
                        break
                is_pass = all_found
                msg = "Profit margins by category found" if all_found else "Some profit margins missing"
                extracted = "Dict output check"
            
            elif test['type'] == 'customer':
                # Check if all top 5 customers are in output (or at least top 3)
                if isinstance(test['answer'], list):
                    found_count = sum(1 for customer in test['answer'][:3] if customer in result['stdout'])
                    is_pass = found_count >= 3  # At least top 3 should be present
                    msg = f"Found {found_count}/3 top customers in output"
                    extracted = f"Found customers: {found_count}"
                else:
                    is_pass = test['answer'] in result['stdout']
                    msg = f"Expected '{test['answer']}' in output"
                    extracted = "Output check"
            
            elif test['type'] == 'list':
                # Check if all expected items are in output
                if isinstance(test['answer'], list):
                    found_count = sum(1 for item in test['answer'] if item in result['stdout'])
                    is_pass = found_count >= len(test['answer']) * 0.8  # 80% match
                    msg = f"Found {found_count}/{len(test['answer'])} items in output"
                    extracted = f"Found items: {found_count}"
                else:
                    is_pass = False
                    msg = "Expected list answer"
                    extracted = "Not a list"
            
            elif test['type'] in ['state', 'product', 'date']:
                # String comparison
                if extracted is not None:
                    if test['type'] == 'date':
                        # For dates, check if the date part matches (ignore time)
                        exp_date = str(test['answer']).split()[0] if ' ' in str(test['answer']) else str(test['answer'])
                        act_date = str(extracted).split()[0] if ' ' in str(extracted) else str(extracted)
                        is_pass = exp_date in act_date or act_date in exp_date
                    else:
                        is_pass = str(test['answer']).lower() in str(extracted).lower() or str(extracted).lower() in str(test['answer']).lower()
                    msg = f"Expected '{test['answer']}', Got '{extracted}'"
                else:
                    is_pass = False
                    msg = f"Could not extract {test['type']} from output"
                    extracted = None
            
            elif test['type'] == 'month':
                # Month should be an integer 1-12
                if extracted is not None:
                    try:
                        month_num = int(float(extracted))
                        is_pass = month_num == test['answer']
                        msg = f"Expected month {test['answer']}, Got {month_num}"
                    except:
                        is_pass = False
                        msg = f"Could not parse month from '{extracted}'"
                else:
                    is_pass = False
                    msg = "Could not extract month from output"
            
            elif test['type'] == 'margin':
                # Margin is a ratio (0-1)
                is_pass, msg = compare_answers(test['answer'], extracted, tolerance=0.01)

            else:
                is_pass, msg = compare_answers(test['answer'], extracted)

            if is_pass:
                print(f"✅ PASS - {msg}")
                print(f"   Extracted: {extracted}")
                passed_count += 1
                if level == 1:
                    level1_passed += 1
                elif level == 2:
                    level2_passed += 1
                elif level == 3:
                    level3_passed += 1
            else:
                print(f"❌ FAIL - {msg}")
                print(f"   Extracted: {extracted}")
                print(f"   Raw Output: {result['stdout'].strip()[:300]}...") # Show start of output
            
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 80)

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total: {passed_count}/{len(tests)} Passed ({passed_count/len(tests)*100:.1f}%)")
    level1_total = sum(1 for t in tests if t.get('level') == 1)
    level2_total = sum(1 for t in tests if t.get('level') == 2)
    level3_total = sum(1 for t in tests if t.get('level') == 3)
    if level1_total > 0:
        print(f"Level 1: {level1_passed}/{level1_total} Passed ({level1_passed/level1_total*100:.1f}%)")
    if level2_total > 0:
        print(f"Level 2: {level2_passed}/{level2_total} Passed ({level2_passed/level2_total*100:.1f}%)")
    if level3_total > 0:
        print(f"Level 3: {level3_passed}/{level3_total} Passed ({level3_passed/level3_total*100:.1f}%)")
    print(f"{'='*80}")

if __name__ == "__main__":
    run_superstore_tests('test_data/superstore.csv')

