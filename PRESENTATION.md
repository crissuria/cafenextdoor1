# Cafe Next Door - Web Application Presentation

---

## Slide 1: Title & Team Members

**Cafe Next Door**
*Web Application Project*

**Team Members:**
- Sudaria
- Aganan
- Mauricio
- Guzman

**Course:** Flask Web Application Development
**Date:** January 2025

---

## Slide 2: Problem Identification

**The Challenge:**
- Cafe Next Door lacks a digital presence
- No efficient system for menu management
- Limited customer communication channels
- Difficulty updating menu items and prices

**Affected Stakeholders:**
- Cafe owners and managers
- Customers and potential customers
- Cafe staff

**Why This Problem Matters:**
- Real-world relevance for small businesses
- Educational value in web development
- Scalable solution for future enhancements

---

## Slide 3: Proposed Solution

**Cafe Next Door Web Application**

A simple, user-friendly Flask-based web system that provides:

- **Public Pages:**
  - Home page with cafe information
  - Menu display with database integration
  - Contact form for customer inquiries

- **Admin Features:**
  - Secure authentication system
  - Full CRUD operations for menu items
  - Contact message management
  - Spam protection and duplicate detection
  - Image upload functionality

- **Key Benefits:**
  - Easy to use and maintain
  - Responsive design for all devices
  - Clean, modern interface

---

## Slide 4: System Features

**Core Functionality:**

1. **Home Page**
   - Welcome section with cafe branding
   - Feature highlights
   - Location, hours, and contact info

2. **Menu Page**
   - Dynamic menu display from database
   - Items organized by category
   - Shows name, description, and price

3. **Contact Form**
   - Name, email, and message fields
   - Form validation
   - Success/error notifications

4. **Admin Panel**
   - Secure login system with password hashing
   - Dashboard with navigation cards
   - Add, edit, and delete menu items
   - Direct image file uploads
   - Sortable menu management table

5. **Contact Message Management**
   - View all customer messages
   - Filter by status (Active/Archived/All)
   - Sort by date (Newest/Oldest)
   - Archive/unarchive messages
   - Reply via email functionality
   - Delete messages

6. **Spam Protection**
   - Rate limiting (IP and email-based)
   - Honeypot field detection
   - Automatic duplicate message removal
   - IP address tracking

---

## Slide 5: System Design

**Architecture Overview:**

```
Client Browser
    ↓
Flask Application (Routes & Logic)
    ↓
SQLite Database (Menu Items)
    ↓
Jinja2 Templates (Views)
    ↓
Static Files (CSS/JS)
```

**Technology Stack:**
- **Backend:** Python 3.8+, Flask 3.0.0, Werkzeug 3.0.1
- **Database:** SQLite3 (4 tables: menu_items, users, contact_messages, rate_limiting)
- **Frontend:** HTML5, CSS3, JavaScript (ES6+)
- **Templates:** Jinja2
- **Security:** Password hashing, session management, spam protection

**Key Components:**
- Route handlers with authentication decorators
- Database initialization with multiple tables
- Form processing with file uploads
- Toast-style flash messages with auto-dismiss
- Responsive hamburger menu
- Custom font integration
- Client-side sorting and filtering

---

## Slide 6: Demo Screenshots

**Application Screens:**

1. **Home Page**
   - Hero section with call-to-action buttons
   - Feature cards (Premium Coffee, Fresh Pastries, Cozy Atmosphere)
   - Information section

2. **Menu Page**
   - Category-organized menu items
   - Item cards with descriptions and prices
   - Responsive grid layout

3. **Contact Page**
   - Contact form with validation
   - Contact information display
   - Success message after submission

4. **Admin Dashboard**
   - Grid of 4 navigation cards
   - Manage Menu, Add Item, View Messages, View Public Menu
   - Welcome message with username

5. **Admin Menu Management**
   - Sortable table with all menu items
   - Edit and delete actions
   - Add new item button
   - Category icons and organized display

6. **Admin Contact Messages**
   - Message cards with sender info
   - Filter dropdowns (Active/Archived/All)
   - Sort dropdowns (Newest/Oldest)
   - Action buttons: Reply, Archive, Delete

7. **Toast Notifications**
   - Centered flash messages at top
   - Auto-dismiss after 2 seconds
   - Smooth fade-out animation

---

## Slide 7: Conclusion

**What We Learned:**
- Flask framework fundamentals and advanced features
- Database integration with SQLite (multiple tables)
- Template rendering with Jinja2
- Form handling with file uploads
- Authentication and session management
- Password hashing and security best practices
- Spam protection and rate limiting
- Responsive web design with hamburger menu
- Custom font integration (@font-face)
- Toast notification systems
- Client-side sorting and filtering
- Project documentation

**Challenges Overcome:**
- Database initialization with multiple tables
- Template inheritance and code organization
- Form validation (client & server-side)
- File upload handling and storage
- Authentication system implementation
- Session management and route protection
- Spam protection strategies
- Responsive design implementation
- Flash message styling and auto-dismiss
- Duplicate message detection and removal

**Completed Enhancements:**
- ✅ User authentication with secure password hashing
- ✅ Full CRUD operations (Create, Read, Update, Delete) for menu items
- ✅ Image upload functionality with file validation
- ✅ Contact message management system
- ✅ Spam protection (rate limiting, honeypot, duplicates)
- ✅ Automatic duplicate message removal
- ✅ Toast-style flash messages with auto-dismiss
- ✅ Responsive hamburger menu for mobile
- ✅ Custom branding with custom fonts

**Future Enhancements:**
- Email integration for contact form submissions
- Search functionality for menu items
- Online ordering system
- Payment processing
- Reservation system
- Customer reviews and ratings
- Analytics dashboard
- Multi-language support

**Project Status:** ✅ Complete and Functional

**Thank You!**

---

*Questions?*

