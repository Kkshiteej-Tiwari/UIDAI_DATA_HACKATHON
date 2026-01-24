/*
 * ============================================================================
 * GIE EXAM - OOP PRACTICE PROBLEMS
 * ============================================================================
 * Topics Covered:
 * 1. Class structure, access specifiers, constructors, destructors
 * 2. Copy constructor, assignment operator, new/delete, deep/shallow copy
 * 3. Function overloading, overriding, single inheritance
 * 4. Runtime polymorphism (virtual keyword)
 * 5. Exceptions
 * 6. STL structures (vector, list) with iterators
 * ============================================================================
 */

#include <iostream>
#include <string>
#include <vector>
#include <list>
#include <stdexcept>
using namespace std;

// ============================================================================
// PROBLEM 1: Basic Class Structure with Access Specifiers
// ============================================================================
/*
 * TASK: Complete the BankAccount class with:
 * - Private members: accountNumber (string), balance (double)
 * - Public constructor that initializes both members
 * - Public methods: deposit(double), withdraw(double), getBalance()
 * - Protected method: applyInterest(double rate) that adds interest to balance
 * 
 * Constraints:
 * - Withdraw should throw an exception if amount > balance
 * - Deposit should throw an exception if amount is negative
 */

class NegativeValueException : public exception {
    int value;
public :
    NegativeValueException(int val) {
        this->value = value;
    }
    int getValue() {
        return value;
    }

};
class BankAccount {
private:
    // TODO: Add private data members
    double balance;
    string accountNumber;
    
protected:
    // TODO: Add protected method applyInterest
    void applyInterest(double rate) {
        balance = balance + balance*rate;
    }

public:
    // TODO: Add constructor
    BankAccount(string num, double bal) : accountNumber(num) , balance(bal) {}
    
    // TODO: Add deposit method
    void deposit(double amount) {
        try {
            if (amount<0) {
                throw NegativeValueException(amount);
            }
            else {
                this->balance+=amount;
            }
        }
        catch (NegativeValueException e) {
            cout << "deposited amount "<< e.getValue() << "is invalid!" << endl;
        }
    }
    
    // TODO: Add withdraw method
    void withdraw(double amount) {
        try {
            if ( balance < amount) {
                throw amount-balance;
            }
            else {
                balance-=amount;
            }
        }
        catch(int num) {
            cout << "Account balance is not suficient by" << num << endl; 
        }
    }
    
    // TODO: Add getBalance method
    double getBalance() {
        return balance;
    }
};


// ============================================================================
// PROBLEM 2: Constructors, Destructor, Copy Constructor, Assignment Operator
// ============================================================================
/*
 * TASK: Implement a DynamicArray class that:
 * - Has a private int* data and int size
 * - Default constructor: creates array of size 5, initialized to 0
 * - Parameterized constructor: takes size and initial value
 * - Copy constructor: performs DEEP COPY
 * - Assignment operator: performs DEEP COPY (handle self-assignment!)
 * - Destructor: properly frees memory
 * - Methods: setElement(int index, int value), getElement(int index), getSize()
 * 
 * This tests your understanding of:
 * - new and delete operators
 * - Deep copy vs shallow copy
 * - Rule of Three
 */

class DynamicArray {
private:
    int* data;
    int size; // if u dont wanna allocate then dont??
    int* accounts;
public:
    // Default Constructor
    DynamicArray() {
        // TODO: Allocate array of size 5, initialize to 0
        accounts = new int[size];
        for (int i = 0; i<5; i++) {
            accounts[i] = 0;
        }
         
    }

    // Parameterized Constructor
    DynamicArray(int sz, int initialValue) {
        // TODO: Allocate array of given size, initialize to initialValue

        accounts = new int[sz];
        for (int i =0; i<sz; i++) {
            accounts[i] = initialValue;
        }
    }

    // Copy Constructor - DEEP COPY
    DynamicArray(const DynamicArray& other) {
        // TODO: Create a deep copy of 'other'
        // Hint: Allocate new memory, copy each element
        size = other.size;
        accounts = new int[size];
        for (int i = 0; i < other.size; i++) {
            accounts[i] = other.accounts[i];   ;
        }
    }

