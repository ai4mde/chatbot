#!/usr/bin/env python
"""
Script to test the Document Writer and Reviewer Agents.
This script simulates generating and reviewing technical documentation.
"""

import os
import sys
import asyncio
import logging
from termcolor import colored
import argparse
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Mock OpenAI API key for testing
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mocking"

# Import after setting environment variables
from app.services.chat.documents import DocumentWriterAgent, DocumentReviewerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample requirements for testing
SAMPLE_REQUIREMENTS = {
    "functional_requirements": [
        {
            "id": "FR-001",
            "name": "User Registration",
            "description": "Users should be able to create accounts with email verification",
            "priority": "High"
        },
        {
            "id": "FR-002",
            "name": "Product Search",
            "description": "Users should be able to search for products with filtering by faculty",
            "priority": "High"
        },
        {
            "id": "FR-003",
            "name": "Shopping Cart",
            "description": "Users should be able to add items to a cart and manage quantities",
            "priority": "High"
        }
    ],
    "non_functional_requirements": [
        {
            "id": "NFR-001",
            "name": "Web-based Application",
            "description": "System should be accessible through web browsers",
            "priority": "High"
        },
        {
            "id": "NFR-002",
            "name": "Mobile Support",
            "description": "System should be responsive and work well on mobile devices",
            "priority": "High"
        }
    ]
}

# Sample UML diagrams for testing
SAMPLE_UML_DIAGRAMS = {
    "class_diagram": """
@startuml
class User {
  +id: int
  +username: string
  +email: string
  +password: string
  +register()
  +login()
  +logout()
}

class Product {
  +id: int
  +name: string
  +description: string
  +price: float
  +faculty: string
  +getDetails()
}

class ShoppingCart {
  +id: int
  +user_id: int
  +items: List<CartItem>
  +addItem()
  +removeItem()
  +checkout()
}

User "1" -- "0..1" ShoppingCart
ShoppingCart "1" -- "0..*" Product
@enduml
    """,
    "sequence_diagram": """
@startuml
actor User
participant "Web Interface" as UI
participant "Backend API" as API
participant "Database" as DB

User -> UI: Register Account
UI -> API: POST /register
API -> DB: Create User
DB --> API: User Created
API --> UI: 201 Created
UI --> User: Registration Successful

User -> UI: Search Products
UI -> API: GET /products?faculty=science
API -> DB: Query Products
DB --> API: Product List
API --> UI: 200 OK with Products
UI --> User: Display Products

User -> UI: Add to Cart
UI -> API: POST /cart/items
API -> DB: Update Cart
DB --> API: Cart Updated
API --> UI: 200 OK
UI --> User: Item Added to Cart
@enduml
    """
}

# Sample conversation for testing
SAMPLE_CONVERSATION = [
    {"role": "user", "content": "I need an online bookstore for Leiden University students."},
    {"role": "assistant", "content": "Could you tell me more about your requirements?"},
    {"role": "user", "content": "We need a platform where students can buy textbooks, course materials, and academic supplies."},
    {"role": "assistant", "content": "What specific features do you need?"},
    {"role": "user", "content": "We need user registration, product search with filtering by faculty, shopping cart, checkout with multiple payment methods, and academic bundles for different faculties."},
    {"role": "assistant", "content": "Any specific technical requirements?"},
    {"role": "user", "content": "It should be a web-based application with mobile support. We also need inventory management for administrators and order tracking for users."},
    {"role": "assistant", "content": "Any other features you'd like to include?"},
    {"role": "user", "content": "We'd like to have personalized recommendations based on user preferences and multi-language support for international students."},
]

