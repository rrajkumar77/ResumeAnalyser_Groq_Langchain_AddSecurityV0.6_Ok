"""
Coding Interview Questions Generator
====================================

Generates practical coding challenges based on JD requirements with:
- Working solutions
- Test cases
- Time/space complexity analysis
- Common mistakes to watch for
- Hints for struggling candidates
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class DifficultyLevel(Enum):
    """Coding question difficulty."""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


@dataclass
class CodingQuestion:
    """Coding interview question with solution."""
    title: str
    skill_area: str
    difficulty: DifficultyLevel
    problem_statement: str
    input_format: str
    output_format: str
    examples: List[Dict[str, str]]
    constraints: List[str]
    solution_code: str
    solution_explanation: str
    time_complexity: str
    space_complexity: str
    test_cases: List[Dict]
    common_mistakes: List[str]
    hints: List[str]
    
    def format_for_candidate(self) -> str:
        """Format question for candidate (without solution)."""
        output = f"""
{'='*80}
{self.title}
{'='*80}
Difficulty: {self.difficulty.value} | Skill: {self.skill_area}

PROBLEM:
{self.problem_statement}

{'─'*80}
INPUT FORMAT:
{self.input_format}

OUTPUT FORMAT:
{self.output_format}

{'─'*80}
EXAMPLES:

{chr(10).join(
    f"Example {i+1}:\\n"
    f"Input: {ex['input']}\\n"
    f"Output: {ex['output']}\\n"
    f"{('Explanation: ' + ex.get('explanation', '')) if ex.get('explanation') else ''}"
    for i, ex in enumerate(self.examples)
)}

{'─'*80}
CONSTRAINTS:
{chr(10).join(f'  • {c}' for c in self.constraints)}

{'='*80}
"""
        return output
    
    def format_solution(self) -> str:
        """Format solution for interviewer."""
        output = f"""
{'='*80}
SOLUTION - {self.title}
{'='*80}

CODE SOLUTION:
```python
{self.solution_code}
```

{'─'*80}
EXPLANATION:
{self.solution_explanation}

{'─'*80}
COMPLEXITY ANALYSIS:
Time Complexity: {self.time_complexity}
Space Complexity: {self.space_complexity}

{'─'*80}
TEST CASES:
{chr(10).join(
    f"Test {i+1}: {tc.get('description', '')}\\n"
    f"Input: {tc['input']}\\n"
    f"Expected Output: {tc['output']}"
    for i, tc in enumerate(self.test_cases)
)}

{'─'*80}
COMMON MISTAKES TO WATCH FOR:
{chr(10).join(f'  ⚠️  {mistake}' for mistake in self.common_mistakes)}

{'─'*80}
HINTS (if candidate is stuck):
{chr(10).join(f'  💡 Hint {i+1}: {hint}' for i, hint in enumerate(self.hints))}

{'='*80}
"""
        return output


class CodingQuestionGenerator:
    """
    Generates coding questions based on JD skills.
    """
    
    # Coding question bank by skill
    QUESTIONS = {
        "python": [
            {
                "title": "Parse and Transform CSV Data",
                "difficulty": DifficultyLevel.MEDIUM,
                "problem_statement": """
You're given a CSV string representing employee records. Each record has:
name, department, salary, join_date (YYYY-MM-DD format).

Write a function that:
1. Parses the CSV data
2. Filters employees who joined in the last 2 years
3. Groups by department
4. Returns average salary per department, sorted by salary (descending)
5. Handles edge cases (empty data, malformed dates, invalid salaries)
""",
                "input_format": "csv_data: str (CSV format with headers)",
                "output_format": "Dict[str, float] (department -> avg_salary)",
                "examples": [
                    {
                        "input": '''name,department,salary,join_date
John,Engineering,120000,2023-01-15
Jane,Engineering,110000,2022-06-20
Bob,Marketing,80000,2020-03-10
Alice,Marketing,85000,2024-01-05''',
                        "output": "{'Engineering': 115000.0, 'Marketing': 85000.0}",
                        "explanation": "Bob filtered out (joined >2 years ago). Engineering avg: (120000+110000)/2=115000"
                    }
                ],
                "constraints": [
                    "CSV is well-formed (proper headers, commas)",
                    "Dates in YYYY-MM-DD format",
                    "Salary is a valid positive integer",
                    "Handle empty CSV gracefully"
                ],
                "solution_code": """from datetime import datetime, timedelta
from collections import defaultdict
import csv
from io import StringIO