    // Assignment Operator - DEEP COPY
    DynamicArray& operator=(const DynamicArray& other) {
        // TODO: Handle self-assignment, delete old memory, deep copy
        // Hint: Check if this != &other
        if (this != &other) {
            delete[] accounts; // Free existing memory

            size = other.size;
            accounts = new int[size];
            for (int i = 0; i < other.size; i++) {
                accounts[i] = other.accounts[i];
            }
        }
        return *this;
    }

    // Destructor
    ~DynamicArray() {
        // TODO: Free allocated memory
        delete[] accounts;
    }

    void setElement(int index, int value) {
        // TODO: Set element at index (with bounds checking)
        accounts[index] = value;
    }

    int getElement(int index) const { // const method because it does not modify the object if i remove const then it will give error when i call this method on const object because it may modify the object 
        // TODO: Return element at index (with bounds checking)
        if (index>=0 || index < size)
            return accounts[index];
        return 0;
    }

    int getSize() const {
        return size;
    }

    void print() const {
        cout << "Array: [";
        for (int i = 0; i < size; i++) {
            cout << accounts[i];
            if (i < size - 1) cout << ", ";
        }
        cout << "]" << endl;
    }
};


// ============================================================================
// PROBLEM 3: Function Overloading
// ============================================================================
/*
 * TASK: Create a Calculator class with overloaded 'add' methods:
 * - add(int, int) -> returns int
 * - add(double, double) -> returns double
 * - add(int, int, int) -> returns int (sum of three)
 * - add(string, string) -> returns concatenated string
 * 
 * Also overload the static method 'multiply':
 * - multiply(int, int) -> returns int
 * - multiply(double, double) -> returns double
 */

class Calculator {
public:
    // TODO: Implement overloaded add methods
    int add(int a, int b) {
        return a + b;
    }
    double add(double a, double b) {
        return a + b;
    }
    int add(int a, int b, int c) {
        return a + b + c;
    }
    string add(string a, string b) {
        return a + b;
    }
    int multiply(int a, int b) {
        return a * b;
    }
    double multiply(double a, double b) {
        return a * b;
    }
    // TODO: Implement overloaded multiply methods (static)
};


// ============================================================================
// PROBLEM 4: Single Inheritance and Function Overriding
// ============================================================================
/*
 * TASK: Create an inheritance hierarchy:
 * 
 * Base class: Shape
 * - Protected member: string name
 * - Public virtual method: double getArea() = 0 (pure virtual)
 * - Public virtual method: void display() - prints "Shape: <name>"
 * - Virtual destructor
 * 
 * Derived class: Rectangle (inherits from Shape)
 * - Private members: double width, double height
 * - Constructor that takes width, height (set name = "Rectangle")
 * - Override getArea(): returns width * height
 * - Override display(): prints "Rectangle: <width> x <height>, Area: <area>"
 * 
 * Derived class: Circle (inherits from Shape)
 * - Private member: double radius
 * - Constructor that takes radius (set name = "Circle")
 * - Override getArea(): returns 3.14159 * radius * radius
 * - Override display(): prints "Circle: radius = <radius>, Area: <area>"
 */

class Shape {
protected:
    string name;

public:
    // TODO: Add constructor
    Shape(string s) : name(s) {}
    
    // TODO: Add pure virtual getArea method
    virtual double getArea() = 0;
    
    // TODO: Add virtual display method
    virtual void display() {
        cout << "Shape: " << name << endl;
    }
    
    // TODO: Add virtual destructor
    virtual ~Shape() {}
};

class Rectangle : public Shape {
private:
    // TODO: Add private members
    int length;
    int width;

public:
    // TODO: Add constructor
    Rectangle (int l, int w) : Shape("Rectangle"), length(l), width(w) {}
    
    // TODO: Override getArea
    double getArea() override {
        return length * width;
    }
    
    // TODO: Override display
    void display() override {
        cout << "Rectangle: " << length << " x " << width << ", Area: " << getArea() << endl;
    }
};

class Circle : public Shape {
private:
    // TODO: Add private members
    int radius;

public:
    // TODO: Add constructor
    Circle(int r) : radius(r), Shape("Circle") {}
    
    // TODO: Override getArea
    double getArea() override {
        return 3.14159 * radius * radius;
    }
    
