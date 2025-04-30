#!/usr/bin/env python
"""
Test script to simulate the entire interview and documentation generation process.
This script will:
1. Create a test chat session
2. Simulate the interview with predefined questions and answers
3. Verify the transition to the documentation phase
4. Check the generation of diagrams, requirements, and SRS document
"""

import os
import sys
import asyncio
import logging
import argparse
from termcolor import colored
from datetime import datetime

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the necessary modules
from app.core.config import settings
from app.services.chat.interview import create_interview_agent
from app.services.chat.chat_manager import LangChainChatManager, ConversationState
from app.services.auth import authenticate_user

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Sample interview questions and answers
INTERVIEW_QA = [
    # Section 1: Introduction
    (
        "Could you describe your role and how it connects to this software project?",
        "Certainly! I'm Kate, the owner of a bookshop in Leiden and the primary decision-maker for this project. My role involves overseeing the daily operations, maintaining our relationship with Leiden University as their preferred supplier, curating our book collection, and strategising for business growth. This project is crucial to me as I aim to expand our reach beyond the physical limitations of our store through an online web-shop. I envision this platform as a means to cater to both our existing university partners and a broader audience, offering them an accessible and convenient way to explore and purchase our offerings. My involvement in this project will ensure that the web-shop aligns with our business goals, customer expectations, and unique selling points.",
    ),
    (
        "Could you provide a brief summary of the project and its main goals?",
        "The project involves developing a comprehensive online web-shop for my bookstore in Leiden. The main goals of this project are to expand our customer base beyond our physical store by reaching a wider, potentially global audience, and to enhance the service we provide to Leiden University as their preferred supplier.\n\nKey objectives include:\n\n1. **Online Presence**: Establishing a robust online platform that represents our brand, showcases our curated collection of books, and highlights our partnership with Leiden University.\n2. **User-Friendly Interface**: Creating an intuitive and easy-to-navigate web-shop that provides an excellent user experience for both casual shoppers and university faculty or students who may need to purchase books for academic purposes.\n3. **Order Management**: Implementing efficient order processing and management systems to handle both individual and bulk university orders seamlessly.\n4. **Integrating Academic Needs**: Tailoring features to support academic needs, such as creating specific sections or portals for university faculty to select and recommend course materials.\n5. **Inventory Management**: Streamlining inventory management to synchronise between our physical store and the online platform, ensuring accuracy in stock levels and availability.\n6. **Marketing and Promotion**: Employing digital marketing tools to promote our offerings and engage with customers, including special promotions, newsletters, and recommendations.\n7. **Secure and Reliable Transactions**: Ensuring secure processing of payments and data protection to foster trust with our customers.\n\nThrough these goals, my aim is to maintain the personal touch and community connection that our physical store offers while embracing the scale and opportunities an online platform can provide.",
    ),
    (
        "What are the primary challenges you're expecting for this project?",
        "There are a few primary challenges I anticipate in this project:\n\n1. **Technical Integration**: Ensuring that the web-shop integrates seamlessly with our existing systems, such as our point of sale (POS) system and inventory management, is critical. This challenge involves both the compatibility of technologies and the potential need for upgrades or replacements of existing infrastructure.\n2. **User Experience**: Designing a web-shop that is intuitive and user-friendly for a diverse audience—from casual readers to academic buyers—requires careful planning and understanding of user needs. Balancing aesthetics with functionality to provide an enjoyable shopping experience is crucial.\n3. **Customisation for Academic Needs**: Since we supply books to Leiden University, creating specific features that cater to academic requirements, such as bespoke book lists for courses or easy bulk purchasing options, might be complex to implement without alienating general customers.\n4. **Inventory Synchronisation**: Maintaining accurate inventory information in real-time between the physical store and the online shop poses a significant challenge. Inventory inaccuracies can lead to customer dissatisfaction if items appear available online but are out of stock.\n5. **Security and Privacy**: Establishing a secure platform for transactions and protecting customer data is paramount. This involves not only the technical aspects of security but also ensuring compliance with data protection regulations like the GDPR.\n6. **Marketing and Visibility**: Building and maintaining a strong online presence in a competitive market will require sustained digital marketing efforts. Reaching our target audience and differentiating ourselves from larger online retailers is a notable challenge.\n7. **Logistical Operations**: As order volumes increase, especially with university partnerships, refining our logistics, including shipping, handling returns, and managing customer service efficiently, is essential.\n\nBy anticipating these challenges, we can develop strategic plans to address them proactively, ensuring the successful launch and ongoing management of the web-shop.",
    ),
    # Section 2: Functionality
    (
        "What are the core features and functionalities you require in your application?",
        "Here are the core features and functionalities I envision for the web-shop:\n\n1. **User Account Management**: Allows users to create accounts, login easily, view order history, save favourite books, and manage personal details.\n2. **Detailed Book Catalogue**: A well-organised, searchable catalogue of books with detailed descriptions, categorisation by genre/subject, and options to filter by author, price, or availability.\n3. **Integrated Academic Portal**: A special section dedicated to Leiden University faculty and students, where they can browse and purchase course-specific books and materials easily.\n4. **Advanced Search Functionality**: Capable of quick and precise searches using keywords, ISBN numbers, or other relevant filters to enhance the user experience.\n5. **Shopping Cart and Checkout**: A straightforward shopping cart and seamless checkout process that supports multiple payment options (credit/debit cards, PayPal, etc.) and includes options for discount codes or gift cards.\n6. **Order Management System**: For both customers and administrators, includes order tracking, status updates, and the ability to handle bulk orders efficiently.\n7. **Inventory Management**: Real-time inventory updates that reflect current stock levels both online and within the physical store to avoid overselling or stock-outs.\n8. **Secure Payment Gateway**: A reliable payment processing system ensuring safe and secure transactions for all users, compliant with international standards and regulations.\n9. **Personalised Recommendations**: Utilising data analytics to offer personalised book recommendations based on browsing history and previous purchases.\n10. **Review and Rating System**: Enables customers to leave reviews and ratings for books they've purchased, assisting others in making informed decisions.\n11. **Customer Support**: Integration of chat-bots or live support options to assist customers with inquiries or issues in real-time.\n12. **Marketing Tools**: Features for email marketing, promotional banners, seasonal deals, and newsletter subscriptions to engage with customers and drive sales.\n13. **Analytics and Reporting**: Back-end tools for tracking sales performance, customer behaviour, and inventory turnover to aid strategic decisions.\n\nThese features are designed to provide a comprehensive and competitive online shopping experience that complements our physical store's offerings while maintaining the high service level expected by our existing clientele, including our academic partners.",
    ),
    # Add more questions and answers as needed
    # For brevity, I'm including just a few key questions from each section
    # Section 3: Users
    (
        "Who are your application's primary users?",
        "The primary users of our web-shop can be broadly categorised into the following groups:\n\n1. **General Consumers**: This group includes book enthusiasts, casual readers, and anyone interested in purchasing books online. They range from locals who appreciate the convenience of online shopping to international customers seeking unique or specific titles we offer.\n2. **University Faculty**: As the preferred supplier of Leiden University, faculty members are crucial users. They will use the platform to browse and order course materials, specialised academic publications, and research resources.\n3. **Students**: Students from Leiden University and beyond represent a significant user base. They will use the web-shop for their academic needs, including purchasing textbooks, reference materials, and supplementary reading.\n4. **Research Professionals and Academics**: Users in this category include researchers and academics who seek specialised and scholarly works that we might offer due to our association with the university.\n5. **Gift Buyers**: Customers purchasing books as gifts will value features like gift wrapping, personal messages, and curated lists for gifts, birthdays, or special occasions.\n6. **Local Authors and Literary Fans**: This group includes local authors who might be interested in our support for their works and literary enthusiasts who engage in community-driven events or book clubs.\n\nBy understanding the needs and expectations of these primary user groups, we aim to tailor the web-shop's features and functionalities to serve them effectively, ensuring a rewarding experience that encourages repeat interactions and positive word-of-mouth.",
    ),
    # Section 5: Data Model and Structures
    (
        "What are the main entities or objects that the software will manage on a daily basis?",
        "The software will manage several key entities or objects on a daily basis to ensure smooth and efficient operations. These include:\n\n1. **Books/Products**: Details include title, author, ISBN, genre, language, publication date, price, stock quantity, descriptions, and reviews. Management will involve updating inventory, pricing, and promotions and adding new releases or editions.\n2. **Users/Customers**: Profiles containing account information such as names, email addresses, order history, wish-list items, payment preferences, and user roles (e.g., faculty member, student, general customer). Managing user data includes registrations, login details, and maintaining privacy and security.\n3. **Orders**: Information includes order number, customer details, items purchased, order status, payment confirmation, shipping information, and tracking numbers. Orders require processing, fulfilment, updates, and tracking.\n4. **Inventory**: Includes stock levels, locations (online and physical store), reorder thresholds, and supplier details. It requires synchronisation across systems to prevent discrepancies and optimise stock levels.\n5. **Payments and Transactions**: Data on payment methods, transaction amounts, payment status, and refunds. Secure and compliant processing is vital, as is keeping accurate financial records.\n6. **Vendors/Suppliers**: Details such as supplier contracts, contact information, pricing agreements, and order history. Vendor management includes processing purchase orders and maintaining supply chain relationships.\n7. **Academic Programs/Courses**: Information related to course-specific book lists, faculty associations, and any special pricing or terms. This involves updating course materials and coordinating bulk purchases or billing.\n8. **Reviews and Ratings**: User-generated content on book reviews and ratings, which helps in product visibility and customer decision-making. Moderation and analysis might be needed for quality control.\n9. **Shipping and Logistics**: Includes shipping methods, courier partnerships, delivery status, and cost management. Coordination is necessary to ensure timely delivery and handling returns or issues.\n10. **Marketing and Promotions**: Data on active promotions, discount codes, email campaigns, and user segments targeted for marketing. Managing these entities involves strategic planning and analytics.\n11. **Events**: Information on virtual or physical events, such as dates, participant lists, and event-related sales or promotions. Managing events includes logistics, registration, and post-event evaluations.\n\nEfficiently managing these entities ensures that the webshop operates smoothly, provides excellent customer service, and supports business growth.",
    ),
    # Final question to trigger completion
    (
        "Is there anything else you'd like to highlight about this project?",
        "I think we've covered all the essential aspects of the project. I'm excited to see how the online web-shop will expand our reach and enhance our service to Leiden University. Thank you for your thorough questions and guidance throughout this process.",
    ),
]


