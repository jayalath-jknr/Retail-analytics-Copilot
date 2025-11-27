"""Fallback LM implementation for testing without Ollama.

This module provides a simple rule-based fallback for testing the agent
structure without requiring Ollama to be installed.
"""
import re
from typing import Dict, Any
import json


class FallbackLM:
    """Rule-based fallback LM for testing without Ollama."""
    
    def __init__(self):
        self.call_count = 0
    
    def __call__(self, prompt: str, **kwargs) -> str:
        """Generate response based on simple rules."""
        self.call_count += 1
        prompt_lower = prompt.lower()
        
        # Route classification
        if "routequery" in prompt_lower or ("route" in prompt_lower and "question" in prompt_lower):
            if "policy" in prompt_lower or "return" in prompt_lower:
                return json.dumps({"reasoning": "Question asks about policy which is in documents.", "route": "rag"})
            elif "revenue" in prompt_lower and ("during" in prompt_lower or "campaign" in prompt_lower):
                return json.dumps({"reasoning": "Needs date context from docs and revenue from database.", "route": "hybrid"})
            elif "revenue" in prompt_lower or "top" in prompt_lower:
                return json.dumps({"reasoning": "Pure numerical query from database.", "route": "sql"})
            else:
                return json.dumps({"reasoning": "May need both docs and database.", "route": "hybrid"})
        
        # SQL generation
        if "generatesql" in prompt_lower or ("generate" in prompt_lower and "sql" in prompt_lower):
            sql = "SELECT COUNT(*) FROM Orders"
            
            if "top 3 products" in prompt_lower or "top 3" in prompt_lower:
                sql = '''SELECT p.ProductName as product, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as revenue FROM Products p JOIN "Order Details" od ON p.ProductID = od.ProductID GROUP BY p.ProductName ORDER BY revenue DESC LIMIT 3'''
            
            elif "count" in prompt_lower and "orders" in prompt_lower:
                sql = "SELECT COUNT(*) as count FROM Orders"
            
            elif "aov" in prompt_lower or "average order value" in prompt_lower:
                sql = '''SELECT SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / COUNT(DISTINCT o.OrderID) as aov FROM Orders o JOIN "Order Details" od ON o.OrderID = od.OrderID WHERE o.OrderDate >= "1997-12-01" AND o.OrderDate <= "1997-12-31"'''
            
            elif "category" in prompt_lower and "quantity" in prompt_lower:
                sql = '''SELECT c.CategoryName as category, SUM(od.Quantity) as quantity FROM Categories c JOIN Products p ON c.CategoryID = p.CategoryID JOIN "Order Details" od ON p.ProductID = od.ProductID JOIN Orders o ON od.OrderID = o.OrderID WHERE o.OrderDate >= "1997-06-01" AND o.OrderDate <= "1997-06-30" GROUP BY c.CategoryName ORDER BY quantity DESC'''
            
            elif "beverages" in prompt_lower and "revenue" in prompt_lower:
                sql = '''SELECT SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as revenue FROM Categories c JOIN Products p ON c.CategoryID = p.CategoryID JOIN "Order Details" od ON p.ProductID = od.ProductID JOIN Orders o ON od.OrderID = o.OrderID WHERE c.CategoryName = "Beverages" AND o.OrderDate >= "1997-06-01" AND o.OrderDate <= "1997-06-30"'''
            
            elif "customer" in prompt_lower and "margin" in prompt_lower:
                sql = '''SELECT c.CompanyName as customer, SUM((od.UnitPrice - od.UnitPrice * 0.7) * od.Quantity * (1 - od.Discount)) as margin FROM Customers c JOIN Orders o ON c.CustomerID = o.CustomerID JOIN "Order Details" od ON o.OrderID = od.OrderID WHERE strftime('%Y', o.OrderDate) = '1997' GROUP BY c.CompanyName ORDER BY margin DESC LIMIT 1'''
            
            return json.dumps({"sql_query": sql})
        
        # SQL refinement
        if "refinesql" in prompt_lower or ("refine" in prompt_lower and "sql" in prompt_lower):
            # Try to fix common issues
            if "order details" in prompt_lower:
                return json.dumps({"refined_sql": 'SELECT COUNT(*) FROM "Order Details"'})
            return json.dumps({"refined_sql": "SELECT COUNT(*) FROM Orders"})
        
        # Answer synthesis
        if "synthesizeanswer" in prompt_lower or ("synthesize" in prompt_lower and "answer" in prompt_lower):
            # Extract format hint
            if "int" in prompt_lower:
                if "beverages" in prompt_lower and ("unopened" in prompt_lower or "return" in prompt_lower):
                    return json.dumps({"reasoning": "According to product policy, unopened beverages have 14-day return window.", "answer": "14"})
                return json.dumps({"reasoning": "Based on the data.", "answer": "42"})
            
            elif "float" in prompt_lower:
                if "aov" in prompt_lower:
                    return json.dumps({"reasoning": "Calculated from order totals divided by order count.", "answer": "1234.56"})
                return json.dumps({"reasoning": "Computed from database.", "answer": "1234.56"})
            
            elif "{" in prompt_lower or "dict" in prompt_lower:
                if "category" in prompt_lower:
                    return json.dumps({"reasoning": "Top category by quantity sold.", "answer": '{"category": "Beverages", "quantity": 2057}'})
                elif "customer" in prompt_lower:
                    return json.dumps({"reasoning": "Customer with highest margin.", "answer": '{"customer": "Save-a-lot Markets", "margin": 12345.67}'})
                return json.dumps({"reasoning": "Result object.", "answer": '{"key": "value"}'})
            
            elif "list" in prompt_lower:
                return json.dumps({"reasoning": "Top 3 products by total revenue.", "answer": '[{"product": "Côte de Blaye", "revenue": 141396.74}, {"product": "Thüringer Rostbratwurst", "revenue": 80368.67}, {"product": "Raclette Courdavault", "revenue": 71155.70}]'})
            
            return json.dumps({"reasoning": "Processed query.", "answer": "result"})
        
        # Constraint extraction
        if "extractconstraints" in prompt_lower or ("extract" in prompt_lower and "constraint" in prompt_lower):
            if "summer" in prompt_lower:
                return json.dumps({"constraints": "Date range: 1997-06-01 to 1997-06-30, Focus on Beverages and Condiments categories"})
            elif "winter" in prompt_lower:
                return json.dumps({"constraints": "Date range: 1997-12-01 to 1997-12-31, Focus on Dairy Products and Confections"})
            return json.dumps({"constraints": "No specific constraints found"})
        
        return json.dumps({"response": "Generated response based on input."})


def get_fallback_lm():
    """Get a fallback LM instance."""
    return FallbackLM()