    // TODO: Override display
    void display() override {
        cout << "Circle: radius = " << radius << ", Area: " << getArea() << endl;
    }
};


// ============================================================================
// PROBLEM 5: Runtime Polymorphism (Virtual Functions)
// ============================================================================
/*
 * TASK: Demonstrate runtime polymorphism:
 * 
 * Create a function: void printShapeInfo(Shape* shape)
 * - This should call shape->display() and shape->getArea()
 * - Due to virtual functions, it should work correctly for any Shape subclass
 * 
 * In main(), create:
 * - A Rectangle object
 * - A Circle object
 * - Call printShapeInfo with pointers to both objects
 * - Also create an array of Shape* containing different shapes
 */

void printShapeInfo(Shape* shape) {
    // TODO: Implement this function
    shape->display();
    cout << "Area: " << shape->getArea() << endl;
}


// ============================================================================
// PROBLEM 6: Exception Handling
// ============================================================================
/*
 * TASK: Create a SafeDivision class with:
 * - Static method: double divide(double a, double b)
 *   - Throws std::invalid_argument if b is 0
 *   - Throws std::overflow_error if result is too large (> 1e308)
 * 
 * - Static method: int safeParse(const string& str)
 *   - Uses stoi() to parse string to int
 *   - Catches std::invalid_argument and std::out_of_range exceptions
 *   - Re-throws with more descriptive message
 * 
 * In the test function, demonstrate:
 * - try-catch blocks
 * - Catching specific exception types
 * - Catching base exception class
 * - Using what() method
 */

class SafeDivision {
public:
    static double divide(double a, double b) {
        // TODO: Implement with exception handling
        try {
            if (b == 0) {
                throw b;
            }
            else {
                double result = a / b;
                if (result > 1e308) {
                    throw result;
                }
                return result;
            }
        }
        catch (double val) {
            if ( val == 0) {
                cout << "Division by zero is not allowed!" << endl;
            }
            else {
                cout << "Overflow error: Result is too large!" << endl;
            }
        }
        return 0;
    }

    static int safeParse(const string& str) {
        // TODO: Implement with exception handling
        try {
            int value = stoi(str);
            return value;
        }
        catch (invalid_argument& e) {
            cout << "Invalid argument: Cannot convert '" << str << "' to integer." << endl;
        }
        catch (out_of_range& e) {
            cout << "Out of range: The number in '" << str << "' is too large for an int." << endl;
        }
        return 0;
    }
};

void testExceptions() {
    // TODO: Test the SafeDivision class with various inputs
    // Use try-catch blocks to handle exceptions
    
    cout << "\n=== Testing Exception Handling ===" << endl;
    
    // Test 1: Division by zero
    try {
        // TODO: Call divide with divisor 0
        SafeDivision::divide(10, 0);
    } catch (/* TODO: catch appropriate exception */ ) {
        // TODO: Print error message
        
    }
    
    // Test 2: Normal division
    try {
        // TODO: Call divide with valid inputs
    } catch (...) {
        // TODO: Handle any exception
    }
    
    // Test 3: Parse valid integer
    try {
        // TODO: Parse "123"
    } catch (...) {
        // TODO: Handle exception
    }
    
    // Test 4: Parse invalid integer
    try {
        // TODO: Parse "abc"
    } catch (...) {
        // TODO: Handle exception
    }
}


// ============================================================================
// PROBLEM 7: STL Vector with Iterators
// ============================================================================
/*
 * TASK: Implement the following functions using std::vector and iterators:
 * 
 * 1. void populateVector(vector<int>& vec, int n)
 *    - Add numbers 1 to n to the vector using push_back
 * 
 * 2. void printVector(const vector<int>& vec)
 *    - Print all elements using iterator (not index!)
 * 
 * 3. int sumVector(const vector<int>& vec)
 *    - Calculate sum using const_iterator
 * 
 * 4. void doubleElements(vector<int>& vec)
 *    - Double each element using iterator
 * 
 * 5. void removeEven(vector<int>& vec)
 *    - Remove all even numbers using erase and iterator
 *    - Be careful with iterator invalidation!
 */

void populateVector(vector<int>& vec, int n) {
    // TODO: Add numbers 1 to n
    for (int i = 1; i <= n; i++) {
        vec.push_back(i);
    }

}