# Mock responses for the LLM
MOCK_DOCUMENTATION_RESPONSE = """
# Leiden University Online Bookstore - Technical Documentation

## Introduction
This document provides technical documentation for the Leiden University Online Bookstore, a web-based platform designed for students to purchase textbooks, course materials, and academic supplies. The system includes features such as user registration, product search with faculty filtering, shopping cart functionality, multiple payment methods, and academic bundles for different faculties.

## System Architecture
The system follows a three-tier architecture:
1. **Presentation Layer**: Web interface and mobile-responsive design
2. **Application Layer**: Backend API services
3. **Data Layer**: Database and storage systems

## Component Design
### User Management Component
- Handles user registration, authentication, and profile management
- Implements email verification for new accounts
- Manages user preferences for personalized recommendations

### Product Catalog Component
- Manages product listings and categories
- Implements search functionality with faculty filtering
- Handles academic bundle configurations

### Shopping Cart Component
- Manages cart operations (add, remove, update quantities)
- Calculates totals and applies discounts
- Prepares cart for checkout process

### Order Processing Component
- Handles checkout process
- Integrates with payment gateways
- Manages order tracking and status updates

### Inventory Management Component
- Tracks product availability
- Alerts administrators of low stock
- Manages product restocking

## API Documentation
### Authentication Endpoints
- `POST /api/auth/register`: Create a new user account
- `POST /api/auth/login`: Authenticate a user
- `POST /api/auth/logout`: End a user session

### Product Endpoints
- `GET /api/products`: List all products
- `GET /api/products/{id}`: Get product details
- `GET /api/products/search`: Search products with filters

### Cart Endpoints
- `GET /api/cart`: View current cart
- `POST /api/cart/items`: Add item to cart
- `PUT /api/cart/items/{id}`: Update cart item
- `DELETE /api/cart/items/{id}`: Remove item from cart

### Order Endpoints
- `POST /api/orders`: Create a new order
- `GET /api/orders`: List user orders
- `GET /api/orders/{id}`: Get order details

## Database Schema
### Users Table
- id (PK)
- username
- email
- password_hash
- created_at
- updated_at

### Products Table
- id (PK)
- name
- description
- price
- faculty
- stock_quantity
- created_at
- updated_at

### Carts Table
- id (PK)
- user_id (FK)
- created_at
- updated_at

### CartItems Table
- id (PK)
- cart_id (FK)
- product_id (FK)
- quantity
- created_at
- updated_at

### Orders Table
- id (PK)
- user_id (FK)
- total_amount
- status
- payment_method
- created_at
- updated_at

## Deployment Instructions
1. Set up a web server with Node.js and Express
2. Configure PostgreSQL database
3. Deploy backend API services
4. Set up frontend using React
5. Configure environment variables
6. Set up CI/CD pipeline for automated deployment
7. Configure monitoring and logging

## Testing Strategy
1. **Unit Testing**: Test individual components and functions
2. **Integration Testing**: Test interactions between components
3. **API Testing**: Verify API endpoints functionality
4. **UI Testing**: Test user interface components
5. **Performance Testing**: Verify system performance under load
6. **Security Testing**: Check for vulnerabilities
7. **User Acceptance Testing**: Validate with actual users
"""

