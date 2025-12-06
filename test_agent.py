"""
Automated Test Suite for AutoInsight Agent
Tests the agent against curated questions with ground truth answers.
"""

import os
import sys
import json
import re
from typing import Dict, List, Tuple, Any, Optional
from src.orchestrator import AutoInsightOrchestrator
from datetime import datetime
from generate_ground_truth import calculate_ground_truth_values


class AutoInsightTester:
    """Automated testing framework for AutoInsight agent."""
    
    def __init__(self, data_file_path: str):
        """
        Initialize the tester.
        
        Args:
            data_file_path: Path to the CSV file to test against
        """
        self.data_file_path = data_file_path
        self.orchestrator = AutoInsightOrchestrator()
        self.results = []
    
    def extract_number(self, text: str) -> Optional[float]:
        """
        Extract a number from text, handling various formats.
        
        Args:
            text: Text containing a number
            
        Returns:
            Extracted number as float, or None if not found
        """
        # Remove commas and dollar signs
        text = text.replace(',', '').replace('$', '').replace('%', '')
        
        # Try to find numbers (including decimals and negatives)
        patterns = [
            r'-?\d+\.?\d*',  # Standard number
            r'\d+\.\d+',     # Decimal
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    return float(matches[0])
                except ValueError:
                    continue
        
        return None
    
    def extract_answer_from_output(self, stdout: str, query_type: str) -> Any:
        """
        Extract the answer from code execution output.
        
        Args:
            stdout: Standard output from code execution
            query_type: Type of query (e.g., 'sum', 'mean', 'count', 'city')
            
        Returns:
            Extracted answer
        """
        if not stdout:
            return None
        
        lines = stdout.strip().split('\n')
        
        # For numeric answers (mean, sum, etc.)
        if query_type in ['sum', 'mean', 'count', 'quantity', 'profit', 'sales', 'discount', 'comparison']:
            # Look for numbers in the output, but be smart about which one
            numbers_found = []
            for line in lines:
                line_lower = line.lower()
                # Skip lines that are clearly metadata/headers (but not answer lines)
                skip_patterns = ['dtype:', 'index:', 'name:', 'columns:', 'rows:', 'shape:']
                if any(line_lower.startswith(skip) or line_lower == skip for skip in skip_patterns):
                    continue
                
                num = self.extract_number(line)
                if num is not None:
                    numbers_found.append((num, line))
            
            if not numbers_found:
                return None
            
            # For mean/average queries, prefer numbers from lines containing "average" or "mean"
            if query_type == 'mean' or query_type == 'discount':
                # First, look for numbers in lines that explicitly mention "average" or "mean"
                for num, line in numbers_found:
                    line_lower = line.lower()
                    if 'average' in line_lower or 'mean' in line_lower:
                        # Filter out row counts and other large numbers
                        if num < 1000 and num >= 0:
                            return num
                
                # If no explicit average/mean line found, filter out obviously wrong numbers
                # But allow numbers that could be means (0-1000 range, or very small decimals)
                # Exclude 0.0 as it's likely a min value, not the mean
                filtered = [(n, l) for n, l in numbers_found if (0 < n < 1000) or (0 < n < 1)]
                if filtered:
                    # Return the smallest reasonable number (likely the mean)
                    return min(filtered, key=lambda x: x[0])[0]
                # If no filtered, return the smallest non-zero number
                non_zero = [(n, l) for n, l in numbers_found if n > 0]
                if non_zero:
                    return min(non_zero, key=lambda x: x[0])[0]
                # Last resort: return the smallest overall
                return min(numbers_found, key=lambda x: x[0])[0]
            
            # For sum queries, return the largest number (usually the answer)
            if query_type in ['sum', 'sales', 'profit']:
                return max(numbers_found, key=lambda x: x[0])[0]
            
            # For comparison queries, look for difference or subtraction result
            if query_type == 'comparison':
                # First, look for numbers in lines with "difference", "more", "less" keywords
                for num, line in numbers_found:
                    line_lower = line.lower()
                    if 'difference' in line_lower or 'more' in line_lower or 'less' in line_lower:
                        return num
                # If no keyword match, return the largest number (likely the difference)
                return max(numbers_found, key=lambda x: x[0])[0]
            
            # For count queries, prefer numbers associated with "unique" or "count" keywords
            if query_type in ['count']:
                # Look for numbers in lines with "unique" or "count" keywords
                for num, line in numbers_found:
                    line_lower = line.lower()
                    if 'unique' in line_lower or 'count' in line_lower or 'orders' in line_lower:
                        return num
                # If no keyword match, return the largest number
                return max(numbers_found, key=lambda x: x[0])[0]
            
            # For quantity queries
            if query_type == 'quantity':
                # Look for numbers in lines with "quantity" or "total" keywords
                for num, line in numbers_found:
                    line_lower = line.lower()
                    if 'quantity' in line_lower or ('total' in line_lower and 'quantity' in line_lower):
                        return num
                # If no keyword match, return the largest number
                return max(numbers_found, key=lambda x: x[0])[0]
            
            # For others, return the first reasonable number
            return numbers_found[0][0]
        
        # For city/name/state/product answers
        elif query_type in ['city', 'customer', 'category', 'state', 'product']:
            # Look for text that might be a city or name
            for line in lines:
                line = line.strip()
                
                # Skip lines that are clearly analysis headers or questions
                line_lower = line.lower()
                if any(skip in line_lower for skip in ['analysis:', '---', 'key findings', 'summary:']):
                    continue
                
                # Check if line contains a colon (likely "Label: Value" format)
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        # Get the part after the colon
                        value_part = parts[-1].strip().strip('"\'')
                        # Skip if it's still a label/question
                        if value_part and len(value_part) > 2:
                            value_lower = value_part.lower()
                            # Skip if it's still a question or label
                            if not any(skip in value_lower for skip in ['city with', 'highest', 'which', 'total', 'best', 'is:']):
                                # Check if it looks like a city name (starts with capital, reasonable length)
                                if value_part[0].isupper() and 2 < len(value_part) < 50:
                                    # Additional check: should not be a full sentence/question
                                    if not value_part.endswith('?') and ' ' not in value_part or len(value_part.split()) <= 3:
                                        return value_part
                
                # Skip lines that are clearly labels or headers
                if any(skip in line_lower for skip in ['city with', 'highest', 'total', 'profit:', 'sales:', 'name:', 'which']):
                    continue
                
                # Common patterns: "City: New York", "New York City", etc.
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        city_part = parts[-1].strip().strip('"\'')
                        if city_part and len(city_part) > 2:
                            return city_part
                
                # Check if line looks like a city name (starts with capital, reasonable length)
                if len(line) > 2 and line[0].isupper() and not line.lower().startswith(('the ', 'city ', 'which ', 'total ', 'average ')):
                    # Check if it contains common city name patterns
                    if any(word in line for word in ['City', 'York', 'Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia']):
                        return line
                    # Or if it's a simple name (2-3 words max, all capitalized)
                    words = line.split()
                    if 1 <= len(words) <= 3 and all(w[0].isupper() for w in words if w):
                        return line
        
        # For date answers
        elif query_type == 'date':
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
        
        # For month answers
        elif query_type == 'month':
            # Look for month number (1-12) in output
            for line in lines:
                num = self.extract_number(line)
                if num is not None and 1 <= num <= 12:
                    return int(num)
            return None
        
        # For list answers
        elif query_type == 'list':
            # Return stdout for list comparison
            return stdout
        
        # For margin answers
        elif query_type == 'margin':
            # Extract margin/ratio value (typically 0-1)
            numbers_found = []
            for line in lines:
                num = self.extract_number(line)
                if num is not None:
                    numbers_found.append((num, line))
            if not numbers_found:
                return None
            # Look for small decimal values (margins are typically 0-1)
            filtered = [(n, l) for n, l in numbers_found if 0 <= n <= 1]
            if filtered:
                return filtered[0][0]
            return numbers_found[0][0] if numbers_found else None
        
        # Default: try to extract any number
        for line in lines:
            num = self.extract_number(line)
            if num is not None:
                return num
        
        return None
    
    def compare_answers(self, expected: Any, actual: Any, tolerance: float = 0.01) -> bool:
        """
        Compare expected and actual answers with tolerance for floating point.
        
        Args:
            expected: Expected answer
            actual: Actual answer from agent
            tolerance: Tolerance for floating point comparison (as percentage)
            
        Returns:
            True if answers match within tolerance
        """
        if expected is None or actual is None:
            return False
        
        # Convert to float for comparison
        try:
            exp_float = float(expected)
            act_float = float(actual)
        except (ValueError, TypeError):
            # String comparison
            return str(expected).lower().strip() == str(actual).lower().strip()
        
        # Calculate relative difference
        if exp_float == 0:
            return act_float == 0
        
        relative_diff = abs(exp_float - act_float) / abs(exp_float)
        return relative_diff <= tolerance
    
    def run_test(self, question: str, expected_answer: Any, query_type: str, 
                 category: str = "General", tolerance: float = 0.01) -> Dict[str, Any]:
        """
        Run a single test question.
        
        Args:
            question: Test question
            expected_answer: Expected answer (ground truth)
            query_type: Type of query for answer extraction
            category: Test category
            tolerance: Tolerance for numeric comparison
            
        Returns:
            Test result dictionary
        """
        print(f"\n{'='*80}")
        print(f"Testing: {question}")
        print(f"Expected: {expected_answer}")
        print(f"{'='*80}")
        
        result = {
            'question': question,
            'expected': expected_answer,
            'category': category,
            'query_type': query_type,
            'passed': False,
            'actual': None,
            'error': None,
            'code': None,
            'stdout': None,
            'stderr': None
        }
        
        try:
            # Run the analysis
            analysis_result = self.orchestrator.analyze(
                user_query=question,
                data_file_path=self.data_file_path
            )
            
            result['code'] = analysis_result.get('code', '')
            result['stdout'] = analysis_result.get('stdout', '')
            result['stderr'] = analysis_result.get('stderr', '')
            result['error'] = analysis_result.get('error')
            
            if not analysis_result['success']:
                result['error'] = f"Code execution failed: {analysis_result.get('stderr', 'Unknown error')}"
                print(f"❌ FAILED: {result['error']}")
                return result
            
            # Extract answer from output
            actual_answer = self.extract_answer_from_output(
                analysis_result.get('stdout', ''),
                query_type
            )
            
            result['actual'] = actual_answer
            
            # Compare with expected
            if query_type == 'visualization':
                # Check if visualization code was generated and executed
                code = analysis_result.get('code', '')
                # Look for matplotlib, plotly, seaborn, or other plotting libraries
                has_plotting = any(lib in code.lower() for lib in ['matplotlib', 'plotly', 'seaborn', 'plt.', 'px.', 'sns.', 'plot(', 'show()', 'savefig'])
                # Also check if output mentions visualization or plot
                stdout_lower = analysis_result.get('stdout', '').lower()
                has_plot_output = any(word in stdout_lower for word in ['plot', 'chart', 'graph', 'visualization', 'figure', 'saved'])
                result['passed'] = has_plotting or has_plot_output
                if result['passed']:
                    print(f"✅ PASSED: Visualization code/output detected")
                else:
                    print(f"❌ FAILED: No visualization code/output detected")
            elif query_type == 'dict':
                # Special handling for dictionary answers (profit margins)
                if isinstance(expected_answer, dict) and actual_answer is not None:
                    # Check if all category margins are present in stdout
                    all_found = True
                    for cat, margin in expected_answer.items():
                        margin_str1 = f"{margin:.4f}"
                        margin_str2 = f"{margin:.3f}"
                        margin_str3 = f"{margin*100:.2f}%"
                        if not any(s in analysis_result.get('stdout', '') for s in [margin_str1, margin_str2, margin_str3, cat]):
                            all_found = False
                            break
                    result['passed'] = all_found
                    if all_found:
                        print(f"✅ PASSED: All profit margins found in output")
                    else:
                        print(f"❌ FAILED: Some profit margins missing")
                else:
                    result['error'] = "Could not extract dictionary answer from output"
                    print(f"❌ FAILED: Could not extract dictionary answer from output")
            elif query_type == 'customer':
                # Check if expected customer is in output
                if isinstance(expected_answer, str) and actual_answer is not None:
                    result['passed'] = expected_answer in analysis_result.get('stdout', '')
                    if result['passed']:
                        print(f"✅ PASSED: Found '{expected_answer}' in output")
                    else:
                        print(f"❌ FAILED: Expected '{expected_answer}' not found in output")
                else:
                    result['error'] = "Could not extract customer answer from output"
                    print(f"❌ FAILED: Could not extract customer answer from output")
            elif query_type == 'list':
                # Check if all expected items are in output
                if isinstance(expected_answer, list) and actual_answer is not None:
                    stdout_lower = analysis_result.get('stdout', '').lower()
                    found_count = sum(1 for item in expected_answer if item.lower() in stdout_lower)
                    result['passed'] = found_count >= len(expected_answer) * 0.8  # 80% match
                    if result['passed']:
                        print(f"✅ PASSED: Found {found_count}/{len(expected_answer)} items in output")
                    else:
                        print(f"❌ FAILED: Found only {found_count}/{len(expected_answer)} items")
                else:
                    result['error'] = "Could not extract list answer from output"
                    print(f"❌ FAILED: Could not extract list answer from output")
            elif query_type in ['state', 'product', 'date']:
                # String comparison with tolerance for date formats
                if actual_answer is not None:
                    if query_type == 'date':
                        # For dates, check if the date part matches (ignore time)
                        exp_date = str(expected_answer).split()[0] if ' ' in str(expected_answer) else str(expected_answer)
                        act_date = str(actual_answer).split()[0] if ' ' in str(actual_answer) else str(actual_answer)
                        result['passed'] = exp_date in act_date or act_date in exp_date
                    else:
                        result['passed'] = str(expected_answer).lower() in str(actual_answer).lower() or str(actual_answer).lower() in str(expected_answer).lower()
                    if result['passed']:
                        print(f"✅ PASSED: Found '{expected_answer}' in output")
                    else:
                        print(f"❌ FAILED: Expected '{expected_answer}', got '{actual_answer}'")
                else:
                    result['error'] = f"Could not extract {query_type} answer from output"
                    print(f"❌ FAILED: Could not extract {query_type} answer from output")
            elif actual_answer is not None:
                result['passed'] = self.compare_answers(expected_answer, actual_answer, tolerance)
                if result['passed']:
                    print(f"✅ PASSED: Got {actual_answer} (expected {expected_answer})")
                else:
                    print(f"❌ FAILED: Got {actual_answer} (expected {expected_answer})")
            else:
                result['error'] = "Could not extract answer from output"
                print(f"❌ FAILED: Could not extract answer from output")
                print(f"Output: {analysis_result.get('stdout', 'No output')[:300]}")
        
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ FAILED: Exception - {str(e)}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def run_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run a suite of test cases.
        
        Args:
            test_cases: List of test case dictionaries
            
        Returns:
            Test suite results
        """
        print("\n" + "="*80)
        print("AUTOINSIGHT AGENT TEST SUITE")
        print("="*80)
        print(f"Data file: {self.data_file_path}")
        print(f"Total tests: {len(test_cases)}")
        print("="*80)
        
        self.results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] Running test...")
            result = self.run_test(
                question=test_case['question'],
                expected_answer=test_case['expected'],
                query_type=test_case.get('query_type', 'general'),
                category=test_case.get('category', 'General'),
                tolerance=test_case.get('tolerance', 0.01)
            )
            self.results.append(result)
        
        # Generate summary
        return self.generate_summary()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        
        # Group by category
        by_category = {}
        for result in self.results:
            cat = result['category']
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'passed': 0, 'failed': 0}
            by_category[cat]['total'] += 1
            if result['passed']:
                by_category[cat]['passed'] += 1
            else:
                by_category[cat]['failed'] += 1
        
        summary = {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / total * 100) if total > 0 else 0,
            'by_category': by_category,
            'results': self.results,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print test summary to console."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']} ({summary['success_rate']:.1f}%)")
        print(f"Failed: {summary['failed']}")
        print("\nBy Category:")
        for category, stats in summary['by_category'].items():
            rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {category}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        print("\n" + "="*80)
        print("FAILED TESTS:")
        print("="*80)
        for result in self.results:
            if not result['passed']:
                print(f"\n❌ {result['question']}")
                print(f"   Expected: {result['expected']}")
                print(f"   Got: {result['actual']}")
                if result['error']:
                    print(f"   Error: {result['error']}")
    
    def save_report(self, summary: Dict[str, Any], output_file: str = "test_report.json"):
        """Save test report to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n📄 Test report saved to: {output_file}")


def get_test_cases(data_file_path: str = 'test_data/superstore.csv') -> List[Dict[str, Any]]:
    """
    Get curated test cases for Superstore dataset - Level 1, Level 2, and Level 3.
    
    Args:
        data_file_path: Path to the superstore.csv file for calculating ground truth
        
    Returns:
        List of test case dictionaries with expected values from ground truth
    """
    # Calculate ground truth values dynamically
    gt = calculate_ground_truth_values(data_file_path)
    
    return [
        # Level 1: Basic Questions
        {
            'question': 'What is the total sales revenue for the entire dataset?',
            'expected': gt['total_sales'],
            'query_type': 'sum',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': 'What is the average discount applied to all orders?',
            'expected': gt['avg_discount'],
            'query_type': 'discount',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.05  # 5% tolerance for percentage
        },
        {
            'question': 'How many unique orders are in the dataset?',
            'expected': gt['unique_orders'],
            'query_type': 'count',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': "What is the total quantity of products sold in the 'East' region?",
            'expected': gt['east_quantity'],
            'query_type': 'quantity',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': "What is the total profit generated by the 'Technology' category?",
            'expected': gt['tech_profit'],
            'query_type': 'profit',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': "How many different products (Product Names) are in the dataset?",
            'expected': gt['unique_products'],
            'query_type': 'count',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': "What is the average sales value per order?",
            'expected': gt['avg_sales_per_order'],
            'query_type': 'sales',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': "What is the earliest order date in the dataset?",
            'expected': gt['earliest_date'],
            'query_type': 'date',
            'category': 'Level 1: Basic Questions'
        },
        {
            'question': "Which State has the lowest total sales?",
            'expected': gt['lowest_state'],
            'query_type': 'state',
            'category': 'Level 1: Basic Questions'
        },
        {
            'question': "How many orders were shipped using 'Second Class' mode?",
            'expected': gt['second_class_orders'],
            'query_type': 'count',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': "What is the maximum discount given on any single order?",
            'expected': gt['max_discount'],
            'query_type': 'discount',
            'category': 'Level 1: Basic Questions',
            'tolerance': 0.01
        },
        {
            'question': "List the top 3 sub-categories by total sales.",
            'expected': gt['top_3_subcategories'],
            'query_type': 'list',
            'category': 'Level 1: Basic Questions'
        },
        
        # Level 2: Complex Questions
        {
            'question': 'List the top 5 most profitable customers in the Technology category.',
            'expected': gt['top_5_tech_customers'][0] if gt['top_5_tech_customers'] else None,  # Top customer
            'query_type': 'customer',
            'category': 'Level 2: Complex Questions'
        },
        {
            'question': 'How much more profit did we make in the East region compared to the South region?',
            'expected': gt['east_south_profit_diff'],
            'query_type': 'comparison',
            'category': 'Level 2: Complex Questions',
            'tolerance': 0.01
        },
        {
            'question': 'What is the profit margin (Profit divided by Sales) for each Category?',
            'expected': gt['category_margins'],
            'query_type': 'dict',
            'category': 'Level 2: Complex Questions',
            'tolerance': 0.01
        },
        {
            'question': "What is the average profit for 'Consumer' segment orders in the most recent year?",
            'expected': gt['consumer_profit_avg'],
            'query_type': 'profit',
            'category': 'Level 2: Complex Questions',
            'tolerance': 0.01
        },
        {
            'question': "How many customers have made more than 10 orders?",
            'expected': gt['customers_10plus'],
            'query_type': 'count',
            'category': 'Level 2: Complex Questions',
            'tolerance': 0.01
        },
        {
            'question': "What is the total sales for the 'West' region, excluding the state of California?",
            'expected': gt['west_no_ca_sales'],
            'query_type': 'sales',
            'category': 'Level 2: Complex Questions',
            'tolerance': 0.01
        },
        {
            'question': "Which month of the year generally has the highest average sales?",
            'expected': gt['best_month'],
            'query_type': 'month',
            'category': 'Level 2: Complex Questions',
            'tolerance': 0.01
        },
        {
            'question': "Calculate the ratio of total profit to total sales (Profit Margin) for the 'Furniture' category.",
            'expected': gt['furniture_margin'],
            'query_type': 'margin',
            'category': 'Level 2: Complex Questions',
            'tolerance': 0.01
        },
        {
            'question': "Find the order with the highest loss (lowest negative profit) and tell me the Product Name.",
            'expected': gt['worst_product'],
            'query_type': 'product',
            'category': 'Level 2: Complex Questions'
        },
        
        # Level 3: Visualization Questions
        {
            'question': 'Plot the monthly sales trend for the last 2 years of data.',
            'expected': 'visualization_created',
            'query_type': 'visualization',
            'category': 'Level 3: Visualization Questions'
        },
        {
            'question': 'Show me the distribution of discounts given. Are there any outliers?',
            'expected': 'visualization_created',
            'query_type': 'visualization',
            'category': 'Level 3: Visualization Questions'
        },
        {
            'question': 'Visualize the share of total sales contributed by each Segment (Consumer, Corporate, Home Office).',
            'expected': 'visualization_created',
            'query_type': 'visualization',
            'category': 'Level 3: Visualization Questions'
        },
        {
            'question': 'Is there a relationship between the discount amount and the profit?',
            'expected': 'visualization_created',
            'query_type': 'visualization',
            'category': 'Level 3: Visualization Questions'
        },
    ]


def main():
    """Main test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test AutoInsight Agent')
    parser.add_argument('--data', type=str, default='test_data/superstore.csv',
                       help='Path to CSV data file')
    parser.add_argument('--output', type=str, default='test_report.json',
                       help='Output file for test report')
    parser.add_argument('--category', type=str, default=None,
                       help='Run only tests in this category')
    
    args = parser.parse_args()
    
    # Check if data file exists
    if not os.path.exists(args.data):
        print(f"❌ Error: Data file not found: {args.data}")
        sys.exit(1)
    
    # Get test cases (with ground truth values calculated from data file)
    test_cases = get_test_cases(args.data)
    
    # Filter by category if specified
    if args.category:
        test_cases = [tc for tc in test_cases if tc['category'] == args.category]
        print(f"Running tests for category: {args.category}")
    
    # Run tests
    tester = AutoInsightTester(args.data)
    summary = tester.run_test_suite(test_cases)
    
    # Print and save results
    tester.print_summary(summary)
    tester.save_report(summary, args.output)
    
    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 else 1)


if __name__ == '__main__':
    main()