void printVector(const vector<int>& vec) {
    // TODO: Print using iterator
    
    cout << "Vector: [";
    // Use: vector<int>::const_iterator it = vec.begin()
    // Or: for (auto it = vec.begin(); it != vec.end(); ++it)
    cout << "]" << endl;
}

int sumVector(const vector<int>& vec) {
    // TODO: Calculate sum using const_iterator
    return 0;
}

void doubleElements(vector<int>& vec) {
    // TODO: Double each element using iterator
}

void removeEven(vector<int>& vec) {
    // TODO: Remove even numbers
    // Hint: erase returns iterator to next element
}


// ============================================================================
// PROBLEM 8: STL List with Iterators
// ============================================================================
/*
 * TASK: Implement the following functions using std::list and iterators:
 * 
 * 1. void populateList(list<string>& lst, const vector<string>& words)
 *    - Add all words from vector to list using push_back
 * 
 * 2. void printList(const list<string>& lst)
 *    - Print all elements using iterator
 * 
 * 3. void insertAfter(list<string>& lst, const string& target, const string& newWord)
 *    - Find 'target' in list and insert 'newWord' after it
 *    - If target not found, add newWord at the end
 * 
 * 4. void removeWord(list<string>& lst, const string& word)
 *    - Remove first occurrence of 'word' from list
 * 
 * 5. void reverseList(list<string>& lst)
 *    - Reverse the list (you can use lst.reverse() or do it manually)
 */

void populateList(list<string>& lst, const vector<string>& words) {
    // TODO: Add all words from vector to list
}

void printList(const list<string>& lst) {
    // TODO: Print using iterator
    cout << "List: [";
    // Use: list<string>::const_iterator it = lst.begin()
    cout << "]" << endl;
}

void insertAfter(list<string>& lst, const string& target, const string& newWord) {
    // TODO: Find target and insert newWord after it
}

void removeWord(list<string>& lst, const string& word) {
    // TODO: Remove first occurrence of word
}

void reverseList(list<string>& lst) {
    // TODO: Reverse the list
}


// ============================================================================
// PROBLEM 9: Comprehensive OOP Exercise - Student Management System
// ============================================================================
/*
 * TASK: Build a mini Student Management System that uses ALL concepts:
 * 
 * Class: Person (Base class)
 * - Protected: string name, int age
 * - Public constructor, virtual destructor
 * - Virtual method: void introduce()
 * 
 * Class: Student (Inherits from Person)
 * - Private: string* courses (dynamic array), int numCourses, double gpa
 * - Constructor with name, age, initial courses array
 * - Copy constructor (deep copy for courses)
 * - Assignment operator (deep copy)
 * - Destructor (free courses array)
 * - Override introduce()
 * - Method: void addCourse(const string& course)
 * - Method: void printCourses() - use pointer arithmetic or iteration
 * 
 * Class: StudentManager
 * - Private: vector<Student*> students
 * - Method: void addStudent(Student* s)
 * - Method: void removeStudent(const string& name)
 * - Method: void printAllStudents() - use iterators, demonstrate polymorphism
 * - Method: Student* findStudent(const string& name) - throws exception if not found
 * - Destructor: properly cleanup all dynamically allocated students
 */

class Person {
protected:
    string name;
    int age;

public:
    // TODO: Implement Person class
};

class Student : public Person {
private:
    string* courses;
    int numCourses;
    int maxCourses;
    double gpa;

public:
    // TODO: Implement Student class with all required methods
    // Remember: Rule of Three (copy constructor, assignment operator, destructor)
};

class StudentManager {
private:
    vector<Student*> students;

public:
    // TODO: Implement StudentManager class
    // Use iterators for vector operations
    // Implement proper exception handling
};


// ============================================================================
// MAIN FUNCTION - Test Your Solutions
// ============================================================================

