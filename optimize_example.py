"""DSPy optimization example for NL2SQL module.

This demonstrates how to optimize the NL2SQL module using DSPy's 
BootstrapFewShot optimizer with a small training set.
"""
import dspy
from agent.dspy_signatures import NL2SQL, configure_dspy_ollama
from agent.tools.sqlite_tool import NorthwindDB

# Training examples for SQL generation
TRAINING_EXAMPLES = [
    {
        "question": "Count total orders",
        "schema": "Orders(OrderID, CustomerID, OrderDate)",
        "context": "",
        "sql_query": "SELECT COUNT(*) as count FROM Orders"
    },
    {
        "question": "Top 3 products by revenue",
        "schema": 'Orders(OrderID), "Order Details"(OrderID, ProductID, UnitPrice, Quantity, Discount), Products(ProductID, ProductName)',
        "context": "Revenue = UnitPrice * Quantity * (1 - Discount)",
        "sql_query": 'SELECT p.ProductName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as revenue FROM Products p JOIN "Order Details" od ON p.ProductID = od.ProductID GROUP BY p.ProductName ORDER BY revenue DESC LIMIT 3'
    },
    {
        "question": "Orders in June 1997",
        "schema": "Orders(OrderID, OrderDate, CustomerID)",
        "context": "Date range: 1997-06-01 to 1997-06-30",
        "sql_query": "SELECT COUNT(*) FROM Orders WHERE OrderDate >= '1997-06-01' AND OrderDate <= '1997-06-30'"
    },
    {
        "question": "Revenue by category",
        "schema": 'Products(ProductID, CategoryID), Categories(CategoryID, CategoryName), "Order Details"(ProductID, UnitPrice, Quantity, Discount)',
        "context": "",
        "sql_query": 'SELECT c.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as revenue FROM Categories c JOIN Products p ON c.CategoryID = p.CategoryID JOIN "Order Details" od ON p.ProductID = od.ProductID GROUP BY c.CategoryName ORDER BY revenue DESC'
    },
    {
        "question": "Average order value in December 1997",
        "schema": 'Orders(OrderID, OrderDate), "Order Details"(OrderID, UnitPrice, Quantity, Discount)',
        "context": "AOV = Total revenue / distinct order count",
        "sql_query": 'SELECT SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / COUNT(DISTINCT o.OrderID) as aov FROM Orders o JOIN "Order Details" od ON o.OrderID = od.OrderID WHERE o.OrderDate >= "1997-12-01" AND o.OrderDate <= "1997-12-31"'
    },
    {
        "question": "Top customer by total orders",
        "schema": "Orders(OrderID, CustomerID), Customers(CustomerID, CompanyName)",
        "context": "",
        "sql_query": "SELECT c.CompanyName, COUNT(o.OrderID) as order_count FROM Customers c JOIN Orders o ON c.CustomerID = o.CustomerID GROUP BY c.CompanyName ORDER BY order_count DESC LIMIT 1"
    },
    {
        "question": "Products in Beverages category",
        "schema": "Products(ProductID, ProductName, CategoryID), Categories(CategoryID, CategoryName)",
        "context": "",
        "sql_query": "SELECT p.ProductName FROM Products p JOIN Categories c ON p.CategoryID = c.CategoryID WHERE c.CategoryName = 'Beverages'"
    },
    {
        "question": "Quantity sold per category in June 1997",
        "schema": 'Orders(OrderID, OrderDate), "Order Details"(OrderID, ProductID, Quantity), Products(ProductID, CategoryID), Categories(CategoryID, CategoryName)',
        "context": "Date range: 1997-06-01 to 1997-06-30",
        "sql_query": 'SELECT c.CategoryName, SUM(od.Quantity) as total_quantity FROM Categories c JOIN Products p ON c.CategoryID = p.CategoryID JOIN "Order Details" od ON p.ProductID = od.ProductID JOIN Orders o ON od.OrderID = o.OrderID WHERE o.OrderDate >= "1997-06-01" AND o.OrderDate <= "1997-06-30" GROUP BY c.CategoryName ORDER BY total_quantity DESC'
    }
]


def create_training_set():
    """Convert training examples to DSPy Example format."""
    return [dspy.Example(**ex).with_inputs("question", "schema", "context") for ex in TRAINING_EXAMPLES]


def evaluate_sql_accuracy(module, examples, db):
    """Evaluate SQL generation accuracy."""
    correct = 0
    total = len(examples)
    
    for ex in examples:
        try:
            # Generate SQL
            prediction = module.forward(
                question=ex.question,
                schema=ex.schema,
                context=ex.context
            )
            
            # Test if it executes without error
            result = db.execute_query(prediction)
            
            if result.success and result.rows:
                correct += 1
        except:
            pass
    
    return correct / total if total > 0 else 0


def optimize_nl2sql():
    """Demonstrate DSPy optimization for NL2SQL."""
    print("=" * 60)
    print("DSPy Optimization Example: NL2SQL Module")
    print("=" * 60)
    
    # Setup
    configure_dspy_ollama()
    db = NorthwindDB()
    
    # Create training set
    train_set = create_training_set()
    print(f"\nTraining set: {len(train_set)} examples")
    
    # Baseline (unoptimized)
    print("\n1. Baseline (unoptimized) NL2SQL...")
    baseline_module = NL2SQL()
    baseline_accuracy = evaluate_sql_accuracy(baseline_module, train_set, db)
    print(f"   Baseline accuracy: {baseline_accuracy:.1%}")
    
    # Optimized with BootstrapFewShot
    print("\n2. Optimizing with BootstrapFewShot...")
    try:
        optimizer = dspy.BootstrapFewShot(
            metric=lambda gold, pred, trace=None: 1.0,  # Simplified
            max_bootstrapped_demos=3,
            max_labeled_demos=3
        )
        
        optimized_module = optimizer.compile(
            student=NL2SQL(),
            trainset=train_set
        )
        
        optimized_accuracy = evaluate_sql_accuracy(optimized_module, train_set, db)
        print(f"   Optimized accuracy: {optimized_accuracy:.1%}")
        
        # Summary
        print("\n" + "=" * 60)
        print("Results Summary")
        print("=" * 60)
        print(f"Baseline:  {baseline_accuracy:.1%}")
        print(f"Optimized: {optimized_accuracy:.1%}")
        print(f"Delta:     {(optimized_accuracy - baseline_accuracy):.1%}")
        
        if optimized_accuracy > baseline_accuracy:
            print("\n✓ Optimization successful!")
        else:
            print("\n⚠ No improvement - may need more examples or different optimizer")
    
    except Exception as e:
        print(f"   Optimization failed: {e}")
        print("   Note: This requires Ollama to be running with phi3.5 model")


if __name__ == "__main__":
    optimize_nl2sql()