MOCK_REVIEW_RESPONSE = """
# Document Review: Leiden University Online Bookstore Technical Documentation

## Review Summary
The technical documentation provides a comprehensive overview of the Leiden University Online Bookstore system. It covers the key components, architecture, API endpoints, database schema, deployment instructions, and testing strategy. However, there are areas that could be improved for clarity, completeness, and technical accuracy.

## Issues Identified
1. **Incomplete API Documentation**: The API documentation lacks details on request/response formats and authentication requirements.
2. **Missing Non-Functional Requirements**: The documentation doesn't adequately address the non-functional requirements like mobile support and multi-language support.
3. **Limited Deployment Instructions**: The deployment instructions are too high-level and lack specific steps.
4. **Insufficient Database Schema**: The database schema doesn't include tables for academic bundles or user preferences.
5. **Lack of Error Handling**: There's no mention of error handling strategies throughout the system.

## Suggested Improvements
1. Enhance API documentation with request/response examples and authentication details
2. Add a section specifically addressing non-functional requirements implementation
3. Provide more detailed, step-by-step deployment instructions
4. Expand the database schema to include all required entities
5. Add a section on error handling and system resilience

## Improved Document

# Leiden University Online Bookstore - Technical Documentation

## Introduction
This document provides technical documentation for the Leiden University Online Bookstore, a web-based platform designed for students to purchase textbooks, course materials, and academic supplies. The system includes features such as user registration, product search with faculty filtering, shopping cart functionality, multiple payment methods, and academic bundles for different faculties.

## System Architecture
The system follows a three-tier architecture:
1. **Presentation Layer**: Web interface and mobile-responsive design
2. **Application Layer**: Backend API services
3. **Data Layer**: Database and storage systems

### Non-Functional Requirements Implementation
- **Web-based Application**: The system is implemented as a responsive web application using React for the frontend and Express.js for the backend.
- **Mobile Support**: The UI is built with responsive design principles using Bootstrap 5, ensuring proper display and functionality on mobile devices.
- **Multi-language Support**: The system implements i18next for internationalization, supporting English, Dutch, and other languages commonly used by international students.
- **Performance**: API responses are optimized with caching strategies to ensure page loads within 2 seconds.
- **Security**: The system implements JWT authentication, HTTPS, and input validation to protect user data.

## Component Design
### User Management Component
- Handles user registration, authentication, and profile management
- Implements email verification for new accounts
- Manages user preferences for personalized recommendations
- Handles multi-language preferences for the user interface

### Product Catalog Component
- Manages product listings and categories
- Implements search functionality with faculty filtering
- Handles academic bundle configurations
- Provides personalized product recommendations based on user history and preferences

### Shopping Cart Component
- Manages cart operations (add, remove, update quantities)
- Calculates totals and applies discounts
- Prepares cart for checkout process
- Persists cart contents between sessions

### Order Processing Component
- Handles checkout process
- Integrates with payment gateways (PayPal, Credit Card, iDEAL)
- Manages order tracking and status updates
- Sends email notifications for order status changes

### Inventory Management Component
- Tracks product availability
- Alerts administrators of low stock
- Manages product restocking
- Provides analytics on product sales and trends

## API Documentation
### Authentication Endpoints
- `POST /api/auth/register`: Create a new user account
  - Request: `{ "username": string, "email": string, "password": string }`
  - Response: `{ "id": number, "username": string, "email": string, "token": string }`
  - Authentication: None

- `POST /api/auth/login`: Authenticate a user
  - Request: `{ "email": string, "password": string }`
  - Response: `{ "token": string, "user": { "id": number, "username": string, "email": string } }`
  - Authentication: None

- `POST /api/auth/logout`: End a user session
  - Request: None
  - Response: `{ "message": "Logged out successfully" }`
  - Authentication: JWT Token

### Product Endpoints
- `GET /api/products`: List all products
  - Request Parameters: `page`, `limit`, `faculty`, `sort`
  - Response: `{ "products": [...], "total": number, "page": number, "limit": number }`
  - Authentication: Optional

- `GET /api/products/{id}`: Get product details
  - Response: `{ "id": number, "name": string, "description": string, "price": number, ... }`
  - Authentication: None

- `GET /api/products/search`: Search products with filters
  - Request Parameters: `query`, `faculty`, `min_price`, `max_price`, `sort`
  - Response: `{ "products": [...], "total": number }`
  - Authentication: None

### Cart Endpoints
- `GET /api/cart`: View current cart
  - Response: `{ "id": number, "items": [...], "total": number }`
  - Authentication: JWT Token

- `POST /api/cart/items`: Add item to cart
  - Request: `{ "product_id": number, "quantity": number }`
  - Response: `{ "id": number, "items": [...], "total": number }`
  - Authentication: JWT Token

- `PUT /api/cart/items/{id}`: Update cart item
  - Request: `{ "quantity": number }`
  - Response: `{ "id": number, "items": [...], "total": number }`
  - Authentication: JWT Token

- `DELETE /api/cart/items/{id}`: Remove item from cart
  - Response: `{ "id": number, "items": [...], "total": number }`
  - Authentication: JWT Token

### Order Endpoints
- `POST /api/orders`: Create a new order
  - Request: `{ "payment_method": string, "shipping_address": object }`
  - Response: `{ "id": number, "status": string, "total": number, ... }`
  - Authentication: JWT Token

- `GET /api/orders`: List user orders
  - Request Parameters: `page`, `limit`, `status`
  - Response: `{ "orders": [...], "total": number }`
  - Authentication: JWT Token

- `GET /api/orders/{id}`: Get order details
  - Response: `{ "id": number, "items": [...], "status": string, ... }`
  - Authentication: JWT Token

## Error Handling
The system implements a consistent error handling strategy:
- All API endpoints return appropriate HTTP status codes
- Error responses follow a standard format: `{ "error": string, "details": object }`
- Client-side errors (4xx) include validation errors and authentication failures
- Server-side errors (5xx) are logged for monitoring and debugging
- The frontend implements error boundaries to prevent UI crashes

## Database Schema
### Users Table
- id (PK)
- username
- email
- password_hash
- language_preference
- created_at
- updated_at

### UserPreferences Table
- id (PK)
- user_id (FK)
- faculty
- preferred_categories
- notification_settings
- created_at
- updated_at

### Products Table
- id (PK)
- name
- description
- price
- faculty
- stock_quantity
- image_url
- created_at
- updated_at

### AcademicBundles Table
- id (PK)
- name
- description
- faculty
- price
- created_at
- updated_at

### BundleItems Table
- id (PK)
- bundle_id (FK)
- product_id (FK)
- quantity
- created_at
- updated_at

### Carts Table
- id (PK)
- user_id (FK)
- created_at
- updated_at

### CartItems Table
- id (PK)
- cart_id (FK)
- product_id (FK)
- bundle_id (FK, nullable)
- quantity
- created_at
- updated_at

### Orders Table
- id (PK)
- user_id (FK)
- total_amount
- status
- payment_method
- shipping_address
- tracking_number
- created_at
- updated_at

### OrderItems Table
- id (PK)
- order_id (FK)
- product_id (FK)
- bundle_id (FK, nullable)
- quantity
- price
- created_at
- updated_at

## Deployment Instructions
### Prerequisites
- Node.js 16+ and npm
- PostgreSQL 13+
- Redis for session management
- Docker and Docker Compose (optional)

### Step-by-Step Deployment
1. **Database Setup**
   ```bash
   psql -U postgres -c "CREATE DATABASE leiden_bookstore;"
   psql -U postgres -d leiden_bookstore -f schema.sql
   ```

2. **Backend Setup**
   ```bash
   cd backend
   npm install
   cp .env.example .env
   # Edit .env with your configuration
   npm run migrate
   npm run seed  # Optional: add sample data
   npm run build
   npm start
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   # Edit .env with your API endpoint
   npm run build
   ```

4. **Web Server Configuration (Nginx)**
   ```nginx
   server {
     listen 80;
     server_name bookstore.leiden.edu;
     
     location /api {
       proxy_pass http://localhost:3000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
     }
     
     location / {
       root /path/to/frontend/build;
       try_files $uri /index.html;
     }
   }
   ```

5. **Docker Deployment (Alternative)**
   ```bash
   docker-compose up -d
   ```

6. **SSL Configuration**
   ```bash
   certbot --nginx -d bookstore.leiden.edu
   ```

7. **Monitoring Setup**
   - Set up Prometheus for metrics collection
   - Configure Grafana for visualization
   - Set up log aggregation with ELK stack

## Testing Strategy
1. **Unit Testing**
   - Backend: Jest for testing individual functions and components
   - Frontend: React Testing Library for component tests
   - Run with: `npm test`

2. **Integration Testing**
   - Test API endpoints with Supertest
   - Test database interactions
   - Run with: `npm run test:integration`

3. **API Testing**
   - Automated API tests with Postman/Newman
   - Test all endpoints with various scenarios
   - Run with: `npm run test:api`

4. **UI Testing**
   - End-to-end tests with Cypress
   - Test critical user flows
   - Run with: `npm run test:e2e`

5. **Performance Testing**
   - Load testing with k6
   - Benchmark API response times
   - Test with simulated user load
   - Run with: `npm run test:performance`

6. **Security Testing**
   - OWASP ZAP for vulnerability scanning
   - Dependency scanning with npm audit
   - Run with: `npm run test:security`

7. **User Acceptance Testing**
   - Guided testing sessions with stakeholders
   - Feedback collection and issue tracking
"""