int main() {
    cout << "========================================" << endl;
    cout << "   GIE OOP Practice Problems" << endl;
    cout << "========================================" << endl;

    Circle* c = new Circle(5);
    printShapeInfo(c);
    Rectangle* r = new Rectangle(4,6);
    printShapeInfo(r);
    // Uncomment each section as you complete the problems

    /*
    // ---- Test Problem 1: BankAccount ----
    cout << "\n--- Problem 1: BankAccount ---" << endl;
    BankAccount acc("ACC001", 1000.0);
    cout << "Initial balance: " << acc.getBalance() << endl;
    acc.deposit(500);
    cout << "After deposit: " << acc.getBalance() << endl;
    acc.withdraw(200);
    cout << "After withdraw: " << acc.getBalance() << endl;
    */

    /*
    // ---- Test Problem 2: DynamicArray ----
    cout << "\n--- Problem 2: DynamicArray ---" << endl;
    DynamicArray arr1(5, 10);
    arr1.print();
    
    DynamicArray arr2 = arr1;  // Copy constructor
    arr2.setElement(0, 99);
    cout << "After modifying arr2: " << endl;
    arr1.print();  // Should be unchanged (deep copy)
    arr2.print();
    
    DynamicArray arr3;
    arr3 = arr1;  // Assignment operator
    arr3.setElement(1, 88);
    cout << "After modifying arr3: " << endl;
    arr1.print();  // Should be unchanged
    arr3.print();
    */

    /*
    // ---- Test Problem 3: Calculator ----
    cout << "\n--- Problem 3: Calculator ---" << endl;
    Calculator calc;
    cout << "add(5, 3) = " << calc.add(5, 3) << endl;
    cout << "add(5.5, 3.3) = " << calc.add(5.5, 3.3) << endl;
    cout << "add(1, 2, 3) = " << calc.add(1, 2, 3) << endl;
    cout << "add(\"Hello\", \" World\") = " << calc.add("Hello", " World") << endl;
    */

    /*
    // ---- Test Problem 4 & 5: Inheritance & Polymorphism ----
    cout << "\n--- Problem 4 & 5: Shapes ---" << endl;
    Rectangle rect(5.0, 3.0);
    Circle circ(2.5);
    
    printShapeInfo(&rect);
    printShapeInfo(&circ);
    
    // Array of shapes (polymorphism)
    Shape* shapes[2];
    shapes[0] = new Rectangle(4.0, 6.0);
    shapes[1] = new Circle(3.0);
    
    cout << "\nPolymorphic array:" << endl;
    for (int i = 0; i < 2; i++) {
        shapes[i]->display();
    }
    
    // Cleanup
    for (int i = 0; i < 2; i++) {
        delete shapes[i];
    }
    */

    /*
    // ---- Test Problem 6: Exceptions ----
    testExceptions();
    */

    /*
    // ---- Test Problem 7: Vector with Iterators ----
    cout << "\n--- Problem 7: Vector ---" << endl;
    vector<int> vec;
    populateVector(vec, 10);
    printVector(vec);
    cout << "Sum: " << sumVector(vec) << endl;
    
    doubleElements(vec);
    cout << "After doubling: ";
    printVector(vec);
    
    removeEven(vec);
    cout << "After removing even: ";
    printVector(vec);
    */

    /*
    // ---- Test Problem 8: List with Iterators ----
    cout << "\n--- Problem 8: List ---" << endl;
    vector<string> words = {"apple", "banana", "cherry", "date"};
    list<string> lst;
    
    populateList(lst, words);
    printList(lst);
    
    insertAfter(lst, "banana", "blueberry");
    cout << "After insert: ";
    printList(lst);
    
    removeWord(lst, "cherry");
    cout << "After remove: ";
    printList(lst);
    
    reverseList(lst);
    cout << "After reverse: ";
    printList(lst);
    */

    /*
    // ---- Test Problem 9: Student Management ----
    cout << "\n--- Problem 9: Student Management ---" << endl;
    StudentManager manager;
    
    Student* s1 = new Student("Alice", 20, 3.8);
    s1->addCourse("Math");
    s1->addCourse("Physics");
    
    Student* s2 = new Student("Bob", 22, 3.5);
    s2->addCourse("Chemistry");
    
    manager.addStudent(s1);
    manager.addStudent(s2);
    
    manager.printAllStudents();
    
    try {
        Student* found = manager.findStudent("Alice");
        cout << "Found student: ";
        found->introduce();
    } catch (const exception& e) {
        cout << "Error: " << e.what() << endl;
    }
    */

    cout << "\n========================================" << endl;
    cout << "   Good luck with your GIE exam!" << endl;
    cout << "========================================" << endl;

    return 0;
}


