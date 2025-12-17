# Cafe Next Door - Web Application Documentation

## 1. Document Control

| Section | Details |
|---------|---------|
| **Document Title** | Cafe Next Door - Web Application Documentation |
| **Version** | 2.0 |
| **Date** | January 2025 |
| **Prepared By** | Sudaria, Aganan, Mauricio, Guzman |
| **Approved By** | Dr. Professor Instructor |

---

## 2. Introduction

### 2.1 Purpose of the Document

This document provides comprehensive documentation for the Cafe Next Door web application project. It outlines the problem identification, proposed solution, system design, implementation details, and conclusions. This document serves as a reference for stakeholders, developers, and instructors to understand the project's scope, architecture, and functionality.

### 2.2 Scope

This document covers:
- Problem identification and analysis
- System requirements and features
- Technical architecture and design
- Implementation details and technologies used
- User interface and functionality
- Database structure and operations
- Future recommendations

The scope is limited to the development of a simple web application using Flask framework for a coffee shop management system.

---

## 3. Problem Identification

### 3.1 Problem Description

Cafe Next Door is a small neighborhood coffee shop that currently lacks a digital presence and efficient system for managing its operations. The cafe faces several challenges:

1. **Limited Customer Reach**: The cafe has no online platform to showcase its menu and offerings, limiting its ability to attract new customers and provide information to existing ones.

2. **Inefficient Menu Management**: Menu items are currently managed through physical menus and word-of-mouth, making it difficult to update prices, add new items, or remove discontinued products efficiently.

3. **Poor Customer Communication**: There is no structured system for customers to contact the cafe with inquiries, feedback, or special requests. Communication relies solely on in-person visits or phone calls.

4. **Lack of Digital Presence**: In today's digital age, the absence of a web presence puts the cafe at a competitive disadvantage compared to other establishments that offer online menus and contact forms.

### 3.2 Affected Users / Stakeholders

The following stakeholders are affected by this problem:

1. **Cafe Owners/Managers**: Need an efficient system to manage menu items and respond to customer inquiries.

2. **Customers**: Require easy access to menu information and a convenient way to contact the cafe.

3. **Cafe Staff**: Benefit from a centralized system for menu information that can be easily updated.

4. **Potential Customers**: Need to discover the cafe's offerings before visiting.

### 3.3 Evidence / Reason for Choosing This Problem

This problem was chosen for the following reasons:

1. **Real-World Relevance**: Small businesses, especially local cafes, often struggle with establishing an online presence due to limited resources and technical expertise.

2. **Practical Application**: The solution addresses common needs that many small businesses face, making it a practical and applicable project.

3. **Educational Value**: The project provides an opportunity to learn and apply web development concepts including:
   - Backend development with Flask
   - Database management with SQLite
   - Frontend development with HTML/CSS/JavaScript
   - Form handling and validation
   - User interface design

4. **Scalability**: The solution can be easily extended with additional features such as online ordering, payment processing, or reservation systems in the future.

5. **Community Impact**: Helping local businesses establish an online presence contributes to community development and economic growth.

---

## 4. Proposed Solution

### 4.1 Overview of the Web Application

Cafe Next Door web application is a simple, user-friendly Flask-based web system designed to address the cafe's digital needs. The application provides:

- **Public-Facing Pages**: Home page, menu display, and contact form accessible to all visitors
- **Admin Functionality**: A simple interface for cafe staff to add and manage menu items
- **Database Integration**: SQLite database to store menu items persistently
- **Responsive Design**: Clean, modern interface that works on desktop and mobile devices

The application follows a Model-View-Controller (MVC) pattern with Flask handling routing and business logic, Jinja2 templates for views, and SQLite for data persistence.

### 4.2 System Features / Functional Requirements

#### 4.2.1 Home Page
- **FR-001**: Display welcome message and cafe information
- **FR-002**: Show cafe features and highlights
- **FR-003**: Provide navigation links to other pages
- **FR-004**: Display cafe location, hours, and contact information