MOCK_EVALUATION_RESPONSE = """
{
  "scores": {
    "clarity": 8,
    "completeness": 7,
    "technical_accuracy": 9,
    "structure": 8,
    "language_quality": 9,
    "overall": 8.2
  },
  "feedback": {
    "clarity": "The document is generally clear and well-written. Technical concepts are explained in an understandable way, and the organization makes it easy to find specific information.",
    "completeness": "The document covers most aspects of the system, but could be more detailed in areas like error handling, security measures, and internationalization implementation.",
    "technical_accuracy": "The technical information provided appears accurate and follows industry best practices. The architecture and component design are well-thought-out.",
    "structure": "The document follows a logical structure with clear sections. Some subsections could be better organized for easier navigation.",
    "language_quality": "The writing is professional and consistent, with minimal grammatical errors or typos. Technical terminology is used appropriately."
  },
  "improvement_suggestions": [
    "Add more details about error handling strategies",
    "Include information about security measures and data protection",
    "Expand the deployment instructions with environment-specific configurations",
    "Add diagrams to illustrate the system architecture and component interactions",
    "Include a glossary of technical terms for non-technical stakeholders"
  ]
}
"""

# Create a mock response for OpenAI API
def create_mock_openai_response(content):
    return {
        "id": "chatcmpl-mock-id",
        "object": "chat.completion",
        "created": 1677858242,
        "model": "gpt-4o",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "index": 0,
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 500,
            "total_tokens": 600
        }
    }