// ============================================================================
// SOLUTIONS SECTION (SPOILER ALERT - Try solving first!)
// ============================================================================
/*
 * Scroll down for solutions after attempting the problems...
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * SOLUTIONS:
 * 
 * // Problem 1: BankAccount Solution
 * class BankAccount {
 * private:
 *     string accountNumber;
 *     double balance;
 * 
 * protected:
 *     void applyInterest(double rate) {
 *         balance += balance * rate / 100;
 *     }
 * 
 * public:
 *     BankAccount(string accNum, double initialBalance) 
 *         : accountNumber(accNum), balance(initialBalance) {}
 * 
 *     void deposit(double amount) {
 *         if (amount < 0) throw invalid_argument("Cannot deposit negative amount");
 *         balance += amount;
 *     }
 * 
 *     void withdraw(double amount) {
 *         if (amount > balance) throw runtime_error("Insufficient funds");
 *         balance -= amount;
 *     }
 * 
 *     double getBalance() const { return balance; }
 * };
 * 
 * 
 * // Problem 2: DynamicArray Solution
 * DynamicArray() : size(5) {
 *     data = new int[size];
 *     for (int i = 0; i < size; i++) data[i] = 0;
 * }
 * 
 * DynamicArray(int sz, int initialValue) : size(sz) {
 *     data = new int[size];
 *     for (int i = 0; i < size; i++) data[i] = initialValue;
 * }
 * 
 * DynamicArray(const DynamicArray& other) : size(other.size) {
 *     data = new int[size];
 *     for (int i = 0; i < size; i++) data[i] = other.data[i];
 * }
 * 
 * DynamicArray& operator=(const DynamicArray& other) {
 *     if (this != &other) {
 *         delete[] data;
 *         size = other.size;
 *         data = new int[size];
 *         for (int i = 0; i < size; i++) data[i] = other.data[i];
 *     }
 *     return *this;
 * }
 * 
 * ~DynamicArray() { delete[] data; }
 * 
 * 
 * // Problem 4: Shape hierarchy Solution
 * class Shape {
 * protected:
 *     string name;
 * public:
 *     Shape(string n = "Shape") : name(n) {}
 *     virtual double getArea() = 0;
 *     virtual void display() { cout << "Shape: " << name << endl; }
 *     virtual ~Shape() {}
 * };
 * 
 * class Rectangle : public Shape {
 * private:
 *     double width, height;
 * public:
 *     Rectangle(double w, double h) : Shape("Rectangle"), width(w), height(h) {}
 *     double getArea() override { return width * height; }
 *     void display() override {
 *         cout << "Rectangle: " << width << " x " << height 
 *              << ", Area: " << getArea() << endl;
 *     }
 * };
 * 
 * class Circle : public Shape {
 * private:
 *     double radius;
 * public:
 *     Circle(double r) : Shape("Circle"), radius(r) {}
 *     double getArea() override { return 3.14159 * radius * radius; }
 *     void display() override {
 *         cout << "Circle: radius = " << radius 
 *              << ", Area: " << getArea() << endl;
 *     }
 * };
 * 
 * 
 * // Problem 7: Vector functions Solution
 * void populateVector(vector<int>& vec, int n) {
 *     for (int i = 1; i <= n; i++) vec.push_back(i);
 * }
 * 
 * void printVector(const vector<int>& vec) {
 *     cout << "Vector: [";
 *     for (vector<int>::const_iterator it = vec.begin(); it != vec.end(); ++it) {
 *         if (it != vec.begin()) cout << ", ";
 *         cout << *it;
 *     }
 *     cout << "]" << endl;
 * }
 * 
 * int sumVector(const vector<int>& vec) {
 *     int sum = 0;
 *     for (auto it = vec.begin(); it != vec.end(); ++it) sum += *it;
 *     return sum;
 * }
 * 
 * void doubleElements(vector<int>& vec) {
 *     for (auto it = vec.begin(); it != vec.end(); ++it) *it *= 2;
 * }
 * 
 * void removeEven(vector<int>& vec) {
 *     for (auto it = vec.begin(); it != vec.end(); ) {
 *         if (*it % 2 == 0) it = vec.erase(it);
 *         else ++it;
 *     }
 * }
 */