#### 4.2.2 Menu Page
- **FR-005**: Display all menu items from the database
- **FR-006**: Organize items by category (Hot Drinks, Cold Drinks, Pastries, Desserts, etc.)
- **FR-007**: Show item name, description, and price for each menu item
- **FR-008**: Support optional image display for menu items
- **FR-009**: Automatically update when new items are added via admin panel

#### 4.2.3 Contact Form
- **FR-010**: Provide a contact form with name, email, and message fields
- **FR-011**: Validate required fields before submission
- **FR-012**: Implement spam protection (honeypot field, rate limiting)
- **FR-013**: Store form submissions in database
- **FR-014**: Automatically detect and remove duplicate messages
- **FR-015**: Display success/error messages using toast-style flash messages
- **FR-016**: Auto-dismiss flash messages after 2 seconds

#### 4.2.4 Admin Panel
- **FR-014**: Require user authentication to access admin panel
- **FR-015**: Provide secure login system with password hashing
- **FR-016**: Allow authorized users to add new menu items
- **FR-017**: Allow authorized users to edit existing menu items
- **FR-018**: Allow authorized users to delete menu items
- **FR-019**: Require item name, price, and category as mandatory fields
- **FR-020**: Support optional description and image upload/URL fields
- **FR-021**: Validate price input (must be a valid number)
- **FR-022**: Provide feedback on successful item operations
- **FR-023**: Display existing menu items in sortable table format
- **FR-024**: Support direct image file uploads for menu items

#### 4.2.5 Contact Message Management
- **FR-025**: Allow admin to view all contact messages
- **FR-026**: Support filtering messages (Active, Archived, All)
- **FR-027**: Support sorting messages by date (Newest/Oldest)
- **FR-028**: Allow admin to archive/unarchive messages
- **FR-029**: Allow admin to delete messages
- **FR-030**: Provide email reply functionality via mailto links
- **FR-031**: Automatically remove duplicate messages (same email + content within 24 hours)

#### 4.2.6 Database Management
- **FR-032**: Automatically initialize database on first run
- **FR-033**: Seed database with sample menu items and default admin user
- **FR-034**: Support full CRUD operations for menu items
- **FR-035**: Track IP addresses for spam prevention

### 4.3 System Design

#### 4.3.1 System Flow

```
User Access
    │
    ├──> Home Page (/)
    │       └──> Navigation to other pages
    │
    ├──> Menu Page (/menu)
    │       └──> Display items from database
    │
    ├──> Contact Page (/contact)
    │       ├──> GET: Display contact form
    │       └──> POST: Process form, show flash message
    │
    ├──> Admin Login (/login)
    │       ├──> GET: Display login form
    │       └──> POST: Authenticate and create session
    │
    ├──> Admin Dashboard (/admin)
    │       └──> Display admin options (requires login)
    │
    ├──> Admin Menu Management (/admin/menu)
    │       ├──> GET: Display all menu items in sortable table
    │       ├──> Edit: Update existing menu item
    │       └──> Delete: Remove menu item
    │
    ├──> Admin Add Item (/admin/add)
    │       ├──> GET: Display add item form
    │       └──> POST: Validate and insert into database
    │
    └──> Admin Messages (/admin/messages)
            ├──> GET: Display contact messages with filters
            ├──> Archive/Unarchive: Change message status
            ├──> Delete: Remove message
            └──> Reply: Generate mailto link
```

#### 4.3.2 Wireframe

**Home Page Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar (Home|Menu|Contact) │
├─────────────────────────────────────┤
│                                     │
│      Hero Section (Welcome)         │
│      [View Menu] [Contact Us]       │
│                                     │
├─────────────────────────────────────┤
│  Features Section (3 cards)         │
│  [Premium Coffee] [Pastries] [Atmos] │
├─────────────────────────────────────┤
│  Info Section (Location|Hours|Phone) │
├─────────────────────────────────────┤
│           Footer                     │
└─────────────────────────────────────┘
```

**Menu Page Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar                      │
├─────────────────────────────────────┤
│         Menu Header                 │
├─────────────────────────────────────┤
│  Category: Hot Drinks               │
│  ┌──────┐ ┌──────┐ ┌──────┐        │
│  │Item 1│ │Item 2│ │Item 3│        │
│  └──────┘ └──────┘ └──────┘        │
│  Category: Cold Drinks              │
│  ┌──────┐ ┌──────┐                 │
│  │Item 4│ │Item 5│                 │
│  └──────┘ └──────┘                 │
└─────────────────────────────────────┘
```