def analyze_employees(csv_data: str) -> dict:
    if not csv_data.strip():
        return {}
    
    # Parse CSV
    reader = csv.DictReader(StringIO(csv_data))
    
    # Calculate cutoff date (2 years ago from today)
    cutoff_date = datetime.now() - timedelta(days=730)
    
    # Group by department
    dept_salaries = defaultdict(list)
    
    for row in reader:
        try:
            # Parse join date
            join_date = datetime.strptime(row['join_date'], '%Y-%m-%d')
            
            # Filter: only employees who joined in last 2 years
            if join_date >= cutoff_date:
                dept = row['department']
                salary = float(row['salary'])
                dept_salaries[dept].append(salary)
        except (ValueError, KeyError):
            # Skip malformed rows
            continue
    
    # Calculate average per department
    avg_salaries = {
        dept: sum(salaries) / len(salaries)
        for dept, salaries in dept_salaries.items()
    }
    
    # Sort by salary descending
    return dict(sorted(avg_salaries.items(), 
                      key=lambda x: x[1], 
                      reverse=True))
""",
                "solution_explanation": """
Key steps:
1. Use csv.DictReader for parsing (handles quotes, commas in values)
2. Calculate cutoff date dynamically (today - 2 years)
3. Try-except for error handling (malformed dates, invalid salaries)
4. defaultdict(list) for grouping by department
5. Dictionary comprehension for calculating averages
6. sorted() with key and reverse for descending order
""",
                "time_complexity": "O(n log n) where n is number of employees (sorting dominates)",
                "space_complexity": "O(n) for storing department salary lists",
                "test_cases": [
                    {
                        "description": "Empty CSV",
                        "input": "''",
                        "output": "{}"
                    },
                    {
                        "description": "All employees filtered out (>2 years old)",
                        "input": "name,department,salary,join_date\nJohn,Eng,100000,2020-01-01",
                        "output": "{}"
                    },
                    {
                        "description": "Malformed date (skip row)",
                        "input": "name,department,salary,join_date\nJohn,Eng,100000,invalid-date\nJane,Eng,110000,2024-01-01",
                        "output": "{'Eng': 110000.0}"
                    }
                ],
                "common_mistakes": [
                    "Doesn't handle malformed dates (crashes on ValueError)",
                    "Hardcodes cutoff date instead of calculating dynamically",
                    "Doesn't sort results",
                    "Uses split(',') instead of csv module (breaks on quoted values)",
                    "Doesn't filter by join date at all"
                ],
                "hints": [
                    "Use csv.DictReader for robust CSV parsing",
                    "datetime.strptime() for parsing dates",
                    "defaultdict(list) is great for grouping",
                    "Don't forget to sort the final results!"
                ]
            },
            {
                "title": "Database Query Result Deduplication",
                "difficulty": DifficultyLevel.EASY,
                "problem_statement": """
You're querying a database that returns duplicate records due to a JOIN bug.
Write a function to deduplicate records based on a unique 'id' field,
keeping the record with the most recent 'timestamp'.

Each record is a dictionary with: id, name, timestamp, value
""",
                "input_format": "records: List[Dict] - list of record dictionaries",
                "output_format": "List[Dict] - deduplicated records",
                "examples": [
                    {
                        "input": "[{'id': 1, 'name': 'A', 'timestamp': '2024-01-01', 'value': 100}, {'id': 1, 'name': 'A', 'timestamp': '2024-01-02', 'value': 200}]",
                        "output": "[{'id': 1, 'name': 'A', 'timestamp': '2024-01-02', 'value': 200}]",
                        "explanation": "Keep the record with id=1 and latest timestamp (2024-01-02)"
                    }
                ],
                "constraints": [
                    "id is always present and is an integer",
                    "timestamp is in YYYY-MM-DD format",
                    "At least one record in input"
                ],
                "solution_code": """def deduplicate_records(records):
    # Dictionary to track latest record per ID
    latest = {}
    
    for record in records:
        record_id = record['id']
        timestamp = record['timestamp']
        
        # If ID not seen or this timestamp is newer
        if record_id not in latest or timestamp > latest[record_id]['timestamp']:
            latest[record_id] = record
    
    return list(latest.values())
""",
                "solution_explanation": """
