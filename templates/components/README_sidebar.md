# Sidebar Component Documentation

## Overview
The sidebar component is a reusable UI element that provides consistent navigation across all dashboard pages in the FinTera application.

## Files Structure
```
templates/
├── components/
│   ├── sidebar.html           # Main sidebar component
│   └── README_sidebar.md      # This documentation
├── dashboard_base.html        # Base template with sidebar layout
└── examples/
    └── automl_dashboard.html.example  # Example usage
```

## Features
- ✅ **Collapsible sidebar** with smooth animations
- ✅ **Mobile responsive** with hamburger menu
- ✅ **Active state detection** for current page
- ✅ **Fixed positioning** with proper scroll control
- ✅ **Icon-only mode** when collapsed
- ✅ **Coming Soon modal** for unimplemented features

## Usage

### Method 1: Using Dashboard Base Template (Recommended)
```html
{% extends 'dashboard_base.html' %}

{% block title %}Your App Name - FinTera{% endblock %}

{% block dashboard_content %}
<!-- Your app content goes here -->
<div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content">Your App Name</h1>
    <p class="text-base-content/70 mt-2">Your app description.</p>
</div>
<!-- Add more content -->
{% endblock %}
```

### Method 2: Direct Include
```html
{% extends 'base.html' %}

{% block content %}
<div class="min-h-screen bg-base-100">
    <div class="flex">
        {% include 'components/sidebar.html' %}
        
        <div id="mainContent" class="flex-1 w-full ml-64 min-h-screen bg-base-100 transition-all duration-300">
            <!-- Your content -->
        </div>
    </div>
</div>
{% endblock %}
```

## Customization

### Adding New Navigation Items
Edit `templates/components/sidebar.html` and add new navigation items:

```html
<a href="{% url 'your_app:view_name' %}" class="flex items-center p-3 rounded-lg {% if request.resolver_match.url_name == 'view_name' %}bg-primary text-primary-content{% else %}hover:bg-base-300 text-base-content{% endif %} transition-colors sidebar-nav-item">
    <i class="ri-your-icon mr-3 flex-shrink-0"></i>
    <span class="sidebar-text">Your App Name</span>
</a>
```

### Active State Detection
The sidebar automatically detects the current page using:
```html
{% if request.resolver_match.url_name == 'dashboard' %}bg-primary text-primary-content{% else %}hover:bg-base-300 text-base-content{% endif %}
```

## JavaScript Features

### Collapse/Expand
- Desktop: Click the toggle button in sidebar header
- Mobile: Use hamburger menu

### Responsive Behavior
- Desktop: Sidebar is always visible
- Mobile: Sidebar slides in/out on demand

### Main Content Adjustment
When sidebar collapses:
- Sidebar width: 64 → 16 units
- Main content margin: ml-64 → ml-16

## CSS Classes

### Required Classes for Main Content
```html
<div id="mainContent" class="flex-1 w-full ml-64 min-h-screen bg-base-100 transition-all duration-300">
```

### Sidebar Text Elements
All text that should hide when collapsed:
```html
<span class="sidebar-text">Text that hides when collapsed</span>
```

### Navigation Items
```html
<a href="#" class="flex items-center p-3 rounded-lg hover:bg-base-300 text-base-content transition-colors sidebar-nav-item">
```

## Dependencies
- **RemixIcon**: For all icons
- **DaisyUI**: For styling components
- **Tailwind CSS**: For utility classes

## Browser Support
- Modern browsers with CSS Grid and Flexbox support
- JavaScript ES6+ features used

## Notes
- The sidebar component includes its own JavaScript
- Coming Soon modal is automatically created if needed
- Mobile responsiveness handled automatically
- Scroll is disabled on sidebar, enabled on main content only 