**Contact Page Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar                      │
├─────────────────────────────────────┤
│         Contact Header              │
├──────────────┬──────────────────────┤
│ Contact Info  │  Contact Form        │
│ (Location)    │  [Name*]            │
│ (Phone)       │  [Email*]           │
│ (Email)       │  [Message*]         │
│ (Hours)       │  [Submit Button]    │
└──────────────┴──────────────────────┘
```

**Admin Dashboard Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar                      │
├─────────────────────────────────────┤
│      Admin Dashboard Header          │
│      Welcome, [username]!           │
├─────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐         │
│  │ Manage   │  │ Add Menu │         │
│  │ Menu     │  │ Item     │         │
│  │ [Icon]   │  │ [Icon]   │         │
│  └──────────┘  └──────────┘         │
│  ┌──────────┐  ┌──────────┐         │
│  │ View     │  │ View     │         │
│  │ Messages │  │ Public   │         │
│  │ [Icon]   │  │ Menu     │         │
│  └──────────┘  └──────────┘         │
└─────────────────────────────────────┘
```

**Admin Add Item Page Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar                      │
├─────────────────────────────────────┤
│      Add Menu Item Header            │
├─────────────────────────────────────┤
│  Form:                              │
│  [Item Name*]                       │
│  [Description]                      │
│  [Price*] [Category*]               │
│  [Upload Image] or [Image URL]       │
│  [Add Item] [View Menu]             │
└─────────────────────────────────────┘
```

**Admin Menu Management Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar                      │
├─────────────────────────────────────┤
│      Manage Menu Items Header        │
├─────────────────────────────────────┤
│  [Add New Item] [Back to Dashboard] │
├─────────────────────────────────────┤
│  Sortable Table:                     │
│  ID | Name | Category | Price | Desc │
│  ─────────────────────────────────── │
│  1  | Item | Category | P10.00 | ...│
│  [Edit] [Delete]                    │
└─────────────────────────────────────┘
```

**Admin Messages Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar                      │
├─────────────────────────────────────┤
│      Contact Messages Header         │
├─────────────────────────────────────┤
│  [Back] [Filter: ▼] [Sort: ▼]      │
├─────────────────────────────────────┤
│  Message Cards:                      │
│  ┌──────────────────────────────┐ │
│  │ Name | Email | Date            │ │
│  │ Message content...             │ │
│  │ [Reply] [Archive] [Delete]    │ │
│  └──────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Admin Login Page Layout:**
```
┌─────────────────────────────────────┐
│  Navigation Bar                      │
├─────────────────────────────────────┤
│  ┌──────────────┬─────────────────┐ │
│  │              │                 │ │
│  │  Admin       │  Login Form:    │ │
│  │  Login       │  [Username*]    │ │
│  │              │  [Password*]   │ │
│  │  Title       │  [Login Button] │ │
│  │  Section     │                 │ │
│  │              │                 │ │
│  └──────────────┴─────────────────┘ │
│  (Dark brown gradient background)    │
└─────────────────────────────────────┘
```

#### 4.3.3 Architecture