Simple approach using dictionary:
1. Iterate through all records
2. For each record, check if we've seen this ID before
3. If not seen, or if current timestamp is newer, update
4. String comparison works for YYYY-MM-DD format ('2024-01-02' > '2024-01-01')
5. Return all values from dictionary
""",
                "time_complexity": "O(n) where n is number of records",
                "space_complexity": "O(k) where k is number of unique IDs",
                "test_cases": [
                    {"input": "[]", "output": "[]"},
                    {"input": "[{'id': 1, 'timestamp': '2024-01-01', 'value': 100}]", "output": "[{'id': 1, 'timestamp': '2024-01-01', 'value': 100}]"},
                    {"input": "[{'id': 1, 'timestamp': '2024-01-01', 'value': 100}, {'id': 2, 'timestamp': '2024-01-01', 'value': 200}]", "output": "2 records (different IDs)"}
                ],
                "common_mistakes": [
                    "Sorts all records (O(n log n) when O(n) is sufficient)",
                    "Doesn't handle empty list",
                    "Compares timestamps as strings incorrectly",
                    "Uses list instead of dict (O(n²) lookups)"
                ],
                "hints": [
                    "Dictionary is perfect for tracking 'latest' by ID",
                    "String comparison works for YYYY-MM-DD format",
                    "One pass through the data is enough"
                ]
            }
        ],
        
        "sql": [
            {
                "title": "Write SQL Query for Sales Analysis",
                "difficulty": DifficultyLevel.MEDIUM,
                "problem_statement": """
Given three tables:
- customers (id, name, region)
- orders (id, customer_id, order_date, total_amount)
- products (id, order_id, product_name, quantity, unit_price)

Write a SQL query to find:
- Top 5 customers by total revenue in the last 30 days
- Include: customer name, region, total revenue, number of orders
- Order by total revenue descending
""",
                "input_format": "Three tables as described above",
                "output_format": "Table with columns: name, region, total_revenue, order_count",
                "examples": [
                    {
                        "input": "See table schemas above",
                        "output": "name | region | total_revenue | order_count\nJohn | West  | 15000        | 5",
                        "explanation": "Top customer by revenue in last 30 days"
                    }
                ],
                "constraints": [
                    "Use window functions if needed",
                    "Date comparison for 'last 30 days'",
                    "Handle NULL values appropriately"
                ],
                "solution_code": """SELECT 
    c.name,
    c.region,
    SUM(o.total_amount) as total_revenue,
    COUNT(DISTINCT o.id) as order_count
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.id, c.name, c.region
ORDER BY total_revenue DESC
LIMIT 5;
""",
                "solution_explanation": """
Key points:
1. JOIN customers and orders on customer_id
2. Filter orders from last 30 days using date arithmetic
3. GROUP BY customer (include all SELECT non-aggregated columns)
4. SUM for total revenue, COUNT DISTINCT for number of orders
5. ORDER BY revenue descending
6. LIMIT 5 for top 5
""",
                "time_complexity": "O(n log n) - depends on indexes and data volume",
                "space_complexity": "O(1) - query execution",
                "test_cases": [
                    {"description": "No orders in last 30 days", "output": "Empty result set"},
                    {"description": "Less than 5 customers", "output": "Return all customers"},
                    {"description": "Ties in revenue", "output": "Arbitrary order among ties"}
                ],
                "common_mistakes": [
                    "Forgets to filter by last 30 days",
                    "Doesn't GROUP BY all non-aggregated columns",
                    "Uses COUNT(*) instead of COUNT(DISTINCT o.id)",
                    "Forgets LIMIT 5",
                    "Joins products table unnecessarily (not needed for this query)"
                ],
                "hints": [
                    "CURRENT_DATE - INTERVAL '30 days' for date filtering",
                    "Don't forget to GROUP BY customer attributes",
                    "Use DISTINCT in COUNT to avoid duplicate order counting"
                ]
            }
        ],
        
        "aws": [
            {
                "title": "Design S3 Event Processing Lambda",
                "difficulty": DifficultyLevel.MEDIUM,
                "problem_statement": """
Write a Python Lambda function that:
1. Triggers on S3 file upload
2. Reads CSV file from S3
3. Validates data (skip invalid rows)
4. Writes valid records to DynamoDB
5. Sends email notification with summary (using SES)

Requirements:
- Handle large files (streaming, not loading all in memory)
- Idempotent (handle duplicate events)
- Error handling with retries
- Log all operations
""",
                "input_format": "S3 event (JSON)",
                "output_format": "Success/failure response",
                "examples": [
                    {
                        "input": "S3 event with bucket='mybucket', key='data.csv'",
                        "output": "{'statusCode': 200, 'body': 'Processed 100 records'}",
                        "explanation": "Successfully processed CSV and loaded to DynamoDB"
                    }
                ],
                "constraints": [
                    "CSV files up to 100MB",
                    "Lambda timeout: 5 minutes",
                    "Memory: 512MB"
                ],
                "solution_code": """import boto3
import csv
import json
import logging
from io import StringIO

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')
table = dynamodb.Table('MyTable')