async def test_document_writer_agent():
    """Test the document writer agent."""
    try:
        # Generate a unique session ID for testing
        session_id = f"test-{uuid.uuid4()}"
        username = "test-group"  # Use test-group as the username to match the directory structure
        
        print(colored(f"Creating document writer agent for session {session_id}...", "blue"))
        
        # Create a mock directory for documentation if it doesn't exist
        docs_dir = os.path.join(os.environ.get('CHATBOT_DATA_PATH', 'data'), username, "documentation")
        os.makedirs(docs_dir, exist_ok=True)
        print(colored(f"Using documentation directory: {docs_dir}", "blue"))
        
        # Patch the OpenAI API client at the lowest level
        with patch('openai.resources.chat.completions.Completions.create') as mock_create:
            # Configure the mock to return our mock response
            mock_create.return_value = create_mock_openai_response(MOCK_DOCUMENTATION_RESPONSE)
            
            # Make it work with async
            mock_create.side_effect = None
            mock_create.return_value = create_mock_openai_response(MOCK_DOCUMENTATION_RESPONSE)
            mock_create.__aenter__ = AsyncMock(return_value=mock_create)
            mock_create.__aexit__ = AsyncMock(return_value=None)
            
            # Create the agent
            writer_agent = DocumentWriterAgent(session_id, username)
            
            print(colored("Generating technical documentation...", "blue"))
            result = await writer_agent.generate_technical_documentation(
                project_name="Leiden University Online Bookstore",
                requirements=SAMPLE_REQUIREMENTS,
                uml_diagrams=SAMPLE_UML_DIAGRAMS,
                messages=SAMPLE_CONVERSATION
            )
        
        print(colored("Technical documentation generated successfully!", "green"))
        print(colored(f"Documentation saved to: {result['file_path']}", "green"))
        
        # Return the file path for use in the reviewer test
        return result['file_path']
        
    except Exception as e:
        logger.error(f"Error testing document writer agent: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return None

async def test_document_reviewer_agent(document_path=None):
    """Test the document reviewer agent."""
    try:
        # Generate a unique session ID for testing
        session_id = f"test-{uuid.uuid4()}"
        username = "test-group"  # Use test-group as the username to match the directory structure
        
        print(colored(f"Creating document reviewer agent for session {session_id}...", "blue"))
        
        # If no document path is provided, create a sample document
        if not document_path:
            docs_dir = os.path.join(os.environ.get('CHATBOT_DATA_PATH', 'data'), username, "documentation")
            os.makedirs(docs_dir, exist_ok=True)
            document_path = os.path.join(docs_dir, "sample_doc_for_review.md")
            
            with open(document_path, 'w', encoding="utf-8") as f:
                f.write(MOCK_DOCUMENTATION_RESPONSE)
            
            print(colored(f"Created sample document for review: {document_path}", "blue"))
        
        # Patch the OpenAI API client at the lowest level for review
        with patch('openai.resources.chat.completions.Completions.create') as mock_create:
            # Configure the mock to return our mock response
            mock_create.return_value = create_mock_openai_response(MOCK_REVIEW_RESPONSE)
            
            # Make it work with async
            mock_create.side_effect = None
            mock_create.__aenter__ = AsyncMock(return_value=mock_create)
            mock_create.__aexit__ = AsyncMock(return_value=None)
            
            # Create the agent
            reviewer_agent = DocumentReviewerAgent(session_id, username)
            
            print(colored(f"Reviewing document: {document_path}", "blue"))
            review_result = await reviewer_agent.review_document(
                document_path=document_path,
                requirements=SAMPLE_REQUIREMENTS
            )
        
        print(colored("Document review completed successfully!", "green"))
        print(colored(f"Reviewed document saved to: {review_result['improved_path']}", "green"))
        
        # Test the document quality evaluation
        with patch('openai.resources.chat.completions.Completions.create') as mock_create:
            # Configure the mock to return our mock response
            mock_create.return_value = create_mock_openai_response(MOCK_EVALUATION_RESPONSE)
            
            # Make it work with async
            mock_create.side_effect = None
            mock_create.__aenter__ = AsyncMock(return_value=mock_create)
            mock_create.__aexit__ = AsyncMock(return_value=None)
            
            print(colored(f"Evaluating document quality: {review_result['improved_path']}", "blue"))
            eval_result = await reviewer_agent.evaluate_documentation_quality(
                document_path=review_result['improved_path']
            )
        
        print(colored("Document quality evaluation completed successfully!", "green"))
        print(colored("Quality scores:", "blue"))
        
        # Print the evaluation scores
        if 'evaluation' in eval_result and 'scores' in eval_result['evaluation']:
            scores = eval_result['evaluation']['scores']
            for criterion, score in scores.items():
                print(colored(f"  {criterion.replace('_', ' ').title()}: {score}/10", "cyan"))
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing document reviewer agent: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False

async def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test the Document Writer and Reviewer Agents")
    parser.add_argument("--test", choices=["writer", "reviewer", "all"], default="all",
                        help="Which test to run (default: all)")
    
    args = parser.parse_args()
    
    document_path = None
    
    if args.test == "writer" or args.test == "all":
        print(colored("\n=== Testing Document Writer Agent ===", "blue", attrs=["bold"]))
        document_path = await test_document_writer_agent()
    
    if args.test == "reviewer" or args.test == "all":
        print(colored("\n=== Testing Document Reviewer Agent ===", "blue", attrs=["bold"]))
        await test_document_reviewer_agent(document_path)

if __name__ == "__main__":
    print(colored("Testing Document Writer and Reviewer Agents...", "blue", attrs=["bold"]))
    asyncio.run(main()) 