**Flask Application Structure:**
```
┌─────────────────────────────────────┐
│         Client Browser              │
└──────────────┬──────────────────────┘
               │ HTTP Requests
               ▼
┌─────────────────────────────────────┐
│      Flask Application (app.py)     │
│  ┌──────────────────────────────┐   │
│  │  Routes:                     │   │
│  │  - / (index)                 │   │
│  │  - /menu                     │   │
│  │  - /contact                  │   │
│  │  - /login                     │   │
│  │  - /logout                    │   │
│  │  - /admin                     │   │
│  │  - /admin/menu                │   │
│  │  - /admin/add                 │   │
│  │  - /admin/edit/<id>           │   │
│  │  - /admin/delete/<id>         │   │
│  │  - /admin/messages            │   │
│  │  - /admin/messages/archive/<id>│ │
│  │  - /admin/messages/delete/<id>│ │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Database Functions:         │   │
│  │  - init_database()           │   │
│  │  - seed_database()           │   │
│  │  - get_db_connection()       │   │
│  └──────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    SQLite Database (cafe.db)        │
│  ┌──────────────────────────────┐   │
│  │  Table: menu_items            │   │
│  │  - id (PK)                    │   │
│  │  - name                       │   │
│  │  - description                │   │
│  │  - price                      │   │
│  │  - category                   │   │
│  │  - image_url                  │   │
│  │  - created_at                 │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Table: users                 │   │
│  │  - id (PK)                    │   │
│  │  - username (UNIQUE)          │   │
│  │  - password_hash              │   │
│  │  - created_at                 │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Table: contact_messages      │   │
│  │  - id (PK)                    │   │
│  │  - name                       │   │
│  │  - email                      │   │
│  │  - message                    │   │
│  │  - archived                   │   │
│  │  - ip_address                │   │
│  │  - created_at                 │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Table: rate_limiting         │   │
│  │  - id (PK)                    │   │
│  │  - ip_address                │   │
│  │  - email                      │   │
│  │  - submission_count           │   │
│  │  - last_submission            │   │
│  │  - created_at                 │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Templates (Jinja2)             │
│  - base.html                        │
│  - index.html                       │
│  - menu.html                        │
│  - contact.html                     │
│  - admin_add.html                   │
└─────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Static Files                   │
│  - css/style.css                    │
│  - js/main.js                       │
└─────────────────────────────────────┘
```

**Data Flow:**
1. User makes HTTP request to Flask route
2. Flask route processes request (queries database if needed)
3. Route renders appropriate template with data
4. Template combines HTML with data using Jinja2
5. Static files (CSS/JS) are served separately
6. Complete HTML page sent to browser

---

## 5. Implementation

### 5.1 Technologies Used

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Programming language |
| **Flask** | 3.0.0 | Web framework |
| **Werkzeug** | 3.0.1 | Password hashing and security utilities |
| **SQLite3** | Built-in | Database management |
| **HTML5** | - | Markup language |
| **CSS3** | - | Styling and animations |
| **JavaScript** | ES6+ | Client-side interactivity |
| **Jinja2** | (Flask) | Template engine |

### 5.2 Flask Application Structure

```
project/
│
├── app.py                    # Main application file
│   ├── Flask app initialization
│   ├── Database functions
│   ├── Route handlers
│   └── Database seeding
│
├── requirements.txt          # Python dependencies
│
├── README.md                # Project documentation
│
├── templates/               # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── index.html          # Home page
│   ├── menu.html           # Menu display page
│   ├── contact.html        # Contact form page
│   ├── login.html          # Admin login page
│   ├── admin_dashboard.html # Admin dashboard
│   ├── admin_add.html      # Admin add item page
│   ├── admin_edit.html     # Admin edit item page
│   ├── admin_menu.html     # Admin menu management page
│   └── admin_messages.html # Admin contact messages page
│
├── static/                  # Static files
│   ├── css/
│   │   └── style.css       # Main stylesheet
│   ├── js/
│   │   └── main.js         # JavaScript functionality
│   ├── images/              # Image assets
│   │   ├── favicon.png     # Site favicon and logo
│   │   ├── hero.jpg        # Hero section background
│   │   ├── menu/           # Uploaded menu item images
│   │   └── [various icons] # Category and feature icons
│   └── fonts/
│       └── BaksoSapi.otf   # Custom brand font
│
└── database/                # Database directory
    └── cafe.db             # SQLite database (auto-created)
```

**Key Components:**

1. **app.py**: 
   - Initializes Flask application
   - Defines database schema and seeding
   - Implements all route handlers
   - Manages database connections

2. **Templates**:
   - Use Jinja2 templating for dynamic content
   - Extend base.html for consistent layout
   - Handle form submissions and flash messages

3. **Database**:
   - SQLite database for simplicity
   - Four tables: `menu_items`, `users`, `contact_messages`, `rate_limiting`
   - Auto-initialization and seeding on first run
   - Default admin user: username='admin', password='admin123'