def lambda_handler(event, context):
    try:
        # Extract S3 info from event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        logger.info(f"Processing {bucket}/{key}")
        
        # Download file from S3 (streaming)
        response = s3.get_object(Bucket=bucket, Key=key)
        
        # Process CSV line by line (streaming)
        valid_count = 0
        invalid_count = 0
        
        # Decode streaming body
        lines = response['Body'].iter_lines()
        csv_reader = csv.DictReader(
            (line.decode('utf-8') for line in lines)
        )
        
        # Batch write to DynamoDB
        with table.batch_writer() as batch:
            for row in csv_reader:
                if validate_row(row):
                    batch.put_item(Item=row)
                    valid_count += 1
                else:
                    invalid_count += 1
                    logger.warning(f"Invalid row: {row}")
        
        # Send notification
        send_notification(
            valid_count, 
            invalid_count, 
            key
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Success',
                'valid': valid_count,
                'invalid': invalid_count
            })
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

def validate_row(row):
    '''Validate row has required fields'''
    required = ['id', 'name', 'email']
    return all(field in row and row[field] for field in required)

def send_notification(valid, invalid, filename):
    '''Send email summary via SES'''
    ses.send_email(
        Source='noreply@example.com',
        Destination={'ToAddresses': ['admin@example.com']},
        Message={
            'Subject': {'Data': f'Processing complete: {filename}'},
            'Body': {
                'Text': {
                    'Data': f'Valid: {valid}, Invalid: {invalid}'
                }
            }
        }
    )
""",
                "solution_explanation": """
Key design decisions:
1. Streaming: iter_lines() instead of loading entire file
2. Batch writer: DynamoDB batch_writer for efficiency
3. Error handling: Try-except with logging
4. Idempotency: Could add check for duplicate S3 key in DynamoDB
5. Validation: Separate function for clarity
6. SES: Send summary email after processing
""",
                "time_complexity": "O(n) where n is number of CSV rows",
                "space_complexity": "O(1) - streaming, batch size is constant",
                "test_cases": [
                    {"description": "Valid CSV with 100 rows", "output": "All 100 processed"},
                    {"description": "CSV with some invalid rows", "output": "Skip invalid, process valid"},
                    {"description": "Empty CSV", "output": "0 records processed"}
                ],
                "common_mistakes": [
                    "Loads entire file into memory (fails for large files)",
                    "No error handling",
                    "Individual DynamoDB puts instead of batch",
                    "No logging",
                    "Doesn't validate rows",
                    "Not idempotent (processes same file twice)"
                ],
                "hints": [
                    "Use iter_lines() for streaming",
                    "batch_writer() for efficient DynamoDB writes",
                    "Always log for debugging in Lambda",
                    "Try-except for error handling"
                ]
            }
        ]
    }
    
    def generate_coding_questions(
        self,
        jd_text: str,
        num_questions: int = 5
    ) -> List[CodingQuestion]:
        """
        Generate coding questions based on JD skills.
        
        Args:
            jd_text: Job description text
            num_questions: Number of questions to generate
            
        Returns:
            List of CodingQuestion objects
        """
        # Extract skills from JD
        skills = self._extract_skills(jd_text)
        
        questions = []
        
        # Get questions for each skill
        for skill in skills:
            skill_lower = skill.lower()
            
            if skill_lower in self.QUESTIONS:
                for q_data in self.QUESTIONS[skill_lower]:
                    question = CodingQuestion(
                        title=q_data["title"],
                        skill_area=skill,
                        difficulty=q_data["difficulty"],
                        problem_statement=q_data["problem_statement"],
                        input_format=q_data["input_format"],
                        output_format=q_data["output_format"],
                        examples=q_data["examples"],
                        constraints=q_data["constraints"],
                        solution_code=q_data["solution_code"],
                        solution_explanation=q_data["solution_explanation"],
                        time_complexity=q_data["time_complexity"],
                        space_complexity=q_data["space_complexity"],
                        test_cases=q_data["test_cases"],
                        common_mistakes=q_data["common_mistakes"],
                        hints=q_data["hints"]
                    )
                    questions.append(question)
                    
                    if len(questions) >= num_questions:
                        return questions
        
        return questions[:num_questions] if questions else []
    
    def _extract_skills(self, jd_text: str) -> List[str]:
        """Extract skills from JD."""
        skills = []
        skill_keywords = ["Python", "SQL", "AWS", "Kubernetes", "Databricks"]
        
        jd_lower = jd_text.lower()
        for keyword in skill_keywords:
            if keyword.lower() in jd_lower:
                skills.append(keyword)
        
        return skills if skills else ["Python"]  # Default to Python


if __name__ == "__main__":
    print("Coding Question Generator - Ready")