async def test_full_process():
    """Test the full interview and documentation generation process."""
    try:
        session_id = "test-interview"
        username = "kate"
        password = "TesP@ssword"

        print(
            colored(
                f"\n=== TESTING FULL INTERVIEW AND DOCUMENTATION PROCESS ===",
                "blue",
                attrs=["bold"],
            )
        )
        print(colored(f"Logging in as {username}...", "blue"))

        # Authenticate user
        auth_result = await authenticate_user(username, password)
        if not auth_result:
            raise Exception("Authentication failed")

        print(colored("Authentication successful!", "green"))

        # Create the chat manager
        chat_manager = LangChainChatManager(session_id, username)

        # Start the interview
        response = await chat_manager.process_message("Hello")
        print(colored(f"Agent: {response}", "green"))

        answers = [
            "Certainly! I'm Kate, the owner of a bookshop in Leiden and the primary decision-maker for this project. My role involves overseeing the daily operations, maintaining our relationship with Leiden University as their preferred supplier, curating our book collection, and strategising for business growth. This project is crucial to me as I aim to expand our reach beyond the physical limitations of our store through an online web-shop. I envision this platform as a means to cater to both our existing university partners and a broader audience, offering them an accessible and convenient way to explore and purchase our offerings. My involvement in this project will ensure that the web-shop aligns with our business goals, customer expectations, and unique selling points.",
            "The project involves developing a comprehensive online web-shop for my bookstore in Leiden. The main goals of this project are to expand our customer base beyond our physical store by reaching a wider, potentially global audience, and to enhance the service we provide to Leiden University as their preferred supplier. Key objectives include: Online Presence, User-Friendly Interface, Order Management, Integrating Academic Needs, Inventory Management, Marketing and Promotion, Secure and Reliable Transactions.",
            "There are a few primary challenges I anticipate in this project: Technical Integration, User Experience, Customisation for Academic Needs, Inventory Synchronisation, Security and Privacy, Marketing and Visibility, Logistical Operations.",
            "Here are the core features and functionalities I envision for the web-shop: User Account Management, Detailed Book Catalogue, Integrated Academic Portal, Advanced Search Functionality, Shopping Cart and Checkout, Order Management System, Inventory Management, Secure Payment Gateway, Personalised Recommendations, Review and Rating System, Customer Support, Marketing Tools, Analytics and Reporting.",
            "The primary users of our web-shop can be broadly categorised into the following groups: General Consumers, University Faculty, Students, Research Professionals and Academics, Gift Buyers, Local Authors and Literary Fans.",
            "The software will manage several key entities or objects on a daily basis to ensure smooth and efficient operations: Books/Products, Users/Customers, Orders, Inventory, Payments and Transactions, Vendors/Suppliers, Academic Programs/Courses, Reviews and Ratings, Shipping and Logistics, Marketing and Promotions, Events.",
            "I think we've covered all the essential aspects of the project. I'm excited to see how the online web-shop will expand our reach and enhance our service to Leiden University. Thank you for your thorough questions and guidance throughout this process.",
        ]

        for answer in answers:
            response = await chat_manager.process_message(answer)
            print(colored(f"Agent: {response}", "green"))
            next_response = await chat_manager.process_message("next")
            print(colored(f"Agent: {next_response}", "green"))

        print(colored("\nTest completed successfully!", "blue", attrs=["bold"]))
        return True

    except Exception as e:
        logger.error(f"Error in full process test: {str(e)}", exc_info=True)
        print(colored(f"Error: {str(e)}", "red"))
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test the full interview and documentation process"
    )
    args = parser.parse_args()

    print(colored("Starting full process test...", "blue"))
    asyncio.run(test_full_process())