4. **Static Files**:
   - Custom CSS for styling (no external dependencies)
   - JavaScript for enhanced user experience

### 5.3 Screenshots of Working Prototype

**Note**: The following are placeholder descriptions for screenshots that would be included in the actual documentation.

#### Screenshot 1: Home Page
- **Description**: Shows the welcome hero section with cafe branding, feature cards highlighting premium coffee, fresh pastries, and cozy atmosphere, and information section with location, hours, and contact details.
- **Key Features Visible**: Navigation bar, hero section with call-to-action buttons, three feature cards, and footer.

#### Screenshot 2: Menu Page
- **Description**: Displays menu items organized by category (Hot Drinks, Cold Drinks, Pastries, Desserts). Each item card shows the item name, description, and price.
- **Key Features Visible**: Category headers, menu item cards in grid layout, responsive design.

#### Screenshot 3: Contact Page
- **Description**: Shows contact form on the right side with name, email, and message fields, and contact information on the left (address, phone, email, hours).
- **Key Features Visible**: Two-column layout, form validation, contact details.

#### Screenshot 4: Contact Form Success Message
- **Description**: Displays a green success flash message after form submission: "Thank you, [Name]! Your message has been received. We will get back to you soon."
- **Key Features Visible**: Flash message notification, form reset.

#### Screenshot 5: Admin Add Item Page
- **Description**: Shows the admin form with fields for item name, description, price, category dropdown, and optional image URL.
- **Key Features Visible**: Form fields, category selection, submit button.

#### Screenshot 6: Admin Success Message
- **Description**: Displays success message after adding a menu item: "Menu item '[Item Name]' has been added successfully!"
- **Key Features Visible**: Flash message, confirmation of database insertion.

#### Screenshot 7: Menu Page with New Item
- **Description**: Shows the menu page after adding a new item, with the new item visible in the appropriate category.
- **Key Features Visible**: Newly added item in the menu grid, proper categorization.

#### Screenshot 8: Admin Login Page
- **Description**: Displays the admin login form with two-column layout (title on left, form on right) and dark brown gradient background.
- **Key Features Visible**: Login form, secure authentication interface.

#### Screenshot 9: Admin Dashboard
- **Description**: Shows the admin dashboard with cards for managing menu items, adding new items, viewing messages, and viewing the public menu.
- **Key Features Visible**: Dashboard cards with icons, navigation options.

#### Screenshot 10: Admin Menu Management
- **Description**: Displays all menu items in a sortable table with edit and delete actions for each item.
- **Key Features Visible**: Sortable columns, action buttons, table layout.

#### Screenshot 11: Admin Contact Messages
- **Description**: Shows contact messages with filter dropdowns (Active/Archived/All), sort options, and action buttons (Reply, Archive, Delete).
- **Key Features Visible**: Message cards, filtering, sorting, action buttons.

#### Screenshot 12: Toast Flash Messages
- **Description**: Displays centered toast-style flash messages at the top of the page that auto-dismiss after 2 seconds.
- **Key Features Visible**: Centered notification, fade-out animation.

---

## 6. Conclusion

### 6.1 What the Group Learned

Through the development of the Cafe Next Door web application, the team gained valuable experience in several areas:

1. **Web Development Fundamentals**: 
   - Understanding of client-server architecture
   - HTTP request/response cycle
   - RESTful routing principles

2. **Flask Framework**:
   - Route definition and handling
   - Template rendering with Jinja2
   - Form processing and validation
   - Flash messaging system with auto-dismiss
   - Database integration
   - Session management for authentication
   - File upload handling
   - Decorators for route protection

3. **Database Management**:
   - SQLite database setup and configuration
   - SQL query execution
   - Database schema design
   - Data seeding strategies

4. **Frontend Development**:
   - HTML5 semantic markup
   - CSS3 styling, animations, and responsive design
   - Custom font integration (@font-face)
   - JavaScript for enhanced interactivity
   - Hamburger menu for mobile devices
   - Toast notification system
   - User experience considerations

5. **Project Management**:
   - Code organization and structure
   - Version control practices
   - Documentation writing
   - Testing and debugging

### 6.2 Challenges Encountered

1. **Database Initialization**: Ensuring the database directory exists and handling first-run initialization required careful error handling.

2. **Template Inheritance**: Learning to effectively use Jinja2 template inheritance to avoid code duplication while maintaining flexibility.

3. **Form Validation**: Implementing both client-side and server-side validation to ensure data integrity and good user experience.

4. **Responsive Design**: Creating a layout that works well on both desktop and mobile devices required careful CSS planning.

5. **Flash Messages**: Understanding Flask's flash message system and implementing toast-style notifications with auto-dismiss functionality.

6. **Category Grouping**: Organizing menu items by category in the template required understanding of Jinja2 control structures.

7. **Authentication System**: Implementing secure password hashing with Werkzeug and session management for protected routes.

8. **File Uploads**: Handling image file uploads with proper validation, secure filename generation, and storage organization.

9. **Spam Protection**: Implementing rate limiting, honeypot fields, and duplicate detection to prevent abuse of the contact form.

10. **Responsive Navigation**: Creating a hamburger menu system that works seamlessly across different screen sizes.

### 6.3 Recommendations

#### Short-term Improvements:
1. ✅ **Authentication System**: Implemented secure user authentication with password hashing.

2. ✅ **Edit/Delete Functionality**: Full CRUD operations implemented for menu items.

3. ✅ **Image Upload**: Direct file upload functionality implemented with secure storage.

4. **Email Integration**: Integrate with an email service (e.g., SendGrid, SMTP) to automatically send contact form submissions to cafe email.

5. **Search Functionality**: Add search capability to the menu page to help users find specific items.

6. ✅ **Contact Message Management**: Admin can view, archive, and manage contact messages.

7. ✅ **Spam Protection**: Rate limiting, honeypot fields, and duplicate detection implemented.

#### Long-term Enhancements:
1. **Online Ordering**: Implement an online ordering system with shopping cart functionality.

2. **Payment Integration**: Add payment processing for online orders.

3. **Reservation System**: Allow customers to make table reservations online.

4. **Customer Reviews**: Add a review/rating system for menu items.

5. **Inventory Management**: Extend the system to track inventory levels and alert when items are low.

6. **Analytics Dashboard**: Add analytics to track popular items, peak hours, and customer preferences.

7. **Mobile App**: Develop a companion mobile application for iOS and Android.

8. **Multi-language Support**: Add internationalization (i18n) to support multiple languages.

### 6.4 Project Success Metrics

The project successfully achieved its primary objectives:
- ✅ Created a functional web application using Flask
- ✅ Implemented menu display with database integration
- ✅ Developed contact form with validation and spam protection
- ✅ Built secure admin interface with authentication
- ✅ Implemented full CRUD operations for menu items
- ✅ Created contact message management system
- ✅ Added automatic duplicate message removal
- ✅ Implemented toast-style flash messages with auto-dismiss
- ✅ Created clean, responsive user interface with hamburger menu
- ✅ Integrated custom fonts and professional styling
- ✅ Documented the entire project comprehensively

---

## 7. References

1. **Flask Documentation**: https://flask.palletsprojects.com/
   - Official Flask framework documentation for routing, templates, and request handling.

2. **SQLite Documentation**: https://www.sqlite.org/docs.html
   - SQLite database documentation for database operations and SQL syntax.

3. **Jinja2 Template Documentation**: https://jinja.palletsprojects.com/
   - Template engine documentation for template syntax and inheritance.

4. **Python Documentation**: https://docs.python.org/3/
   - Python programming language reference.

5. **MDN Web Docs**: https://developer.mozilla.org/
   - HTML, CSS, and JavaScript reference and tutorials.

6. **W3Schools**: https://www.w3schools.com/
   - Web development tutorials and references.

7. **Bootstrap Documentation** (for design inspiration): https://getbootstrap.com/
   - Design patterns and responsive layout concepts (though not used directly).

---

**Document End**

---

*This document was prepared as part of the Flask Web Application course project. For questions or clarifications, please contact the development team.*

